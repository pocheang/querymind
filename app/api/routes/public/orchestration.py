"""Versioned, safe Server-Sent Event delivery for orchestration traces.

Two delivery paths, chosen by STATE_BACKEND:

- `memory`: the pipeline and the subscriber meet in this process's stores, read
  on a 50ms poll -- correct only while there is one worker.
- `shared` (ARC-01 phase 3): the pipeline mirrors every event and redacted
  fragment into one Redis stream per execution (`shared_execution`), and the
  subscriber reads it with XREAD BLOCK, so it may sit on any worker.

Both send the same events in the same format. Neither sends the tracker's trace
steps any more: those were the same stage events recorded a second time and
relabelled through a table written for older stage names, so six of ten stages
reached the browser twice -- once correctly, once as a spurious `rag` event.
"""

from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps.runtime import (
    get_answer_stream_store,
    get_execution_event_store,
    get_thought_stream_store,
    require_trace_actor,
)
from app.api.routes.internal.path_params import ExecutionId
from app.api.transport.errors import forbidden, not_found, rate_limited
from app.domain.events import ExecutionEvent
from app.orchestration import shared_execution
from app.orchestration.answer_stream import AnswerStreamStore
from app.orchestration.execution_events import ExecutionEventStore
from app.orchestration.request import RequestActor
from app.services.observability.agent_execution_tracker import AgentExecutionTracker, ExecutionTrace, terminal_event
from app.services.runtime.shared_state import SharedStateUnavailable, is_shared

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


def serialize_answer_fragment(fragment: str) -> str:
    """Serialize one already-redacted draft fragment for the SSE wire format.

    A distinct event name so a client cannot mistake a draft for a finished
    answer: these carry no citation numbering and no reference list, both of
    which are decided in `output_filter` once the whole answer exists.
    """
    payload = json.dumps({"text": fragment}, ensure_ascii=False, separators=(",", ":"))
    return f"event: answer_fragment\ndata: {payload}\n\n"


def serialize_thought_fragment(fragment: str) -> str:
    """Serialize one already-redacted reasoning fragment for the SSE wire format.

    Mirrors `serialize_answer_fragment` exactly, under its own event name so a
    client cannot mistake reasoning for answer text -- only published at all
    when the request opted in to visible reasoning
    (`AdvancedRAGRequest.use_reasoning`).
    """
    payload = json.dumps({"text": fragment}, ensure_ascii=False, separators=(",", ":"))
    return f"event: thought_fragment\ndata: {payload}\n\n"


def serialize_execution_event(event: ExecutionEvent) -> str:
    """Serialize exactly one safe execution event for the SSE wire format."""
    payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    return f"event: execution_event\ndata: {payload}\n\n"


def _ensure_trace_access(owner_user_id: str | None, actor: RequestActor) -> None:
    """Only the run's owner, or an administrator, may watch it."""
    if str(actor.role or "").lower() == "admin":
        return
    if str(actor.user_id or "") != str(owner_user_id or ""):
        raise forbidden("You do not have permission to access this execution trace")


# ---- STATE_BACKEND=memory: this process's stores, polled ----------------------------


def _poll_execution_updates(
    execution_id,
    event_store,
    answer_store,
    thought_store,
    event_offset,
    answer_offset,
    thought_offset,
):
    """Everything new since the last poll, in emission order, plus the advanced offsets.

    Same subscription, same access check for both drafts: a client watching
    the trace is already watching them. The thought store is simply empty for
    an execution that never opted in to visible reasoning, so polling it costs
    nothing extra in the common case.
    """
    events = event_store.events_since(execution_id, event_offset)
    items = [serialize_execution_event(event) for event in events]
    event_offset += len(events)

    fragments = answer_store.since(execution_id, answer_offset)
    items.extend(serialize_answer_fragment(fragment) for fragment in fragments)
    answer_offset += len(fragments)

    thoughts = thought_store.since(execution_id, thought_offset)
    items.extend(serialize_thought_fragment(fragment) for fragment in thoughts)
    thought_offset += len(thoughts)

    return event_offset, answer_offset, thought_offset, items


async def _stream_execution_events(
    execution_id: ExecutionId, request: Request, event_store, answer_store, thought_store
):
    event_offset = 0
    answer_offset = 0
    thought_offset = 0
    while True:
        current_trace = AgentExecutionTracker.get_instance().get_execution_trace(execution_id)
        if current_trace is None:
            return
        event_offset, answer_offset, thought_offset, items = _poll_execution_updates(
            execution_id, event_store, answer_store, thought_store, event_offset, answer_offset, thought_offset
        )
        for item in items:
            yield item
        if current_trace.status in {"completed", "failed"}:
            yield serialize_execution_event(terminal_event(current_trace))
            return
        if await request.is_disconnected():
            return
        await asyncio.sleep(0.05)


_SUBSCRIBE_GRACE_SECONDS = 10.0
_SUBSCRIBE_POLL_SECONDS = 0.05


async def _await_trace(execution_id: str) -> ExecutionTrace | None:
    """Wait briefly for a trace a client subscribed to before it was created.

    A caller may generate its own execution id and open this subscription
    before, or concurrently with, the request that calls
    ``AgentExecutionTracker.start_execution`` for it -- that ordering is the
    whole point of a client-chosen id (see ``AdvancedRAGRequest.execution_id``).
    Failing fast on "not found yet" would make that race lose every time the
    SSE connection reaches the server first.
    """
    deadline = time.monotonic() + _SUBSCRIBE_GRACE_SECONDS
    while True:
        trace = AgentExecutionTracker.get_instance().get_execution_trace(execution_id)
        if trace is not None or time.monotonic() >= deadline:
            return trace
        await asyncio.sleep(_SUBSCRIBE_POLL_SECONDS)


# ---- STATE_BACKEND=shared: one Redis stream per execution, pushed ---------------------

_SHARED_BLOCK_MS = 15_000


async def _await_shared_meta(execution_id: str) -> dict[str, str] | None:
    """The shared-state twin of `_await_trace`: the run may be opened on another worker a moment later."""

    deadline = time.monotonic() + _SUBSCRIBE_GRACE_SECONDS
    while True:
        meta = await shared_execution.read_meta(execution_id)
        if meta is not None or time.monotonic() >= deadline:
            return meta
        await asyncio.sleep(_SUBSCRIBE_POLL_SECONDS * 2)


def _serialize_shared_entry(kind: str, data: str) -> str | None:
    if kind in (shared_execution.KIND_EVENT, shared_execution.KIND_TERMINAL):
        return serialize_execution_event(ExecutionEvent.model_validate_json(data))
    if kind == shared_execution.KIND_ANSWER:
        return serialize_answer_fragment(data)
    if kind == shared_execution.KIND_THOUGHT:
        return serialize_thought_fragment(data)
    return None


async def _stream_shared_execution(execution_id: str, request: Request):
    """Push each stream entry as it arrives; stop at the terminal entry.

    A Redis failure mid-stream ends the stream rather than the request: the
    status line has already been sent, and the query response carries the
    final answer either way.
    """

    after = "0-0"
    try:
        while True:
            entries = await shared_execution.read_entries(execution_id, after, block_ms=_SHARED_BLOCK_MS)
            for entry_id, kind, data in entries:
                after = entry_id
                item = _serialize_shared_entry(kind, data)
                if item is not None:
                    yield item
                if kind == shared_execution.KIND_TERMINAL:
                    return
            if await request.is_disconnected():
                return
            if not entries and await shared_execution.read_meta(execution_id) is None:
                return  # expired: the run ended long ago, or its worker died before finishing it
    except SharedStateUnavailable:
        return


# ---- the endpoint ------------------------------------------------------------------

# How many subscriptions one user may hold open for executions that do not exist
# yet. Each waits up to `_SUBSCRIBE_GRACE_SECONDS`, and any signed-in user could
# otherwise park an unbounded number of them on random ids (ARC-02). Per worker,
# which is enough: the point is that one caller cannot exhaust one process.
_MAX_PENDING_SUBSCRIPTIONS_PER_USER = 4
_pending_subscriptions: dict[str, int] = {}


class _PendingSubscription:
    def __init__(self, actor: RequestActor) -> None:
        self._key = str(actor.user_id or "")

    def __enter__(self) -> None:
        if _pending_subscriptions.get(self._key, 0) >= _MAX_PENDING_SUBSCRIPTIONS_PER_USER:
            raise rate_limited("too many subscriptions waiting for executions that have not started")
        _pending_subscriptions[self._key] = _pending_subscriptions.get(self._key, 0) + 1

    def __exit__(self, *_exc) -> None:
        remaining = _pending_subscriptions.get(self._key, 1) - 1
        if remaining > 0:
            _pending_subscriptions[self._key] = remaining
        else:
            _pending_subscriptions.pop(self._key, None)


async def _open_local(execution_id: str, actor: RequestActor, request: Request, stores) -> StreamingResponse:
    trace = AgentExecutionTracker.get_instance().get_execution_trace(execution_id)
    if trace is None:
        with _PendingSubscription(actor):
            trace = await _await_trace(execution_id)
    if trace is None:
        raise not_found("Execution")
    _ensure_trace_access(trace.user_id, actor)
    return _sse(_stream_execution_events(execution_id, request, *stores))


async def _open_shared(execution_id: str, actor: RequestActor, request: Request) -> StreamingResponse:
    meta = await shared_execution.read_meta(execution_id)
    if meta is None:
        with _PendingSubscription(actor):
            meta = await _await_shared_meta(execution_id)
    if meta is None:
        raise not_found("Execution")
    _ensure_trace_access(meta.get("user_id") or None, actor)
    return _sse(_stream_shared_execution(execution_id, request))


def _sse(body) -> StreamingResponse:
    return StreamingResponse(
        body,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/executions/{execution_id}/events")
async def stream_execution_events(
    execution_id: ExecutionId,
    request: Request,
    actor: RequestActor = Depends(require_trace_actor),
    event_store: ExecutionEventStore = Depends(get_execution_event_store),
    answer_store: AnswerStreamStore = Depends(get_answer_stream_store),
    thought_store: AnswerStreamStore = Depends(get_thought_stream_store),
) -> StreamingResponse:
    """Follow safe events for one execution until it reaches a terminal state."""
    if is_shared():
        return await _open_shared(execution_id, actor, request)
    return await _open_local(execution_id, actor, request, (event_store, answer_store, thought_store))
