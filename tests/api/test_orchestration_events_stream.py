"""A client that generates its own execution id may reach this endpoint before
the request that registers it does.

`AdvancedRAGRequest.execution_id` exists so a caller can open
`GET /executions/{id}/events` before, or concurrently with, sending the query
that calls `AgentExecutionTracker.start_execution` for that same id -- that
ordering is the whole point of a client-chosen id (see
tests/api/test_advanced_rag_execution_flow.py). Failing fast on "not found
yet" would make that race lose whenever the SSE connection reaches the server
first, so `_await_trace` polls briefly instead of refusing immediately.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.api.routes.public import orchestration as orchestration_module
from app.services.observability.agent_execution_tracker import AgentExecutionTracker


@pytest.mark.asyncio
async def test_a_trace_registered_shortly_after_the_subscription_is_still_found(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(orchestration_module, "_SUBSCRIBE_GRACE_SECONDS", 2.0)
    execution_id = str(uuid.uuid4())

    async def register_shortly() -> None:
        await asyncio.sleep(0.1)
        AgentExecutionTracker.get_instance().start_execution(
            "a question", execution_id, user_id="u1", profile="advanced"
        )

    registration = asyncio.create_task(register_shortly())
    try:
        trace = await orchestration_module._await_trace(execution_id)
    finally:
        await registration

    assert trace is not None
    assert trace.execution_id == execution_id


@pytest.mark.asyncio
async def test_an_id_nobody_ever_registers_still_gives_up(monkeypatch: pytest.MonkeyPatch):
    """The grace period is a bounded wait, not an indefinite one: a bogus or
    mistyped id must still resolve to "not found" rather than hang."""

    monkeypatch.setattr(orchestration_module, "_SUBSCRIBE_GRACE_SECONDS", 0.05)

    trace = await orchestration_module._await_trace(str(uuid.uuid4()))

    assert trace is None
