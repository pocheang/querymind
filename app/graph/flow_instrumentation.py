"""LangGraph workflow instrumentation for agent flow tracking."""

import logging
from typing import Any, Dict, Optional
from functools import wraps
from app.services.agent_flow_tracker import get_tracker

logger = logging.getLogger(__name__)


def track_agent_node(node_name: str, node_type: str):
    """Decorator to track agent node execution.

    Args:
        node_name: Display name of the agent node
        node_type: Type of agent (router, retriever, generator, etc.)

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(state: Dict[str, Any], *args, **kwargs):
            session_id = state.get("session_id")
            if not session_id:
                # No session ID, skip tracking
                return await func(state, *args, **kwargs)

            tracker = get_tracker()
            node_id = f"{node_type}_{node_name}_{id(state)}"

            # Add node and start tracking
            tracker.add_node(
                session_id=session_id,
                node_id=node_id,
                name=node_name,
                node_type=node_type,
                input_data={"question": state.get("question")}
            )
            tracker.start_node(session_id, node_id)

            try:
                # Execute the actual function
                result = await func(state, *args, **kwargs)

                # Mark as completed
                tracker.complete_node(
                    session_id=session_id,
                    node_id=node_id,
                    output_data={"status": "success"}
                )

                return result

            except Exception as e:
                # Mark as failed
                tracker.fail_node(
                    session_id=session_id,
                    node_id=node_id,
                    error=str(e)
                )
                raise

        @wraps(func)
        def sync_wrapper(state: Dict[str, Any], *args, **kwargs):
            session_id = state.get("session_id")
            if not session_id:
                return func(state, *args, **kwargs)

            tracker = get_tracker()
            node_id = f"{node_type}_{node_name}_{id(state)}"

            tracker.add_node(
                session_id=session_id,
                node_id=node_id,
                name=node_name,
                node_type=node_type,
                input_data={"question": state.get("question")}
            )
            tracker.start_node(session_id, node_id)

            try:
                result = func(state, *args, **kwargs)
                tracker.complete_node(
                    session_id=session_id,
                    node_id=node_id,
                    output_data={"status": "success"}
                )
                return result

            except Exception as e:
                tracker.fail_node(
                    session_id=session_id,
                    node_id=node_id,
                    error=str(e)
                )
                raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_edge(from_node: str, to_node: str, condition: Optional[str] = None):
    """Track an edge between two nodes in the workflow.

    Args:
        from_node: Source node name
        to_node: Target node name
        condition: Optional condition for the edge

    Returns:
        Function to execute the tracking
    """
    def track(state: Dict[str, Any]):
        session_id = state.get("session_id")
        if not session_id:
            return

        tracker = get_tracker()
        tracker.add_edge(
            session_id=session_id,
            from_node=from_node,
            to_node=to_node,
            condition=condition
        )

    return track


class FlowInstrumentationContext:
    """Context manager for tracking a complete workflow execution."""

    def __init__(self, session_id: str):
        """Initialize the context.

        Args:
            session_id: Session identifier
        """
        self.session_id = session_id
        self.tracker = get_tracker()

    def __enter__(self):
        """Enter the context and create a new flow."""
        self.tracker.create_flow(self.session_id)
        logger.info(f"Started flow tracking for session {self.session_id}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context."""
        if exc_type is not None:
            logger.error(f"Flow tracking ended with error for session {self.session_id}: {exc_val}")
        else:
            logger.info(f"Flow tracking completed for session {self.session_id}")
        return False

    async def __aenter__(self):
        """Async enter."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)


def instrument_workflow_state(state: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Add session_id to workflow state for tracking.

    Args:
        state: Workflow state dictionary
        session_id: Session identifier

    Returns:
        Updated state with session_id
    """
    state["session_id"] = session_id
    return state
