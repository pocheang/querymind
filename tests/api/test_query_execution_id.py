"""Tests for execution_id in query responses."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_execution_tracker import AgentExecutionTracker


@pytest.fixture(autouse=True)
def clear_tracker():
    """Clear tracker before and after each test."""
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()
    yield
    tracker.clear_all_traces()


@pytest.fixture
def user_headers():
    """Mock user headers."""
    return {"X-Test-User": "testuser", "X-Test-Role": "viewer", "X-Test-User-Id": "test-123"}


@pytest.fixture
def mock_run_query():
    """Mock run_query to return a simple result with execution_id."""
    with patch("app.api.routes.query.run_query") as mock:

        def side_effect(question, **kwargs):
            execution_id = kwargs.get("execution_id") or "test-exec-id"
            return {
                "answer": "Test answer",
                "route": "vector",
                "reason": "test",
                "skill": "test",
                "agent_class": "general",
                "execution_id": execution_id,
                "vector_result": {"citations": [], "retrieved_count": 0},
                "graph_result": {"entities": []},
                "web_result": {"used": False, "citations": []},
                "detected_language": "zh",
            }

        mock.side_effect = side_effect
        yield mock


def test_query_endpoint_returns_execution_id(user_headers, mock_run_query):
    """Test that /query endpoint returns execution_id in response."""
    client = TestClient(app)

    response = client.post(
        "/api/query", json={"question": "test question", "session_id": "test-session"}, headers=user_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify execution_id is present
    assert "execution_id" in data
    assert data["execution_id"] is not None


def test_stream_query_returns_execution_id(user_headers):
    """Test that /query/stream endpoint returns execution_id in final result."""
    with patch("app.api.routes.query.run_query_stream") as mock_stream:
        # Mock streaming events including execution_id
        def stream_generator(*args, **kwargs):
            yield {"type": "status", "message": "routing"}
            yield {"type": "route", "route": "vector"}
            yield {
                "type": "done",
                "result": {
                    "answer": "Test answer",
                    "route": "vector",
                    "execution_id": "stream-exec-id",
                    "vector_result": {},
                    "graph_result": {},
                    "web_result": {"used": False},
                    "detected_language": "zh",
                },
            }

        mock_stream.return_value = stream_generator()

        client = TestClient(app)
        response = client.post(
            "/api/query/stream", data={"question": "test question", "session_id": "test-session"}, headers=user_headers
        )

        # Parse SSE events
        lines = response.text.strip().split("\n")
        events = []
        current_event = {}

        for line in lines:
            if line.startswith("event:"):
                current_event["event"] = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                import json

                current_event["data"] = json.loads(line.split(":", 1)[1].strip())
            elif line == "":
                if current_event:
                    events.append(current_event)
                    current_event = {}

        # Find the 'done' event
        done_events = [e for e in events if e.get("data", {}).get("type") == "done"]
        assert len(done_events) > 0

        # Verify execution_id is in the final result
        result = done_events[0]["data"]["result"]
        assert "execution_id" in result
        assert result["execution_id"] == "stream-exec-id"


def test_execution_id_can_be_used_with_tracking_endpoints(user_headers, mock_run_query):
    """Test that execution_id from query can be used with agent-tracking endpoints."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a real execution trace
    exec_id = tracker.start_execution("test question", user_id="test-123")
    tracker.complete_execution(exec_id, {"answer": "test"})

    # Mock run_query to return this execution_id
    def side_effect(question, **kwargs):
        return {
            "answer": "Test answer",
            "route": "vector",
            "reason": "test",
            "skill": "test",
            "agent_class": "general",
            "execution_id": exec_id,
            "vector_result": {"citations": [], "retrieved_count": 0},
            "graph_result": {"entities": []},
            "web_result": {"used": False, "citations": []},
            "detected_language": "zh",
        }

    mock_run_query.side_effect = side_effect

    client = TestClient(app)

    # Make a query
    query_response = client.post(
        "/api/query", json={"question": "test question", "session_id": "test-session"}, headers=user_headers
    )

    assert query_response.status_code == 200
    execution_id = query_response.json()["execution_id"]

    # Use the execution_id with tracking endpoint
    trace_response = client.get(f"/api/agent-tracking/trace/{execution_id}", headers=user_headers)

    assert trace_response.status_code == 200
    trace_data = trace_response.json()
    assert trace_data["execution_id"] == execution_id
    assert trace_data["query"] == "test question"


def test_execution_id_persists_through_workflow(user_headers):
    """Test that execution_id is created and persists through the entire workflow."""
    tracker = AgentExecutionTracker.get_instance()

    # We can't easily test the full workflow without mocking everything,
    # but we can verify the tracker creates and maintains execution_id
    exec_id = tracker.start_execution("workflow test", user_id="test-123")

    # Simulate workflow steps
    step_id = tracker.record_agent_step(exec_id, "router", {"question": "test"})
    tracker.complete_agent_step(exec_id, step_id, {"route": "vector"})

    # Complete execution
    final_result = {"answer": "final answer", "route": "vector"}
    tracker.complete_execution(exec_id, final_result)

    # Retrieve and verify
    trace = tracker.get_execution_trace(exec_id)
    assert trace is not None
    assert trace.execution_id == exec_id
    assert len(trace.steps) == 1
    assert trace.status == "completed"
    assert trace.metadata.get("result") == final_result
