"""The reasoning channel reaches a subscriber as its own SSE event name.

`answer_fragment` already carries the draft answer, and this file exists for
the property that made a second event name worth having rather than a flag on
the first: a client must not be able to mistake reasoning for answer text.
The two channels share one subscription, one execution id and one poll loop,
so nothing but the event name keeps them apart -- and a reader that renders
reasoning into the answer bubble is the leak `strip_chain_of_thought_preamble`
was written to prevent, arriving through the front door.

Driven through the real `_stream_execution_events` generator with the real
stores, because the seam being tested is the poll loop's own offset
bookkeeping: `_poll_execution_updates` advances four offsets, and a thought
offset that shared or shadowed the answer offset would replay or drop
fragments in a way no unit test of the serializers could see.
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.api.routes.public import orchestration as orchestration_module
from app.orchestration.answer_stream import AnswerStreamStore
from app.orchestration.execution_events import ExecutionEventStore
from app.services.observability.agent_execution_tracker import AgentExecutionTracker


class _NeverDisconnected:
    """The generator checks `request.is_disconnected()`; nothing else."""

    async def is_disconnected(self) -> bool:
        return False


async def _collect(execution_id: str, event_store, answer_store, thought_store) -> list[str]:
    frames: list[str] = []
    generator = orchestration_module._stream_execution_events(
        execution_id, _NeverDisconnected(), event_store, answer_store, thought_store
    )
    async for frame in generator:
        frames.append(frame)
    return frames


def _payloads(frames: list[str], event_name: str) -> list[str]:
    """The `text` of every frame carrying this event name, in wire order."""
    out: list[str] = []
    for frame in frames:
        if not frame.startswith(f"event: {event_name}\n"):
            continue
        data = frame.split("data: ", 1)[1].strip()
        out.append(json.loads(data)["text"])
    return out


@pytest.fixture
def execution_id() -> str:
    return str(uuid.uuid4())


@pytest.mark.asyncio
async def test_reasoning_reaches_the_subscriber_under_its_own_event_name(execution_id: str):
    tracker = AgentExecutionTracker.get_instance()
    tracker.start_execution("what is BM25?", execution_id, user_id="u1", profile="advanced")
    answer_store, thought_store = AnswerStreamStore(), AnswerStreamStore()

    thought_store.publish(execution_id, "The user is asking ")
    thought_store.publish(execution_id, "for a definition.")
    answer_store.publish(execution_id, "BM25 is a ranking function.")
    tracker.complete_execution(execution_id)

    frames = await _collect(execution_id, ExecutionEventStore(), answer_store, thought_store)

    assert _payloads(frames, "thought_fragment") == ["The user is asking ", "for a definition."]
    assert _payloads(frames, "answer_fragment") == ["BM25 is a ranking function."]


@pytest.mark.asyncio
async def test_an_execution_that_never_opted_in_streams_no_reasoning_at_all(execution_id: str):
    """`use_reasoning` defaults False, so the common case must be unchanged:
    nothing publishes to the thought store and the subscriber sees the same
    frames it saw before this channel existed."""

    tracker = AgentExecutionTracker.get_instance()
    tracker.start_execution("what is BM25?", execution_id, user_id="u1", profile="advanced")
    answer_store, thought_store = AnswerStreamStore(), AnswerStreamStore()

    answer_store.publish(execution_id, "BM25 is a ranking function.")
    tracker.complete_execution(execution_id)

    frames = await _collect(execution_id, ExecutionEventStore(), answer_store, thought_store)

    assert _payloads(frames, "thought_fragment") == []
    assert _payloads(frames, "answer_fragment") == ["BM25 is a ranking function."]


@pytest.mark.asyncio
async def test_a_fragment_is_emitted_once_however_many_times_the_loop_polls(execution_id: str):
    """The thought offset has to advance on its own.

    A thought offset left un-advanced (or shadowed by the answer offset, which
    advances at a different rate whenever the two channels are not the same
    length) replays every reasoning fragment on each 50ms poll -- which in the
    browser reads as the panel repeating itself, and is exactly the bug class
    `applyThinkingDraft` cannot defend against because it trusts the stream.
    """

    tracker = AgentExecutionTracker.get_instance()
    tracker.start_execution("what is BM25?", execution_id, user_id="u1", profile="advanced")
    answer_store, thought_store = AnswerStreamStore(), AnswerStreamStore()
    event_store = ExecutionEventStore()

    # Two polls' worth of state, with the channels deliberately uneven: three
    # reasoning fragments against one answer fragment.
    thought_store.publish(execution_id, "one ")
    thought_store.publish(execution_id, "two ")

    offsets = orchestration_module._poll_execution_updates(
        tracker.get_execution_trace(execution_id), execution_id, event_store, answer_store, thought_store, 0, 0, 0, 0
    )
    legacy_offset, event_offset, answer_offset, thought_offset, first = offsets
    assert _payloads(first, "thought_fragment") == ["one ", "two "]

    thought_store.publish(execution_id, "three")
    answer_store.publish(execution_id, "BM25 is a ranking function.")

    _, _, _, _, second = orchestration_module._poll_execution_updates(
        tracker.get_execution_trace(execution_id),
        execution_id,
        event_store,
        answer_store,
        thought_store,
        legacy_offset,
        event_offset,
        answer_offset,
        thought_offset,
    )

    assert _payloads(second, "thought_fragment") == ["three"]
    assert _payloads(second, "answer_fragment") == ["BM25 is a ranking function."]


def test_the_two_channels_do_not_share_an_event_name():
    """A regression guard with no state: if these two ever serialize under one
    name, every assertion above still passes while the client can no longer
    tell reasoning from answer."""

    assert "event: thought_fragment\n" in orchestration_module.serialize_thought_fragment("x")
    assert "event: answer_fragment\n" in orchestration_module.serialize_answer_fragment("x")
    assert orchestration_module.serialize_thought_fragment("x") != orchestration_module.serialize_answer_fragment("x")
