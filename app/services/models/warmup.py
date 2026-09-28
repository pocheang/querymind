"""Load the local models before the first question needs them.

Measured on the development machine (2026-09-28), a fresh process paid, inside
its first request: 19.5 s loading the BGE-M3 embedding model and 5-8 s loading
the reranker. The first cost alone is twice `KNOWLEDGE_SOURCE_TIMEOUT_MS`
(10 s), so the vector source timed out, retrieval came back empty and the first
question in every process was answered "no material found" -- while the load
finished in its thread and the same question worked seconds later. The reranker's
first load could also run past its own budget and fall back to lexical scoring,
which degrades the ranking without saying so.

So the loads run in a background thread when the process starts, and again
after a configuration reload (which drops the reranker and NLI models). Startup
is not delayed and no gunicorn timeout is at risk. A request that arrives while
the warm-up runs waits for the same load (`single_flight`) rather than starting a
second one, and `/ready` reports `warming` until it is done.

Nothing here reaches the network: the loaders open local files only
(`local_files_only=True`), and a remote embedding backend is constructed but
never called.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

__all__ = ["WARMERS", "model_warmup_status", "run_warmup", "start_model_warmup"]

Warmer = Callable[[], str]


def _warm_embedding() -> str:
    from app.services.models.runtime import LocalSemanticEmbeddings, get_embedding_model

    model = get_embedding_model()
    if not isinstance(model, LocalSemanticEmbeddings):
        # A remote backend is only constructed; embedding a string would be a
        # network call, and a hash fallback has nothing to load.
        return f"not local ({type(model).__name__})"
    model.embed_query("warm-up")
    return "loaded"


def _warm_reranker() -> str:
    from app.core.config import get_settings

    if not get_settings().enable_reranker:
        return "disabled"
    from app.retrievers.reranker import _load_cross_encoder

    return "loaded" if _load_cross_encoder() is not None else "absent"


def _warm_nli() -> str:
    from app.core.config import get_settings

    if not get_settings().cascade_enable_nli:
        return "disabled"
    from app.agents.verifier.validation.nli import load_nli_cross_encoder

    return "loaded" if load_nli_cross_encoder() is not None else "absent"


WARMERS: tuple[tuple[str, Warmer], ...] = (
    ("embedding", _warm_embedding),
    ("reranker", _warm_reranker),
    ("validation_nli", _warm_nli),
)
"""In the order a question needs them."""


@dataclass
class _State:
    status: str = "idle"  # idle -> warming -> ready
    components: dict[str, dict[str, object]] = field(default_factory=dict)
    duration_ms: int = 0


_state = _State()
_lock = threading.Lock()


def model_warmup_status() -> dict[str, object]:
    """What the warm-up has done so far, for `/ready`."""

    with _lock:
        return {
            "status": _state.status,
            "duration_ms": _state.duration_ms,
            "components": {name: dict(detail) for name, detail in _state.components.items()},
        }


def run_warmup(warmers: Sequence[tuple[str, Warmer]] = WARMERS) -> None:
    """Run each warmer in turn. A failure is recorded and never raised: warming is an optimisation."""

    started = time.perf_counter()
    for name, warm in warmers:
        begun = time.perf_counter()
        try:
            outcome, ok = warm(), True
        except Exception as error:  # a model library may raise anything; startup must not
            logger.warning("model warm-up: %s failed: %s", name, error, exc_info=True)
            outcome, ok = f"failed: {type(error).__name__}", False
        with _lock:
            _state.components[name] = {
                "result": outcome,
                "ok": ok,
                "duration_ms": int((time.perf_counter() - begun) * 1000),
            }
    with _lock:
        _state.status = "ready"
        _state.duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info("model warm-up finished in %d ms: %s", _state.duration_ms, model_warmup_status()["components"])


def start_model_warmup(warmers: Sequence[tuple[str, Warmer]] = WARMERS) -> threading.Thread | None:
    """Start the warm-up in a daemon thread, unless one is already running.

    Skipped under pytest: starting an app or reloading configuration in a test
    must not load gigabytes of models. `run_warmup` is what the tests drive.
    """

    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    with _lock:
        if _state.status == "warming":
            return None
        _state.status = "warming"
        _state.components = {}
    thread = threading.Thread(target=run_warmup, args=(tuple(warmers),), name="model-warmup", daemon=True)
    thread.start()
    return thread
