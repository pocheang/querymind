"""Application startup and shutdown lifecycle for the QueryMind API."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import dependencies as api_dependencies
from app.api.application.config_reload import reload_from_remote_config
from app.api.dependencies import (
    _auto_ingest_stop_event,
    auto_ingest_watcher,
)
from app.api.deps.runtime import install_app_services
from app.core.config import validate_security_settings, validate_shared_state_backends, validate_worker_topology
from app.core.remote_config import watch_remote_config
from app.graph.knowledge.client import Neo4jClient
from app.services.observability.log_buffer import setup_log_capture
from app.services.observability.log_safety import install_control_character_escaping

# Before the capture handler, so nothing it buffers can carry a forged line.
install_control_character_escaping()
setup_log_capture()
logger = logging.getLogger(__name__)
_auto_ingest_thread: threading.Thread | None = None

# Performance optimization imports
_cache_initialized = False


def _run_startup_tasks(settings) -> None:
    """Migrate every SQLite store and run the once-only tasks (`app/init_app.py`).

    The shared-state deployment runs the same code first, in its `init`
    service; here it is the backstop, and costs one read per store once the
    databases are current. Any number of processes may run it at once: the
    migrations are transactions and the once-only tasks hold a file lock.

    Skipped under pytest: a test run must not write an account into the
    developer's `data/app.db`, and the behaviour is driven directly by
    `tests/services/test_admin_bootstrap.py` and `tests/core/test_init_app.py`,
    which are better tests of it than a side effect of starting an app would
    be. Each store still migrates itself when it is constructed.
    """

    if os.getenv("PYTEST_CURRENT_TEST"):
        return

    from app.init_app import run

    run(settings)


def _start_invalidation_tracking() -> None:
    """Record where this process starts, and what a configuration change means here.

    Before any cache is built, so every cache this process builds is at least as
    new as the generation recorded. A no-op outside shared mode.
    """
    from app.api.application.config_reload import apply_config_reload
    from app.services.runtime.invalidation import catch_up, on_config_change

    on_config_change(apply_config_reload)
    catch_up()


def _require_reachable_shared_state(settings) -> None:
    """With STATE_BACKEND=shared, a Redis that does not answer is a failed start.

    Shared state that silently fell back to process memory is the ARC-01 defect
    itself, so this refuses instead of degrading. The URL is not repeated in the
    message: it can carry the Redis password.
    """

    if settings.state_backend != "shared":
        return
    from app.services.runtime.redis_connector import probe

    error = probe(settings.redis_url)
    if error is not None:
        raise RuntimeError(f"STATE_BACKEND=shared needs a reachable Redis at REDIS_URL, and it did not answer: {error}")


def _warm_nli_model() -> None:
    try:
        from app.services.legacy_agent_runtime import warm_nli_model

        logger.info("Warming up NLI model for hallucination detection...")
        warm_nli_model()
        logger.info("✓ NLI model loaded successfully")
    except Exception as e:
        logger.warning(f"NLI model warmup failed (non-critical): {e}")


def _warm_chat_model(settings) -> None:
    # `_build_chat_model_cached` imports its provider package (langchain_openai,
    # langchain_ollama, ...) on first use, inside an `lru_cache` -- and lru_cache
    # does not hold a lock across a miss, so two concurrent first requests both
    # do the import and the construction. Doing it here means the first real user
    # does not pay for it, and no two request threads race the same import. The
    # lesson is the one `app/tools/web/search.py` records the hard way: an import
    # that first happens on the request path is a latency and concurrency
    # problem, not a startup optimization.
    try:
        from app.services.models.runtime import get_chat_model

        logger.info("Warming up chat model client (backend=%s)...", settings.model_backend)
        get_chat_model()
        logger.info("✓ Chat model client ready")
    except Exception as e:
        logger.warning(f"Chat model warmup failed (non-critical): {e}")


def _warm_reranker_model(settings) -> None:
    if not settings.enable_reranker:
        return
    try:
        from app.retrievers.reranker import _load_cross_encoder

        logger.info("Warming up reranker model (%s)...", settings.reranker_model_name)
        model = _load_cross_encoder()
        if model is not None:
            logger.info("✓ Reranker model loaded successfully")
        else:
            logger.warning("⚠ Reranker model not available (will use lexical fallback)")
    except Exception as e:
        logger.warning(f"Reranker model warmup failed (non-critical): {e}")


def _init_cache_manager(settings) -> bool:
    """Initialize performance optimization services. True on success."""
    try:
        from app.services.caching import initialize_cache_manager

        initialize_cache_manager(
            l1_max_size=settings.cache_l1_size,
            l1_ttl=settings.cache_l1_ttl,
            l2_enabled=settings.cache_l2_enabled,
            l2_ttl=settings.cache_l2_ttl,
            redis_url=settings.redis_url if settings.cache_l2_enabled else None,
        )
        logger.info(
            "✓ Cache manager initialized (L1: %d items, L2: %s)",
            settings.cache_l1_size,
            "enabled" if settings.cache_l2_enabled else "disabled",
        )
        return True
    except Exception as e:
        logger.warning(f"Cache manager initialization failed (non-critical): {e}")
        return False


def _recover_unfinished_ingests(settings) -> None:
    """In memory mode this process is the only thing that runs ingest jobs.

    So a document still pending or indexing when it starts belongs to a job that
    died with the previous process, and nothing else will ever finish it. In
    shared mode the ingest worker does this when it starts.

    Skipped under pytest for the reason `_run_startup_tasks` is: starting
    an app in a test must not requeue the developer's own documents.
    """
    if settings.state_backend == "shared" or os.getenv("PYTEST_CURRENT_TEST"):
        return
    from app.services.runtime.ingest_queue import recover_unfinished_documents

    try:
        recovered = recover_unfinished_documents()
    except Exception as e:
        logger.warning(f"ingest recovery failed (non-critical): {e}", exc_info=True)
        return
    if recovered:
        logger.warning("ingest_recovery requeued=%d", len(recovered))


def _start_auto_ingest_thread(settings) -> None:
    """Watch the document folders from this process -- in memory mode only.

    With STATE_BACKEND=shared every API worker would run its own watcher and
    ingest each new file once per worker, so the watcher lives in the ingest
    worker instead (ARC-01 phase 5, C1).
    """
    global _auto_ingest_thread
    if not settings.auto_ingest_enabled or settings.state_backend == "shared":
        return
    if _auto_ingest_thread is not None and _auto_ingest_thread.is_alive():
        return
    _auto_ingest_stop_event.clear()
    _auto_ingest_thread = threading.Thread(
        target=auto_ingest_watcher.run_loop,
        args=(lambda: _auto_ingest_stop_event.is_set(),),
        daemon=True,
        name="auto-ingest-watcher",
    )
    _auto_ingest_thread.start()


async def _shutdown_services(tracker, cache_initialized: bool) -> None:
    global _auto_ingest_thread
    logger.info("Shutting down services...")

    await tracker.stop_periodic_cleanup()

    _auto_ingest_stop_event.set()
    if _auto_ingest_thread is not None and _auto_ingest_thread.is_alive():
        _auto_ingest_thread.join(timeout=5)
    _auto_ingest_thread = None
    api_dependencies.get_query_runtime().shadow_queue.stop(timeout=2.0)
    Neo4jClient.close_shared_driver()

    # Shutdown performance optimization services
    if cache_initialized:
        try:
            from app.services.caching import close_cache_manager

            await close_cache_manager()
            logger.info("Cache manager closed")
        except Exception as e:
            logger.warning(f"Cache manager shutdown failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage backend lifecycle (replaces deprecated on_event hooks)."""
    global _cache_initialized
    query_runtime = api_dependencies.get_query_runtime()
    settings = query_runtime.settings
    validate_security_settings(settings)
    validate_worker_topology(settings)
    validate_shared_state_backends(settings)
    _require_reachable_shared_state(settings)
    _start_invalidation_tracking()

    install_app_services(app)
    logger.info(
        "startup_runtime python=%s conda_env=%s model_backend=%s ollama=%s chat_model=%s",
        sys.executable,
        str(os.environ.get("CONDA_DEFAULT_ENV", "") or ""),
        str(settings.model_backend or ""),
        str(settings.ollama_base_url or ""),
        str(settings.ollama_chat_model or ""),
    )

    # Schema first, then the tasks that must run once: an administrator for a
    # checkout that has none (see `app/services/auth/bootstrap.py` for why there
    # is no default password), and clearing the retired per-user model keys.
    _run_startup_tasks(settings)

    query_runtime.shadow_queue.start()

    # A console edit should take effect the same way the admin endpoint's
    # reload does. Returns False when no configuration centre is configured,
    # which is the default, so this costs an ordinary start one env lookup.
    if watch_remote_config(reload_from_remote_config):
        logger.info("remote config: watching for changes")

    _warm_nli_model()
    _warm_chat_model(settings)
    _warm_reranker_model(settings)

    from app.services.observability.agent_execution_tracker import get_tracker

    tracker = get_tracker()
    tracker.start_periodic_cleanup(interval_seconds=300)

    _cache_initialized = _init_cache_manager(settings)
    await asyncio.to_thread(_recover_unfinished_ingests, settings)
    _start_auto_ingest_thread(settings)

    try:
        yield
    finally:
        await _shutdown_services(tracker, _cache_initialized)


__all__ = ["lifespan"]
