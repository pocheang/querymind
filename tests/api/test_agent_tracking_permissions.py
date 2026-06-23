"""Tests for agent-tracking permission and ownership validation."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.services.agent_execution_tracker import AgentExecutionTracker


@pytest.fixture(autouse=True)
def clear_tracker():
    """Clear tracker before and after each test."""
    tracker = AgentExecutionTracker.get_instance()
    tracker.clear_all_traces()
    yield
    tracker.clear_all_traces()


@pytest.fixture
def admin_headers():
    """Mock admin user headers."""
    return {"X-Test-User": "admin", "X-Test-Role": "admin", "X-Test-User-Id": "admin-123"}


@pytest.fixture
def user_headers():
    """Mock regular user headers."""
    return {"X-Test-User": "user1", "X-Test-Role": "viewer", "X-Test-User-Id": "user-456"}


@pytest.fixture
def other_user_headers():
    """Mock another regular user headers."""
    return {"X-Test-User": "user2", "X-Test-Role": "viewer", "X-Test-User-Id": "user-789"}


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_user_cannot_access_other_user_trace(client, user_headers, other_user_headers):
    """Test that a regular user cannot access another user's execution trace."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for user2
    execution_id = tracker.start_execution("test query", user_id="user-789")

    # Try to access it as user1
    client = TestClient(app)
    response = client.get(f"/api/agent-tracking/trace/{execution_id}", headers=user_headers)

    # Should be forbidden
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_user_can_access_own_trace(user_headers):
    """Test that a user can access their own execution trace."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for user1
    execution_id = tracker.start_execution("test query", user_id="user-456")
    tracker.complete_execution(execution_id)

    # Access it as user1
    client = TestClient(app)
    response = client.get(f"/api/agent-tracking/trace/{execution_id}", headers=user_headers)

    # Should succeed
    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == execution_id
    assert data["user_id"] == "user-456"


def test_admin_can_access_any_trace(admin_headers, user_headers):
    """Test that an admin can access any user's execution trace."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for regular user
    execution_id = tracker.start_execution("test query", user_id="user-456")

    # Access it as admin
    client = TestClient(app)
    response = client.get(f"/api/agent-tracking/trace/{execution_id}", headers=admin_headers)

    # Should succeed
    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == execution_id


def test_user_cannot_delete_other_user_trace(user_headers, other_user_headers):
    """Test that a regular user cannot delete another user's execution trace."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for user2
    execution_id = tracker.start_execution("test query", user_id="user-789")

    # Try to delete it as user1
    client = TestClient(app)
    response = client.delete(f"/api/agent-tracking/trace/{execution_id}", headers=user_headers)

    # Should be forbidden
    assert response.status_code == 403


def test_user_can_delete_own_trace(user_headers):
    """Test that a user can delete their own execution trace."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for user1
    execution_id = tracker.start_execution("test query", user_id="user-456")

    # Delete it as user1
    client = TestClient(app)
    response = client.delete(f"/api/agent-tracking/trace/{execution_id}", headers=user_headers)

    # Should succeed
    assert response.status_code == 200
    assert response.json()["execution_id"] == execution_id

    # Verify it's actually deleted
    assert tracker.get_execution_trace(execution_id) is None


def test_user_cannot_stream_other_user_execution(user_headers, other_user_headers):
    """Test that a regular user cannot stream another user's execution."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for user2
    execution_id = tracker.start_execution("test query", user_id="user-789")

    # Try to stream it as user1
    client = TestClient(app)
    response = client.get(f"/api/agent-tracking/stream/{execution_id}", headers=user_headers)

    # Should be forbidden
    assert response.status_code == 403


def test_user_cannot_get_status_of_other_user_execution(user_headers, other_user_headers):
    """Test that a regular user cannot get status of another user's execution."""
    tracker = AgentExecutionTracker.get_instance()

    # Create a trace for user2
    execution_id = tracker.start_execution("test query", user_id="user-789")

    # Try to get status as user1
    client = TestClient(app)
    response = client.get(f"/api/agent-tracking/status/{execution_id}", headers=user_headers)

    # Should be forbidden
    assert response.status_code == 403


def test_history_endpoint_filters_by_user(user_headers, other_user_headers):
    """Test that history endpoint only returns traces for the current user."""
    tracker = AgentExecutionTracker.get_instance()

    # Create traces for different users
    exec_id_1 = tracker.start_execution("query 1", user_id="user-456")
    exec_id_2 = tracker.start_execution("query 2", user_id="user-789")
    exec_id_3 = tracker.start_execution("query 3", user_id="user-456")

    # Get history as user1
    client = TestClient(app)
    response = client.get("/api/agent-tracking/history", headers=user_headers)

    # Should only see user1's traces
    assert response.status_code == 200
    traces = response.json()
    trace_ids = [t["execution_id"] for t in traces]
    assert exec_id_1 in trace_ids
    assert exec_id_3 in trace_ids
    assert exec_id_2 not in trace_ids


def test_admin_sees_all_traces_in_history(admin_headers, user_headers):
    """Test that admin sees all traces in history endpoint."""
    tracker = AgentExecutionTracker.get_instance()

    # Create traces for different users
    exec_id_1 = tracker.start_execution("query 1", user_id="user-456")
    exec_id_2 = tracker.start_execution("query 2", user_id="user-789")

    # Get history as admin
    client = TestClient(app)
    response = client.get("/api/agent-tracking/history", headers=admin_headers)

    # Should see all traces
    assert response.status_code == 200
    traces = response.json()
    trace_ids = [t["execution_id"] for t in traces]
    assert exec_id_1 in trace_ids
    assert exec_id_2 in trace_ids
