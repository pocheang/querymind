"""Unit tests for agent flow tracker."""

import pytest
from app.services.agent_flow_tracker import AgentFlowTracker
from app.models.agent_flow import AgentNode, AgentEdge


@pytest.fixture
def tracker():
    """Create a fresh tracker instance for each test."""
    return AgentFlowTracker()


@pytest.fixture
def session_id():
    """Test session ID."""
    return "test-session-123"


def test_create_flow(tracker, session_id):
    """Test creating a new flow."""
    flow = tracker.create_flow(session_id)

    assert flow.session_id == session_id
    assert len(flow.nodes) == 0
    assert len(flow.edges) == 0
    assert flow.current_node is None


def test_get_flow(tracker, session_id):
    """Test retrieving a flow."""
    tracker.create_flow(session_id)
    flow = tracker.get_flow(session_id)

    assert flow is not None
    assert flow.session_id == session_id


def test_get_nonexistent_flow(tracker):
    """Test retrieving a flow that doesn't exist."""
    flow = tracker.get_flow("nonexistent")
    assert flow is None


def test_add_node(tracker, session_id):
    """Test adding a node to a flow."""
    node = tracker.add_node(
        session_id=session_id,
        node_id="router-1",
        name="Router Agent",
        node_type="router",
        input_data={"question": "What is RAG?"}
    )

    assert node.id == "router-1"
    assert node.name == "Router Agent"
    assert node.type == "router"
    assert node.status == "pending"
    assert node.input_data["question"] == "What is RAG?"

    flow = tracker.get_flow(session_id)
    assert len(flow.nodes) == 1
    assert flow.nodes[0].id == "router-1"


def test_start_node(tracker, session_id):
    """Test starting a node."""
    tracker.add_node(
        session_id=session_id,
        node_id="router-1",
        name="Router Agent",
        node_type="router"
    )

    success = tracker.start_node(session_id, "router-1")
    assert success is True

    flow = tracker.get_flow(session_id)
    node = flow.nodes[0]
    assert node.status == "running"
    assert node.start_time is not None
    assert flow.current_node == "router-1"


def test_complete_node(tracker, session_id):
    """Test completing a node."""
    tracker.add_node(
        session_id=session_id,
        node_id="router-1",
        name="Router Agent",
        node_type="router"
    )
    tracker.start_node(session_id, "router-1")

    success = tracker.complete_node(
        session_id=session_id,
        node_id="router-1",
        output_data={"route": "vector_rag"}
    )
    assert success is True

    flow = tracker.get_flow(session_id)
    node = flow.nodes[0]
    assert node.status == "completed"
    assert node.end_time is not None
    assert node.output_data["route"] == "vector_rag"
    assert flow.current_node is None


def test_fail_node(tracker, session_id):
    """Test failing a node."""
    tracker.add_node(
        session_id=session_id,
        node_id="router-1",
        name="Router Agent",
        node_type="router"
    )
    tracker.start_node(session_id, "router-1")

    success = tracker.fail_node(
        session_id=session_id,
        node_id="router-1",
        error="Connection timeout"
    )
    assert success is True

    flow = tracker.get_flow(session_id)
    node = flow.nodes[0]
    assert node.status == "failed"
    assert node.end_time is not None
    assert node.error == "Connection timeout"
    assert flow.current_node is None


def test_add_edge(tracker, session_id):
    """Test adding an edge between nodes."""
    tracker.add_node(session_id, "router-1", "Router", "router")
    tracker.add_node(session_id, "retriever-1", "Retriever", "retriever")

    edge = tracker.add_edge(
        session_id=session_id,
        from_node="router-1",
        to_node="retriever-1",
        label="route to vector RAG",
        condition="route == 'vector_rag'"
    )

    assert edge.from_node == "router-1"
    assert edge.to_node == "retriever-1"
    assert edge.label == "route to vector RAG"
    assert edge.condition == "route == 'vector_rag'"

    flow = tracker.get_flow(session_id)
    assert len(flow.edges) == 1


def test_get_summary(tracker, session_id):
    """Test getting flow summary statistics."""
    # Add multiple nodes with different statuses
    tracker.add_node(session_id, "node-1", "Node 1", "router")
    tracker.start_node(session_id, "node-1")
    tracker.complete_node(session_id, "node-1")

    tracker.add_node(session_id, "node-2", "Node 2", "retriever")
    tracker.start_node(session_id, "node-2")

    tracker.add_node(session_id, "node-3", "Node 3", "generator")
    tracker.start_node(session_id, "node-3")
    tracker.fail_node(session_id, "node-3", "Error")

    tracker.add_node(session_id, "node-4", "Node 4", "evaluator")

    summary = tracker.get_summary(session_id)

    assert summary.session_id == session_id
    assert summary.total_nodes == 4
    assert summary.completed_nodes == 1
    assert summary.running_nodes == 1
    assert summary.failed_nodes == 1
    assert summary.pending_nodes == 1
    assert summary.total_duration_ms is not None


def test_subscribe_and_notify(tracker, session_id):
    """Test subscribing to flow updates."""
    updates = []

    def callback(update):
        updates.append(update)

    tracker.subscribe(session_id, callback)

    # Add a node, which should trigger a notification
    tracker.add_node(session_id, "node-1", "Node 1", "router")

    assert len(updates) == 1
    assert updates[0].type == "node_add"

    # Start the node
    tracker.start_node(session_id, "node-1")

    assert len(updates) == 2
    assert updates[1].type == "node_update"


def test_unsubscribe(tracker, session_id):
    """Test unsubscribing from flow updates."""
    updates = []

    def callback(update):
        updates.append(update)

    tracker.subscribe(session_id, callback)
    tracker.add_node(session_id, "node-1", "Node 1", "router")

    assert len(updates) == 1

    # Unsubscribe
    tracker.unsubscribe(session_id, callback)

    # Add another node
    tracker.add_node(session_id, "node-2", "Node 2", "retriever")

    # Should still be 1 (no new update)
    assert len(updates) == 1


def test_clear_flow(tracker, session_id):
    """Test clearing a flow."""
    tracker.create_flow(session_id)
    tracker.add_node(session_id, "node-1", "Node 1", "router")

    assert tracker.get_flow(session_id) is not None

    tracker.clear_flow(session_id)

    assert tracker.get_flow(session_id) is None


def test_multiple_sessions(tracker):
    """Test tracking multiple sessions simultaneously."""
    session1 = "session-1"
    session2 = "session-2"

    tracker.add_node(session1, "node-1", "Node 1", "router")
    tracker.add_node(session2, "node-2", "Node 2", "retriever")

    flow1 = tracker.get_flow(session1)
    flow2 = tracker.get_flow(session2)

    assert len(flow1.nodes) == 1
    assert len(flow2.nodes) == 1
    assert flow1.nodes[0].id == "node-1"
    assert flow2.nodes[0].id == "node-2"


def test_node_timing(tracker, session_id):
    """Test that node timing is tracked correctly."""
    import time

    tracker.add_node(session_id, "node-1", "Node 1", "router")
    tracker.start_node(session_id, "node-1")

    time.sleep(0.1)  # Small delay

    tracker.complete_node(session_id, "node-1")

    flow = tracker.get_flow(session_id)
    node = flow.nodes[0]

    assert node.start_time is not None
    assert node.end_time is not None
    assert node.end_time > node.start_time
