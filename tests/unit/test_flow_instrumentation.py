"""Unit tests for LangGraph flow instrumentation."""

import pytest
from unittest.mock import Mock, patch
from app.graph.flow_instrumentation import (
    track_agent_node,
    track_edge,
    FlowInstrumentationContext,
    instrument_workflow_state
)


@pytest.fixture
def mock_tracker():
    """Create a mock tracker."""
    with patch("app.graph.flow_instrumentation.get_tracker") as mock:
        tracker = Mock()
        mock.return_value = tracker
        yield tracker


@pytest.fixture
def state_with_session():
    """Create a state dict with session_id."""
    return {
        "session_id": "test-session-123",
        "question": "What is RAG?"
    }


@pytest.fixture
def state_without_session():
    """Create a state dict without session_id."""
    return {
        "question": "What is RAG?"
    }


def test_track_agent_node_sync(mock_tracker, state_with_session):
    """Test tracking a synchronous agent node."""
    @track_agent_node("Router", "router")
    def router_agent(state):
        return {"route": "vector_rag"}

    result = router_agent(state_with_session)

    assert result["route"] == "vector_rag"
    assert mock_tracker.add_node.called
    assert mock_tracker.start_node.called
    assert mock_tracker.complete_node.called


@pytest.mark.asyncio
async def test_track_agent_node_async(mock_tracker, state_with_session):
    """Test tracking an asynchronous agent node."""
    @track_agent_node("Router", "router")
    async def router_agent(state):
        return {"route": "vector_rag"}

    result = await router_agent(state_with_session)

    assert result["route"] == "vector_rag"
    assert mock_tracker.add_node.called
    assert mock_tracker.start_node.called
    assert mock_tracker.complete_node.called


def test_track_agent_node_without_session(mock_tracker, state_without_session):
    """Test that tracking is skipped when no session_id is present."""
    @track_agent_node("Router", "router")
    def router_agent(state):
        return {"route": "vector_rag"}

    result = router_agent(state_without_session)

    assert result["route"] == "vector_rag"
    assert not mock_tracker.add_node.called
    assert not mock_tracker.start_node.called
    assert not mock_tracker.complete_node.called


def test_track_agent_node_with_error(mock_tracker, state_with_session):
    """Test tracking when agent node raises an error."""
    @track_agent_node("Router", "router")
    def router_agent(state):
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        router_agent(state_with_session)

    assert mock_tracker.add_node.called
    assert mock_tracker.start_node.called
    assert mock_tracker.fail_node.called
    assert not mock_tracker.complete_node.called


@pytest.mark.asyncio
async def test_track_agent_node_async_with_error(mock_tracker, state_with_session):
    """Test tracking when async agent node raises an error."""
    @track_agent_node("Router", "router")
    async def router_agent(state):
        raise ValueError("Test error")

    with pytest.raises(ValueError, match="Test error"):
        await router_agent(state_with_session)

    assert mock_tracker.add_node.called
    assert mock_tracker.start_node.called
    assert mock_tracker.fail_node.called
    assert not mock_tracker.complete_node.called


def test_track_edge(mock_tracker, state_with_session):
    """Test tracking an edge between nodes."""
    track_fn = track_edge("router", "retriever", "route == 'vector_rag'")
    track_fn(state_with_session)

    mock_tracker.add_edge.assert_called_once_with(
        session_id="test-session-123",
        from_node="router",
        to_node="retriever",
        condition="route == 'vector_rag'"
    )


def test_track_edge_without_session(mock_tracker, state_without_session):
    """Test that edge tracking is skipped when no session_id is present."""
    track_fn = track_edge("router", "retriever")
    track_fn(state_without_session)

    assert not mock_tracker.add_edge.called


def test_flow_instrumentation_context(mock_tracker):
    """Test FlowInstrumentationContext context manager."""
    session_id = "test-session-123"

    with FlowInstrumentationContext(session_id) as ctx:
        assert ctx.session_id == session_id
        mock_tracker.create_flow.assert_called_once_with(session_id)


@pytest.mark.asyncio
async def test_flow_instrumentation_context_async(mock_tracker):
    """Test FlowInstrumentationContext async context manager."""
    session_id = "test-session-123"

    async with FlowInstrumentationContext(session_id) as ctx:
        assert ctx.session_id == session_id
        mock_tracker.create_flow.assert_called_once_with(session_id)


def test_flow_instrumentation_context_with_error(mock_tracker):
    """Test FlowInstrumentationContext handles errors correctly."""
    session_id = "test-session-123"

    with pytest.raises(ValueError):
        with FlowInstrumentationContext(session_id):
            raise ValueError("Test error")

    # Should still have created the flow
    mock_tracker.create_flow.assert_called_once_with(session_id)


def test_instrument_workflow_state():
    """Test adding session_id to workflow state."""
    state = {"question": "What is RAG?"}
    session_id = "test-session-123"

    updated_state = instrument_workflow_state(state, session_id)

    assert updated_state["session_id"] == session_id
    assert updated_state["question"] == "What is RAG?"
    assert updated_state is state  # Should modify in place


def test_track_agent_node_preserves_function_metadata():
    """Test that decorator preserves function metadata."""
    @track_agent_node("Router", "router")
    def router_agent(state):
        """Router agent docstring."""
        return {"route": "vector_rag"}

    assert router_agent.__name__ == "router_agent"
    assert router_agent.__doc__ == "Router agent docstring."


@pytest.mark.asyncio
async def test_track_agent_node_async_preserves_metadata():
    """Test that decorator preserves async function metadata."""
    @track_agent_node("Router", "router")
    async def router_agent(state):
        """Async router agent docstring."""
        return {"route": "vector_rag"}

    assert router_agent.__name__ == "router_agent"
    assert router_agent.__doc__ == "Async router agent docstring."
