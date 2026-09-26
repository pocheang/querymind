"""What a live execution's SSE subscriber needs, shared by every worker (ARC-01 phase 3).

The pipeline that answers a question and the SSE connection watching it can land
on different workers. Until this module, both met only in one process's memory
(`ExecutionEventStore`, `AnswerStreamStore`, `AgentExecutionTracker`), so a
subscriber on the other worker got 404 -- or, arriving first, waited ten seconds
for a trace that was being written somewhere it could not see.

With STATE_BACKEND=shared each execution gets two Redis keys:

- `{prefix}exec:{id}:meta` -- a hash: owner, status, start and end, duration.
  Enough to authorize a subscriber and to know the run is over. Never the
  question: it stays out of every store, as it stays out of the logs.
- `{prefix}exec:{id}:s` -- a stream of what the SSE endpoint sends, in the order
  it was produced: stage events, redacted answer and reasoning fragments, and one
  terminal entry. One stream rather than one per channel, so a subscriber reads
  a single ordered log instead of merging three.

Writers are on the request path -- the synthesizer's fragment loop, the engine's
event publisher -- so every write is queued and returns at once; one daemon
thread sends them. A write that fails is logged and dropped: the live draft is a
convenience, and the query response carries the final answer either way.

The subscriber reads with XREAD BLOCK: a push, not the 50ms poll the in-process
path still uses (ARC-02).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from app.domain.events import ExecutionEvent
from app.services.runtime.background_writer import BackgroundWriter
from app.services.runtime.redis_connector import AsyncRedisConnector
from app.services.runtime.shared_state import (
    SharedStateUnavailable,
    is_unavailable_error,
    report_failure,
    shared_client,
    state_key,
)

logger = logging.getLogger(__name__)

# A live execution's keys outlive its request by this much; a finished one's are
# shortened to FINISHED_TTL_S, long enough for a slow subscriber to drain.
LIVE_TTL_S = 3600
FINISHED_TTL_S = 600
# The per-execution caps the in-process stores use, so both paths drop the same.
MAX_STREAM_ENTRIES = 4_400

_MAX_PENDING_WRITES = 10_000

KIND_EVENT = "event"
KIND_ANSWER = "answer"
KIND_THOUGHT = "thought"
KIND_TERMINAL = "terminal"


def meta_key(execution_id: str) -> str:
    return state_key("exec", execution_id, "meta")


def stream_key(execution_id: str) -> str:
    return state_key("exec", execution_id, "s")


def _write_failed(exc: BaseException) -> None:
    """A failed stream write costs the live draft, never the request, so it is logged and dropped."""

    if isinstance(exc, SharedStateUnavailable):
        logger.warning("shared_execution_write_skipped reason=%s", exc)
        return
    if is_unavailable_error(exc):
        report_failure(exc)
    logger.warning("shared_execution_write_failed error=%s", type(exc).__name__)


_WRITER = BackgroundWriter("shared_execution", max_pending=_MAX_PENDING_WRITES, on_error=_write_failed)


def _submit(write: Callable[[Any], None]) -> None:
    _WRITER.submit(lambda: write(shared_client()))


def flush(timeout: float = 5.0) -> bool:
    """Wait for queued writes. For tests and for shutdown; the request path never waits."""

    return _WRITER.flush(timeout)


def open_execution(execution_id: str, user_id: str | None) -> None:
    started_at = time.time()

    def write(client) -> None:
        pipe = client.pipeline()
        pipe.hset(
            meta_key(execution_id), mapping={"user_id": user_id or "", "status": "running", "started_at": started_at}
        )
        pipe.expire(meta_key(execution_id), LIVE_TTL_S)
        pipe.execute()

    _submit(write)


def _append(execution_id: str, kind: str, data: str) -> None:
    def write(client) -> None:
        pipe = client.pipeline()
        pipe.xadd(stream_key(execution_id), {"kind": kind, "data": data}, maxlen=MAX_STREAM_ENTRIES, approximate=True)
        pipe.expire(stream_key(execution_id), LIVE_TTL_S)
        pipe.execute()

    _submit(write)


def publish_event(execution_id: str, event: ExecutionEvent) -> None:
    _append(execution_id, KIND_EVENT, event.model_dump_json())


def publish_fragment(execution_id: str, kind: str, text: str) -> None:
    """`kind` is KIND_ANSWER or KIND_THOUGHT. The text has already been through the redactor."""

    if text:
        _append(execution_id, kind, text)


def finish_execution(execution_id: str, terminal: ExecutionEvent) -> None:
    """Record the outcome and end the stream; both keys then expire sooner."""

    def write(client) -> None:
        pipe = client.pipeline()
        pipe.xadd(
            stream_key(execution_id),
            {"kind": KIND_TERMINAL, "data": terminal.model_dump_json()},
            maxlen=MAX_STREAM_ENTRIES,
            approximate=True,
        )
        pipe.hset(
            meta_key(execution_id),
            mapping={
                "status": terminal.status,
                "ended_at": time.time(),
                "duration_ms": terminal.duration_ms,
            },
        )
        pipe.expire(meta_key(execution_id), FINISHED_TTL_S)
        pipe.expire(stream_key(execution_id), FINISHED_TTL_S)
        pipe.execute()

    _submit(write)


def execution_exists(execution_id: str) -> bool:
    """Whether any worker has opened this execution. Synchronous: call it off the event loop."""

    client = shared_client()
    try:
        return bool(client.exists(meta_key(execution_id)))
    except Exception as exc:
        if is_unavailable_error(exc):
            raise report_failure(exc) from exc
        raise


# ---- the subscriber's side -----------------------------------------------------

# No socket timeout: XREAD BLOCK holds the connection open by design, and a read
# timeout shorter than the block would turn every quiet second into an error.
_READER = AsyncRedisConnector("execution_stream_reader", decode_responses=True, socket_connect_timeout=0.5)


async def _reader():
    client = await _READER.client()
    if client is None:
        raise SharedStateUnavailable("execution stream store (Redis) is unavailable")
    return client


async def read_meta(execution_id: str) -> dict[str, str] | None:
    client = await _reader()
    try:
        meta = await client.hgetall(meta_key(execution_id))
    except Exception as exc:
        if is_unavailable_error(exc):
            await _READER.drop(exc)
            raise SharedStateUnavailable("execution stream store (Redis) failed") from exc
        raise
    return meta or None


async def read_entries(execution_id: str, after: str, *, block_ms: int) -> list[tuple[str, str, str]]:
    """Entries after `after`, waiting up to `block_ms` for the first one. `(entry_id, kind, data)`."""

    client = await _reader()
    try:
        response = await client.xread({stream_key(execution_id): after}, count=200, block=block_ms)
    except Exception as exc:
        if is_unavailable_error(exc):
            await _READER.drop(exc)
            raise SharedStateUnavailable("execution stream store (Redis) failed") from exc
        raise
    entries: list[tuple[str, str, str]] = []
    for _key, items in response or ():
        for entry_id, fields in items:
            entries.append((entry_id, fields.get("kind", ""), fields.get("data", "")))
    return entries


def terminal_event(data: str) -> ExecutionEvent:
    return ExecutionEvent.model_validate(json.loads(data))


__all__ = [
    "FINISHED_TTL_S",
    "KIND_ANSWER",
    "KIND_EVENT",
    "KIND_TERMINAL",
    "KIND_THOUGHT",
    "LIVE_TTL_S",
    "execution_exists",
    "finish_execution",
    "flush",
    "meta_key",
    "open_execution",
    "publish_event",
    "publish_fragment",
    "read_entries",
    "read_meta",
    "stream_key",
    "terminal_event",
]
