"""
Main FastAPI application for Multi-Agent Local RAG.
"""
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.utils.error_responses import not_found
from app.core.config import get_settings
from app.services.log_buffer import setup_log_capture
from app.graph.neo4j_client import Neo4jClient

# Import dependencies to initialize services
from app.api import dependencies as api_dependencies
from app.api.dependencies import (
    auto_ingest_watcher,
    auth_service,
    login_limiter,
    query_result_cache,
    register_limiter,
    shadow_queue,
    settings,
    _audit,
    _auto_ingest_stop_event,
    _history_store_for_user,
    _memory_store_for_user,
    _require_user,
    _enforce_result_source_scope,
    _query_cache_key,
    _allowed_sources_for_user,
)
from app.api.utils import (
    admin_helpers,
    auth_dependencies,
    auth_helpers,
    document_helpers,
    memory_helpers,
    query_helpers,
    session_helpers,
)
from app.api.utils.admin_helpers import _check_chroma_ready, _check_ollama_ready, _load_benchmark_queries
from app.api.utils.document_helpers import (
    _allowed_sources_for_visible_filenames,
    _list_visible_documents_for_user,
    _resynthesize_after_source_scope,
    _source_mtime_ns,
    _visible_index_fingerprint_for_user,
)
from app.agents.synthesis_agent import synthesize_answer
from app.core.models import clear_model_caches, get_chat_model
from app.services.index_manager import rebuild_all_vector_index
from app.retrievers.vector_store import clear_vector_store_cache
from app.services.input_normalizer import enhance_user_question_for_completion, normalize_and_validate_user_question
from app.services.input_normalizer import normalize_user_question
from app.services.index_manager import list_indexed_files
from app.services.agent_classifier import classify_agent_class
from app.services.model_config_store import get_global_model_settings, save_global_model_settings
from app.services.query_intent import is_casual_chat_query
from app.graph.streaming import run_query_stream
from app.graph.workflow import run_query
from app.services.runtime_ops import append_benchmark_trend, apply_rollback_profile, read_benchmark_trends


# Import middleware
from app.api.middleware import request_timing_middleware

# Import route modules
from app.api.routes import health, auth, query, sessions, documents, prompts
from app.api.routes import admin_users, admin_ops, admin_settings, admin_language_stats
from app.api.routes import agent_tracking, evaluation
from app.api.routes import advanced_rag, analytics
from app.api.routes.health import _check_neo4j_ready

auth_dependencies.auth_service = auth_service
auth_helpers.auth_service = auth_service

_ROUTE_MODULES = (
    api_dependencies,
    admin_helpers,
    auth_dependencies,
    auth_helpers,
    document_helpers,
    health,
    memory_helpers,
    query_helpers,
    session_helpers,
    auth,
    query,
    sessions,
    documents,
    prompts,
    admin_users,
    admin_ops,
    admin_settings,
    admin_language_stats,
    agent_tracking,
    evaluation,
    advanced_rag,
    analytics,
)

# Setup logging
setup_log_capture()
logger = logging.getLogger(__name__)

# Auto-ingest watcher state
_auto_ingest_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage backend lifecycle (replaces deprecated on_event hooks)."""
    global _auto_ingest_thread

    # Startup
    logger.info(
        "startup_runtime python=%s conda_env=%s model_backend=%s ollama=%s chat_model=%s",
        sys.executable,
        str(os.environ.get("CONDA_DEFAULT_ENV", "") or ""),
        str(settings.model_backend or ""),
        str(settings.ollama_base_url or ""),
        str(settings.ollama_chat_model or ""),
    )

    # Start shadow queue for background processing
    shadow_queue.start()

    # Start agent execution tracker periodic cleanup
    from app.services.agent_execution_tracker import get_tracker
    tracker = get_tracker()
    await tracker.start_periodic_cleanup(interval_seconds=300)  # 5 minutes

    if settings.auto_ingest_enabled and (
        _auto_ingest_thread is None or not _auto_ingest_thread.is_alive()
    ):
        _auto_ingest_stop_event.clear()
        _auto_ingest_thread = threading.Thread(
            target=auto_ingest_watcher.run_loop,
            args=(lambda: _auto_ingest_stop_event.is_set(),),
            daemon=True,
            name="auto-ingest-watcher",
        )
        _auto_ingest_thread.start()

    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down services...")

        # Stop agent execution tracker cleanup
        await tracker.stop_periodic_cleanup()

        _auto_ingest_stop_event.set()
        if _auto_ingest_thread is not None and _auto_ingest_thread.is_alive():
            _auto_ingest_thread.join(timeout=5)
        _auto_ingest_thread = None
        shadow_queue.stop(timeout=2.0)
        Neo4jClient.close_shared_driver()


# Initialize FastAPI app
app = FastAPI(title="Multi-Agent Local RAG", lifespan=lifespan)


def _configure_cors(app_obj: FastAPI, settings_obj) -> None:
    """Attach CORS middleware according to settings, with prod-safety guards.

    Refuses to start when ``CORS_ALLOW_ORIGINS`` includes ``*`` and
    ``APP_ENV`` is set to ``prod`` / ``production``. Wildcards are still
    accepted in dev/staging but credentials are disabled in that case.
    """
    if not bool(getattr(settings_obj, "cors_enabled", True)):
        return

    cors_origins = settings_obj.cors_origins or []
    allow_all = "*" in cors_origins
    is_production = str(getattr(settings_obj, "app_env", "dev") or "").strip().lower() in {
        "prod",
        "production",
    }

    if allow_all and is_production:
        raise RuntimeError(
            "Refusing to start: CORS_ALLOW_ORIGINS=='*' is not allowed when APP_ENV is "
            "'prod' or 'production'. Set CORS_ALLOW_ORIGINS to an explicit comma-separated "
            "list of trusted frontend origins (https URLs)."
        )

    app_obj.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else cors_origins,
        allow_credentials=bool(getattr(settings_obj, "cors_allow_credentials", True))
        and (not allow_all),
        allow_methods=settings_obj.cors_methods,
        allow_headers=settings_obj.cors_headers,
    )


# Configure CORS
_configure_cors(app, settings)

# Add request timing middleware
app.middleware("http")(request_timing_middleware)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(sessions.router)
app.include_router(documents.router)
app.include_router(prompts.router)
app.include_router(admin_users.router)
app.include_router(admin_ops.router)
app.include_router(admin_settings.router)
app.include_router(admin_language_stats.router)
app.include_router(agent_tracking.router)
app.include_router(evaluation.router)
app.include_router(advanced_rag.router)
app.include_router(analytics.router)

# React frontend serving
react_dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
react_index_file = react_dist_dir / "index.html"
react_assets_dir = react_dist_dir / "assets"

# Serve React build assets
if react_assets_dir.exists():
    app.mount("/app/assets", StaticFiles(directory=str(react_assets_dir)), name="react-assets")


def _serve_react_index() -> FileResponse:
    """Serve the React index.html file."""
    if not react_index_file.exists():
        raise not_found("frontend build not found")
    return FileResponse(str(react_index_file))


@app.get("/app")
@app.get("/app/")
def serve_react_app_root():
    """Serve React app root."""
    return _serve_react_index()


@app.get("/app/{frontend_path:path}")
def serve_react_app(frontend_path: str):
    """Serve React app for all frontend routes."""
    normalized = str(frontend_path or "").strip().strip("/")
    if normalized.startswith("assets/"):
        raise not_found("asset not found")
    return _serve_react_index()


class _CompatMainModule(type(sys)):
    """Backward-compat shim for tests that monkeypatch ``app.api.main`` symbols.

    Many tests do ``monkeypatch.setattr(api_main, "_audit", ...)`` or replace
    globals such as ``auth_service`` and ``settings`` on ``app.api.main``. After
    routes were split into ``app.api.routes.*`` and helpers into
    ``app.api.utils.*``, those modules each hold their own bindings to the same
    callables/instances. Without this shim, monkeypatching ``app.api.main`` no
    longer affects the actual code path executed by the routes.

    This metaclass intercepts attribute writes on the ``app.api.main`` module
    object and propagates them to every module in ``_ROUTE_MODULES`` that
    already has a binding with the same name. New route modules MUST be added
    to ``_ROUTE_MODULES`` above; otherwise their copies of shared globals will
    drift away from the patched ones.
    """

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        for module in _ROUTE_MODULES:
            if hasattr(module, name):
                setattr(module, name, value)


sys.modules[__name__].__class__ = _CompatMainModule
