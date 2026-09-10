"""Versioned, safe Server-Sent Event delivery for orchestration traces."""

from __future__ import annotations

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps.runtime import get_answer_stream_store, get_execution_event_store, require_trace_actor
from app.api.routes.internal.path_params import ExecutionId
from app.api.transport.errors import forbidden, not_found
from app.domain.events import ExecutionEvent
from app.orchestration.answer_stream import AnswerStreamStore
from app.orchestration.execution_events import ExecutionEventStore
from app.orchestration.request import RequestActor
from app.services.observability.agent_execution_tracker import AgentExecutionTracker, AgentStep, ExecutionTrace

router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


_STAGE_BY_AGENT: tuple[tuple[str, Literal["route", "plan", "rag", "tool", "synthesize"]], ...] = (
    ("router", "route"),
    ("planner", "plan"),
    ("plan", "plan"),
    ("tool", "tool"),
    ("synth", "synthesize"),
)


def serialize_answer_fragment(fragment: str) -> str:
    """Serialize one already-redacted draft fragment for the SSE wire format.

    A distinct event name so a client cannot mistake a draft for a finished
    answer: these carry no citation numbering and no reference list, both of
    which are decided in `output_filter` once the whole answer exists.
    """
    payload = json.dumps({"text": fragment}, ensure_ascii=False, separators=(",", ":"))
    return f"event: answer_fragment\ndata: {payload}\n\n"


def serialize_execution_event(event: ExecutionEvent) -> str:
    """Serialize exactly one safe execution event for the SSE wire format."""
    payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))
    return f"event: execution_event\ndata: {payload}\n\n"


def _trace_status(status: str) -> str:
    """Collapse the tracker's vocabulary onto the three the trace shows.

    Anything that is not a recognised failure or a completion is reported
    as skipped, so an unknown status can never read as success.
    """

    if status in {"failed", "error"}:
        return "failed"
    return "completed" if status == "completed" else "skipped"


def _trace_event(step: AgentStep) -> ExecutionEvent:
    """Map legacy tracker detail to a non-sensitive, immutable trace event."""
    stage = next((value for prefix, value in _STAGE_BY_AGENT if step.agent_name.lower().startswith(prefix)), "rag")
    status = _trace_status(step.status)
    return ExecutionEvent(
        stage=stage,
        status=status,
        duration_ms=max(0, int(step.duration_ms or 0)),
        occurred_at=step.end_time or step.start_time,
    )


def _ensure_trace_access(trace: ExecutionTrace, actor: RequestActor) -> None:
    """Keep execution trace visibility aligned with the existing tracker policy."""
    if str(actor.role or "").lower() == "admin":
        return
    if str(actor.user_id or "") != str(trace.user_id or ""):
        raise forbidden("You do not have permission to access this execution trace")


def _poll_execution_updates(
    current_trace, execution_id, event_store, answer_store, legacy_offset, event_offset, answer_offset
):
    """Everything new since the last poll, in emission order, plus the advanced offsets.

    Same subscription, same access check for the answer draft: a client
    watching the trace is already watching it.
    """
    steps = tuple(current_trace.steps)
    items = [serialize_execution_event(_trace_event(step)) for step in steps[legacy_offset:]]
    legacy_offset = len(steps)

    events = event_store.events_since(execution_id, event_offset)
    items.extend(serialize_execution_event(event) for event in events)
    event_offset += len(events)

    fragments = answer_store.since(execution_id, answer_offset)
    items.extend(serialize_answer_fragment(fragment) for fragment in fragments)
    answer_offset += len(fragments)

    return legacy_offset, event_offset, answer_offset, items


def _terminal_event(current_trace):
    return serialize_execution_event(
        ExecutionEvent(
            stage="complete" if current_trace.status == "completed" else "failed",
            status=current_trace.status,
            duration_ms=max(0, int(current_trace.total_duration_ms or 0)),
            occurred_at=current_trace.end_time or current_trace.start_time,
        )
    )


async def _stream_execution_events(execution_id: ExecutionId, request: Request, event_store, answer_store):
    legacy_offset = 0
    event_offset = 0
    answer_offset = 0
    while True:
        current_trace = AgentExecutionTracker.get_instance().get_execution_trace(execution_id)
        if current_trace is None:
            return
        legacy_offset, event_offset, answer_offset, items = _poll_execution_updates(
            current_trace, execution_id, event_store, answer_store, legacy_offset, event_offset, answer_offset
        )
        for item in items:
            yield item
        if current_trace.status in {"completed", "failed"}:
            yield _terminal_event(current_trace)
            return
        if await request.is_disconnected():
            return
        await asyncio.sleep(0.05)


@router.get("/executions/{execution_id}/events")
async def stream_execution_events(
    execution_id: ExecutionId,
    request: Request,
    actor: RequestActor = Depends(require_trace_actor),
    event_store: ExecutionEventStore = Depends(get_execution_event_store),
    answer_store: AnswerStreamStore = Depends(get_answer_stream_store),
) -> StreamingResponse:
    """Follow safe events for one execution until it reaches a terminal state."""
    trace = AgentExecutionTracker.get_instance().get_execution_trace(execution_id)
    if trace is None:
        raise not_found("Execution")
    _ensure_trace_access(trace, actor)

    return StreamingResponse(
        _stream_execution_events(execution_id, request, event_store, answer_store),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
