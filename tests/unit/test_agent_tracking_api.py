import asyncio

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.api.routes.agent_tracking import router
from app.services.agent_execution_tracker import AgentExecutionTracker


@pytest.fixture
def test_app():
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client with the app."""
    return TestClient(test_app)


@pytest.fixture
def tracker():
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()
    return tracker


def test_get_execution_trace_not_found(client):
    response = client.get("/agent-tracking/trace/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_execution_trace_success(client, tracker):
    execution_id = tracker.start_execution("test query")
    step_id = tracker.record_agent_step(execution_id, "TestAgent", {"input": "test"})
    tracker.complete_agent_step(execution_id, step_id, {"output": "result"})
    tracker.complete_execution(execution_id)

    response = client.get(f"/agent-tracking/trace/{execution_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == execution_id
    assert data["query"] == "test query"
    assert data["status"] == "completed"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["agent_name"] == "TestAgent"


def test_get_execution_history(client, tracker):
    for i in range(5):
        execution_id = tracker.start_execution(f"query {i}")
        tracker.complete_execution(execution_id)

    response = client.get("/agent-tracking/history?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["query"] == "query 4"
    assert data[1]["query"] == "query 3"
    assert data[2]["query"] == "query 2"


def test_get_execution_history_invalid_limit(client):
    response = client.get("/agent-tracking/history?limit=0")
    assert response.status_code == 400

    response = client.get("/agent-tracking/history?limit=101")
    assert response.status_code == 400


def test_get_execution_status(client, tracker):
    execution_id = tracker.start_execution("test query")
    step_id = tracker.record_agent_step(execution_id, "TestAgent", {})
    tracker.complete_agent_step(execution_id, step_id, {})

    response = client.get(f"/agent-tracking/status/{execution_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == execution_id
    assert data["status"] == "running"
    assert data["query"] == "test query"
    assert data["step_count"] == 1


def test_get_execution_status_not_found(client):
    response = client.get("/agent-tracking/status/nonexistent-id")
    assert response.status_code == 404


def test_delete_execution_trace(client, tracker):
    execution_id = tracker.start_execution("test query")

    response = client.delete(f"/agent-tracking/trace/{execution_id}")
    assert response.status_code == 200
    assert response.json()["execution_id"] == execution_id

    assert tracker.get_execution_trace(execution_id) is None


def test_delete_execution_trace_not_found(client):
    response = client.delete("/agent-tracking/trace/nonexistent-id")
    assert response.status_code == 404


def test_cleanup_old_traces(client, tracker):
    tracker._ttl_hours = 0

    for i in range(3):
        execution_id = tracker.start_execution(f"old query {i}")
        trace = tracker._traces[execution_id]
        from datetime import timedelta

        from app.services.agent_execution_tracker import utcnow

        trace.start_time = utcnow() - timedelta(hours=2)

    response = client.post("/agent-tracking/cleanup")
    assert response.status_code == 200
    data = response.json()
    assert data["removed_count"] == 3


def test_stream_execution_not_found(client):
    response = client.get("/agent-tracking/stream/nonexistent-id")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    content = response.text
    assert "event: error" in content
    assert "not found" in content.lower()


def test_stream_execution_with_steps(client, tracker):
    execution_id = tracker.start_execution("test query")

    async def add_steps():
        await asyncio.sleep(0.1)
        step_id = tracker.record_agent_step(execution_id, "TestAgent", {"input": "test"})
        await asyncio.sleep(0.1)
        tracker.complete_agent_step(execution_id, step_id, {"output": "result"})
        await asyncio.sleep(0.1)
        tracker.complete_execution(execution_id)

    import threading

    thread = threading.Thread(target=lambda: asyncio.run(add_steps()))
    thread.start()

    response = client.get(f"/agent-tracking/stream/{execution_id}", timeout=5)
    thread.join(timeout=5)

    assert response.status_code == 200
    content = response.text

    assert "event: agent_step" in content
    assert "TestAgent" in content
    assert "event: execution_complete" in content


def test_stream_execution_timeout(client, tracker):
    execution_id = tracker.start_execution("test query")

    response = client.get(f"/agent-tracking/stream/{execution_id}?max_iterations=1")

    assert response.status_code == 200
    content = response.text
    assert "event: heartbeat" in content or "event: timeout" in content or "event: execution_complete" in content
