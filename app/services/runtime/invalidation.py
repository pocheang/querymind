"""Telling the other workers that a cache they hold is stale (ARC-01 phase 6).

Each process caches things built from shared state: BM25 indexes over the
corpus, retrieval results, the settings object and everything made from it,
vector-store handles holding an embedding function. When one worker changes the
shared state it clears its own copies -- and every other worker went on serving
the old ones: a deleted document stayed retrievable through another worker's
BM25 index, a configuration reload took effect on one worker in N.

The mechanism is one counter per kind of change in Redis, `qm:gen:<kind>`:

- whoever changes something clears its own caches and calls `announce(kind)`,
  which increments the counter;
- every process calls `catch_up()` at the start of each request (and the ingest
  worker before each job): one MGET, and for any kind whose counter moved past
  the last one this process applied, the local clear runs first.

So the next request on any worker sees the change -- there is no window in which
a message can be missed, because nothing is sent. (Pub/Sub was considered and
left out: these caches are only read inside requests, so noticing between
requests would buy nothing.)

A failed announce is kept and retried on this process's next `catch_up` or
`announce`, so a Redis outage delays the news rather than losing it. Outside
STATE_BACKEND=shared every function here is a no-op: one process, and the
caller has already cleared its caches.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable

from app.services.runtime.shared_state import (
    SharedStateUnavailable,
    is_shared,
    is_unavailable_error,
    report_failure,
    shared_client,
    state_key,
)

logger = logging.getLogger(__name__)

# corpus:         the document index changed (ingest, delete, full rebuild)
# config:         Settings were reloaded
# model_settings: the administrator's model configuration was saved
KINDS = ("corpus", "config", "model_settings")

_LOCK = threading.Lock()
# The last generation of each kind this process has applied; None until the
# first look, which only records where it starts (its caches were built after).
_APPLIED: dict[str, int | None] = dict.fromkeys(KINDS)
# Announcements that could not reach Redis, retried at the next chance.
_PENDING: set[str] = set()
_CONFIG_HANDLERS: list[Callable[[], object]] = []


def _clear_corpus_caches() -> None:
    from app.retrievers.bm25_retriever import reset_bm25_cache
    from app.retrievers.hybrid.caching import drop_local_retrieval_cache

    reset_bm25_cache()
    drop_local_retrieval_cache()


def _clear_model_caches() -> None:
    from app.retrievers.stores.vector import clear_vector_store_cache
    from app.services.models.runtime import clear_model_caches

    clear_model_caches()
    clear_vector_store_cache()


def _run_config_handlers() -> None:
    for handler in list(_CONFIG_HANDLERS):
        handler()


_HANDLERS: dict[str, Callable[[], None]] = {
    "corpus": _clear_corpus_caches,
    "config": _run_config_handlers,
    "model_settings": _clear_model_caches,
}


def on_config_change(handler: Callable[[], object]) -> None:
    """What a reload means in this process -- `apply_config_reload` in the API and the worker.

    Registered rather than imported: the reload sequence lives in the API layer,
    which a service must not import.
    """
    with _LOCK:
        if handler not in _CONFIG_HANDLERS:
            _CONFIG_HANDLERS.append(handler)


def _key(kind: str) -> str:
    return state_key("gen", kind)


def _flush_pending(client) -> None:
    with _LOCK:
        pending = sorted(_PENDING)
    for kind in pending:
        _increment(client, kind)
        with _LOCK:
            _PENDING.discard(kind)


def _increment(client, kind: str) -> None:
    generation = int(client.incr(_key(kind)))
    with _LOCK:
        # Advance only when this is the very next generation: if another worker
        # announced in between, this process has not applied that change yet,
        # and catch_up must still see it as new.
        if _APPLIED[kind] is not None and generation == _APPLIED[kind] + 1:
            _APPLIED[kind] = generation


def announce(kind: str) -> None:
    """Tell every other process that `kind` changed; the caller has cleared its own caches."""

    if kind not in KINDS:
        raise ValueError(f"unknown invalidation kind: {kind}")
    if not is_shared():
        return
    # The change itself has already happened, so an unreachable Redis must not
    # fail the request that made it: the news is kept and sent later.
    try:
        client = shared_client()
        _flush_pending(client)
        _increment(client, kind)
    except SharedStateUnavailable as error:
        _defer(kind, error)
    except Exception as error:
        if not is_unavailable_error(error):
            raise
        report_failure(error)
        _defer(kind, error)


def _defer(kind: str, error: BaseException) -> None:
    with _LOCK:
        _PENDING.add(kind)
    logger.error("invalidation_announce_deferred kind=%s error=%s", kind, error)


def catch_up() -> list[str]:
    """Clear what other processes changed since this one last looked; return those kinds.

    Raises `SharedStateUnavailable` when Redis does not answer: serving from
    caches that may hold a deleted document is not something to do quietly.
    """

    if not is_shared():
        return []
    client = shared_client()
    try:
        _flush_pending(client)
        values = client.mget([_key(kind) for kind in KINDS])
    except Exception as error:
        if is_unavailable_error(error):
            raise report_failure(error) from error
        raise
    stale = []
    for kind, raw in zip(KINDS, values, strict=True):
        generation = int(raw or 0)
        with _LOCK:
            applied = _APPLIED[kind]
            if applied is None:
                _APPLIED[kind] = generation
                continue
        if generation != applied:
            _HANDLERS[kind]()
            with _LOCK:
                _APPLIED[kind] = generation
            stale.append(kind)
    if stale:
        logger.info("invalidation_applied kinds=%s pid=%d", ",".join(stale), os.getpid())
    return stale


def generation(kind: str) -> int | None:
    """The generation of `kind` this process has applied, or None before its first look."""
    with _LOCK:
        return _APPLIED[kind]


def reset_for_tests() -> None:
    with _LOCK:
        for kind in KINDS:
            _APPLIED[kind] = None
        _PENDING.clear()
        _CONFIG_HANDLERS.clear()
