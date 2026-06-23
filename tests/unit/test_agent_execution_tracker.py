import asyncio
from datetime import timedelta

import pytest

from app.services.agent_execution_tracker import (
    AgentExecutionTracker,
    track_agent_execution,
    utcnow,
)


@pytest.fixture
def tracker():
    tracker = AgentExecutionTracker()
    tracker.clear_all_traces()
    return tracker


def test_start_execution(tracker):
    execution_id = tracker.start_execution("test query")

    assert execution_id is not None
    trace = tracker.get_execution_trace(execution_id)
    assert trace is not None
    assert trace.query == "test query"
    assert trace.status == "running"
    assert len(trace.steps) == 0


def test_start_execution_with_custom_id(tracker):
    custom_id = "custom-execution-id"
    execution_id = tracker.start_execution("test query", execution_id=custom_id)

    assert execution_id == custom_id
    trace = tracker.get_execution_trace(custom_id)
    assert trace is not None


def test_record_agent_step(tracker):
    execution_id = tracker.start_execution("test query")
    input_data = {"param1": "value1"}

    step_id = tracker.record_agent_step(execution_id, "TestAgent", input_data)

    assert step_id is not None
    trace = tracker.get_execution_trace(execution_id)
    assert len(trace.steps) == 1
    assert trace.steps[0].agent_name == "TestAgent"
    assert trace.steps[0].input_data == input_data
    assert trace.steps[0].status == "running"


def test_complete_agent_step(tracker):
    execution_id = tracker.start_execution("test query")
    step_id = tracker.record_agent_step(execution_id, "TestAgent", {})

    output_data = {"result": "success"}
    decision = "Chose this path because..."
    tracker.complete_agent_step(execution_id, step_id, output_data, decision)

    trace = tracker.get_execution_trace(execution_id)
    step = trace.steps[0]
    assert step.status == "completed"
    assert step.output_data == output_data
    assert step.decision_rationale == decision
    assert step.end_time is not None
    assert step.duration_ms is not None
    assert step.duration_ms >= 0


def test_fail_agent_step(tracker):
    execution_id = tracker.start_execution("test query")
    step_id = tracker.record_agent_step(execution_id, "TestAgent", {})

    error_msg = "Something went wrong"
    tracker.fail_agent_step(execution_id, step_id, error_msg)

    trace = tracker.get_execution_trace(execution_id)
    step = trace.steps[0]
    assert step.status == "failed"
    assert step.error == error_msg
    assert step.end_time is not None
    assert step.duration_ms is not None


def test_complete_execution(tracker):
    execution_id = tracker.start_execution("test query")
    tracker.complete_execution(execution_id)

    trace = tracker.get_execution_trace(execution_id)
    assert trace.status == "completed"
    assert trace.end_time is not None
    assert trace.total_duration_ms is not None
    assert trace.total_duration_ms >= 0


def test_complete_execution_accepts_final_result_metadata(tracker):
    execution_id = tracker.start_execution("test query")
    final_result = {"answer": "ok", "route": "vector"}

    tracker.complete_execution(execution_id, final_result)

    trace = tracker.get_execution_trace(execution_id)
    assert trace.status == "completed"
    assert trace.metadata["result"] == final_result


def test_fail_execution(tracker):
    execution_id = tracker.start_execution("test query")
    error_msg = "Execution failed"
    tracker.fail_execution(execution_id, error_msg)

    trace = tracker.get_execution_trace(execution_id)
    assert trace.status == "failed"
    assert trace.end_time is not None
    assert trace.metadata.get("error") == error_msg


def test_get_recent_executions(tracker):
    for i in range(5):
        tracker.start_execution(f"query {i}")

    recent = tracker.get_recent_executions(limit=3)
    assert len(recent) == 3
    assert recent[0].query == "query 4"
    assert recent[1].query == "query 3"
    assert recent[2].query == "query 2"


def test_cleanup_old_traces(tracker):
    tracker._ttl_hours = 0

    execution_id = tracker.start_execution("old query")
    trace = tracker._traces[execution_id]
    trace.start_time = utcnow() - timedelta(hours=2)

    removed = tracker.cleanup_old_traces()

    assert removed == 1
    assert tracker.get_execution_trace(execution_id) is None


def test_singleton_pattern():
    tracker1 = AgentExecutionTracker.get_instance()
    tracker2 = AgentExecutionTracker.get_instance()

    assert tracker1 is tracker2


async def test_track_agent_execution_decorator_async():
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()

    @track_agent_execution("TestAgent")
    async def test_agent_func(query: str, execution_id: str):
        await asyncio.sleep(0.01)
        return {"answer": "test result", "decision_rationale": "test decision"}

    execution_id = tracker.start_execution("test query")
    result = await test_agent_func(query="test", execution_id=execution_id)

    assert result["answer"] == "test result"

    trace = tracker.get_execution_trace(execution_id)
    assert len(trace.steps) == 1
    assert trace.steps[0].agent_name == "TestAgent"
    assert trace.steps[0].status == "completed"
    assert trace.steps[0].output_data["answer"] == "test result"
    assert trace.steps[0].decision_rationale == "test decision"


async def test_track_agent_execution_decorator_handles_error():
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()

    @track_agent_execution("TestAgent")
    async def failing_agent_func(execution_id: str):
        raise ValueError("Test error")

    execution_id = tracker.start_execution("test query")

    with pytest.raises(ValueError):
        await failing_agent_func(execution_id=execution_id)

    trace = tracker.get_execution_trace(execution_id)
    assert len(trace.steps) == 1
    assert trace.steps[0].status == "failed"
    assert "Test error" in trace.steps[0].error


def test_track_agent_execution_decorator_sync():
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()

    @track_agent_execution("TestAgent")
    def test_agent_func(query: str, execution_id: str):
        return {"answer": "test result"}

    execution_id = tracker.start_execution("test query")
    result = test_agent_func(query="test", execution_id=execution_id)

    assert result["answer"] == "test result"

    trace = tracker.get_execution_trace(execution_id)
    assert len(trace.steps) == 1
    assert trace.steps[0].agent_name == "TestAgent"
    assert trace.steps[0].status == "completed"


def test_track_agent_execution_without_execution_id():
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()

    @track_agent_execution("TestAgent")
    def test_agent_func(query: str):
        return {"answer": "test result"}

    result = test_agent_func(query="test")

    assert result["answer"] == "test result"
    recent = tracker.get_recent_executions()
    assert len(recent) == 0


def test_multiple_agent_steps(tracker):
    execution_id = tracker.start_execution("complex query")

    step1_id = tracker.record_agent_step(execution_id, "Router", {"query": "test"})
    tracker.complete_agent_step(execution_id, step1_id, {"route": "vector"})

    step2_id = tracker.record_agent_step(execution_id, "VectorRAG", {"query": "test"})
    tracker.complete_agent_step(execution_id, step2_id, {"docs": ["doc1", "doc2"]})

    step3_id = tracker.record_agent_step(execution_id, "Synthesis", {"docs": ["doc1", "doc2"]})
    tracker.complete_agent_step(execution_id, step3_id, {"answer": "final answer"})

    tracker.complete_execution(execution_id)

    trace = tracker.get_execution_trace(execution_id)
    assert len(trace.steps) == 3
    assert trace.steps[0].agent_name == "Router"
    assert trace.steps[1].agent_name == "VectorRAG"
    assert trace.steps[2].agent_name == "Synthesis"
    assert all(step.status == "completed" for step in trace.steps)
    assert trace.status == "completed"
