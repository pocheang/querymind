"""The admin "Agent Quality" dashboard is fed by the pipeline's own stage events.

`get_quality_stats` aggregates nothing but trace steps, and the only writer of
a step was `record_agent_step` -- which nothing on the request path called. The
query endpoint recorded each run's start and end and no step in between, so the
dashboard could only ever show zero agents and zero executions, with nothing
saying why. The pipeline already reports every stage, with its status and
duration, for the live trace panel; the same events feed the dashboard now.

Driven through the real publisher and the real tracker, read back through the
dashboard's own `get_quality_stats`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.events import ExecutionEvent
from app.orchestration.event_publisher import ExecutionStoreEventPublisher
from app.orchestration.execution_events import ExecutionEventStore, current_execution_id
from app.pipeline.contracts import PipelineProfile
from app.pipeline.rag_pipeline import RAGPipeline
from app.services.observability.agent_execution_tracker import AgentExecutionTracker, record_stage_event


@pytest.fixture
def tracker():
    instance = AgentExecutionTracker.get_instance()
    instance.clear_all_traces()
    yield instance
    instance.clear_all_traces()


def _publish(execution_id: str, *events: ExecutionEvent, sink=record_stage_event) -> None:
    publisher = ExecutionStoreEventPublisher(ExecutionEventStore(), step_sink=sink)
    token = current_execution_id.set(execution_id)
    try:
        for event in events:
            publisher.publish(event)
    finally:
        current_execution_id.reset(token)


def _agents(tracker) -> dict[str, dict]:
    return {agent["agent_name"]: agent for agent in tracker.get_quality_stats()["agents"]}


def test_a_run_s_stages_become_the_dashboard_s_agents(tracker):
    execution_id = tracker.start_execution("q", None, user_id="u1", profile="advanced")

    _publish(
        execution_id,
        ExecutionEvent(stage="route", status="completed", duration_ms=120),
        ExecutionEvent(stage="knowledge", status="completed", duration_ms=800),
        ExecutionEvent(stage="verifier", status="failed", duration_ms=40, message="validator timed out"),
    )

    agents = _agents(tracker)
    assert set(agents) == {"route", "knowledge", "verifier"}
    assert agents["route"]["success_count"] == 1
    assert agents["verifier"]["failure_count"] == 1
    summary = tracker.get_quality_stats()["summary"]
    assert summary["total_executions"] == 3


def test_a_stage_s_duration_is_the_one_it_reported():
    # record_agent_step + complete_agent_step would stamp both ends "now" and
    # measure every stage at 0 ms, because the event arrives once, at the end.
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()
    execution_id = tracker.start_execution("q", None, user_id="u1", profile="advanced")
    finished = datetime.now(UTC)

    _publish(execution_id, ExecutionEvent(stage="knowledge", status="completed", duration_ms=800, occurred_at=finished))

    step = tracker.get_execution_trace(execution_id).steps[0]
    assert step.duration_ms == 800
    assert step.end_time == finished
    assert step.start_time == finished - timedelta(milliseconds=800)
    tracker.clear_all_traces()


def test_skipped_and_terminal_stages_are_not_executions(tracker):
    execution_id = tracker.start_execution("q", None, user_id="u1", profile="advanced")

    _publish(
        execution_id,
        ExecutionEvent(stage="plan", status="skipped"),  # did not run
        ExecutionEvent(stage="complete", status="completed"),  # the run's own marker
    )

    assert _agents(tracker) == {}


def test_a_run_no_endpoint_started_is_not_counted(tracker):
    # A benchmark or rerun publishes stage events under an id the dashboard
    # never opened; it must not invent an "Unknown" trace for them.
    _publish("not-a-started-execution", ExecutionEvent(stage="route", status="completed", duration_ms=5))

    assert tracker.get_quality_stats()["summary"]["total_executions"] == 0


def test_a_failing_sink_never_reaches_the_answer(tracker):
    def broken(execution_id: str, event: ExecutionEvent) -> None:
        raise RuntimeError("dashboard down")

    store = ExecutionEventStore()
    publisher = ExecutionStoreEventPublisher(store, step_sink=broken)
    token = current_execution_id.set("e1")
    try:
        publisher.publish(ExecutionEvent(stage="route", status="completed"))  # must not raise
    finally:
        current_execution_id.reset(token)

    # And the live trace still got its event: the sink runs after the store.
    assert store.events_since("e1", 0)


def test_the_pipeline_s_engine_carries_the_sink():
    engine = RAGPipeline()._engine_for(PipelineProfile.ADVANCED)

    assert engine._publisher._step_sink is record_stage_event
