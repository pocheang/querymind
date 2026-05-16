"""Agent flow tracking service."""

import logging
from typing import Dict, Optional, List
from datetime import datetime
from app.models.agent_flow import (
    AgentFlowData,
    AgentNode,
    AgentEdge,
    AgentFlowUpdate,
    AgentFlowSummary
)

logger = logging.getLogger(__name__)


class AgentFlowTracker:
    """Tracks agent execution flow for visualization."""

    def __init__(self):
        """Initialize the flow tracker."""
        self._flows: Dict[str, AgentFlowData] = {}
        self._subscribers: Dict[str, List] = {}  # WebSocket subscribers

    def create_flow(self, session_id: str) -> AgentFlowData:
        """Create a new agent flow.

        Args:
            session_id: Session identifier

        Returns:
            AgentFlowData instance
        """
        flow = AgentFlowData(session_id=session_id)
        self._flows[session_id] = flow
        logger.info(f"Created agent flow for session {session_id}")
        return flow

    def get_flow(self, session_id: str) -> Optional[AgentFlowData]:
        """Get agent flow by session ID.

        Args:
            session_id: Session identifier

        Returns:
            AgentFlowData if found, None otherwise
        """
        return self._flows.get(session_id)

    def add_node(
        self,
        session_id: str,
        node_id: str,
        name: str,
        node_type: str,
        input_data: Optional[Dict] = None
    ) -> AgentNode:
        """Add a new node to the flow.

        Args:
            session_id: Session identifier
            node_id: Unique node identifier
            name: Node display name
            node_type: Type of agent node
            input_data: Optional input data

        Returns:
            Created AgentNode
        """
        flow = self._flows.get(session_id)
        if not flow:
            flow = self.create_flow(session_id)

        node = AgentNode(
            id=node_id,
            name=name,
            type=node_type,
            status="pending",
            input_data=input_data
        )

        flow.nodes.append(node)
        flow.updated_at = datetime.utcnow()

        # Notify subscribers
        self._notify_subscribers(session_id, AgentFlowUpdate(
            type="node_add",
            data=node.model_dump()
        ))

        logger.debug(f"Added node {node_id} to flow {session_id}")
        return node

    def start_node(self, session_id: str, node_id: str) -> bool:
        """Mark a node as running.

        Args:
            session_id: Session identifier
            node_id: Node identifier

        Returns:
            True if successful, False otherwise
        """
        flow = self._flows.get(session_id)
        if not flow:
            logger.warning(f"Flow {session_id} not found")
            return False

        for node in flow.nodes:
            if node.id == node_id:
                node.status = "running"
                node.start_time = datetime.utcnow().timestamp() * 1000
                flow.current_node = node_id
                flow.updated_at = datetime.utcnow()

                # Notify subscribers
                self._notify_subscribers(session_id, AgentFlowUpdate(
                    type="node_update",
                    data=node.model_dump()
                ))

                logger.debug(f"Started node {node_id} in flow {session_id}")
                return True

        logger.warning(f"Node {node_id} not found in flow {session_id}")
        return False

    def complete_node(
        self,
        session_id: str,
        node_id: str,
        output_data: Optional[Dict] = None
    ) -> bool:
        """Mark a node as completed.

        Args:
            session_id: Session identifier
            node_id: Node identifier
            output_data: Optional output data

        Returns:
            True if successful, False otherwise
        """
        flow = self._flows.get(session_id)
        if not flow:
            return False

        for node in flow.nodes:
            if node.id == node_id:
                node.status = "completed"
                node.end_time = datetime.utcnow().timestamp() * 1000
                node.output_data = output_data
                flow.updated_at = datetime.utcnow()

                # Clear current node if this was it
                if flow.current_node == node_id:
                    flow.current_node = None

                # Notify subscribers
                self._notify_subscribers(session_id, AgentFlowUpdate(
                    type="node_update",
                    data=node.model_dump()
                ))

                logger.debug(f"Completed node {node_id} in flow {session_id}")
                return True

        return False

    def fail_node(
        self,
        session_id: str,
        node_id: str,
        error: str
    ) -> bool:
        """Mark a node as failed.

        Args:
            session_id: Session identifier
            node_id: Node identifier
            error: Error message

        Returns:
            True if successful, False otherwise
        """
        flow = self._flows.get(session_id)
        if not flow:
            return False

        for node in flow.nodes:
            if node.id == node_id:
                node.status = "failed"
                node.end_time = datetime.utcnow().timestamp() * 1000
                node.error = error
                flow.updated_at = datetime.utcnow()

                # Clear current node if this was it
                if flow.current_node == node_id:
                    flow.current_node = None

                # Notify subscribers
                self._notify_subscribers(session_id, AgentFlowUpdate(
                    type="node_update",
                    data=node.model_dump()
                ))

                logger.debug(f"Failed node {node_id} in flow {session_id}: {error}")
                return True

        return False

    def add_edge(
        self,
        session_id: str,
        from_node: str,
        to_node: str,
        label: Optional[str] = None,
        condition: Optional[str] = None
    ) -> AgentEdge:
        """Add an edge between two nodes.

        Args:
            session_id: Session identifier
            from_node: Source node ID
            to_node: Target node ID
            label: Optional edge label
            condition: Optional condition

        Returns:
            Created AgentEdge
        """
        flow = self._flows.get(session_id)
        if not flow:
            flow = self.create_flow(session_id)

        edge = AgentEdge(
            from_node=from_node,
            to_node=to_node,
            label=label,
            condition=condition
        )

        flow.edges.append(edge)
        flow.updated_at = datetime.utcnow()

        # Notify subscribers
        self._notify_subscribers(session_id, AgentFlowUpdate(
            type="edge_add",
            data=edge.model_dump(by_alias=True)
        ))

        logger.debug(f"Added edge {from_node} -> {to_node} in flow {session_id}")
        return edge

    def get_summary(self, session_id: str) -> Optional[AgentFlowSummary]:
        """Get flow summary statistics.

        Args:
            session_id: Session identifier

        Returns:
            AgentFlowSummary if flow exists, None otherwise
        """
        flow = self._flows.get(session_id)
        if not flow:
            return None

        completed = [n for n in flow.nodes if n.status == "completed"]
        running = [n for n in flow.nodes if n.status == "running"]
        failed = [n for n in flow.nodes if n.status == "failed"]
        pending = [n for n in flow.nodes if n.status == "pending"]

        # Calculate total duration
        total_duration = None
        start_time = None
        end_time = None

        if completed:
            start_times = [n.start_time for n in flow.nodes if n.start_time]
            end_times = [n.end_time for n in completed if n.end_time]

            if start_times and end_times:
                start_time = datetime.fromtimestamp(min(start_times) / 1000)
                end_time = datetime.fromtimestamp(max(end_times) / 1000)
                total_duration = max(end_times) - min(start_times)

        return AgentFlowSummary(
            session_id=session_id,
            total_nodes=len(flow.nodes),
            completed_nodes=len(completed),
            running_nodes=len(running),
            failed_nodes=len(failed),
            pending_nodes=len(pending),
            total_duration_ms=total_duration,
            start_time=start_time,
            end_time=end_time
        )

    def subscribe(self, session_id: str, callback):
        """Subscribe to flow updates.

        Args:
            session_id: Session identifier
            callback: Callback function for updates
        """
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []
        self._subscribers[session_id].append(callback)

    def unsubscribe(self, session_id: str, callback):
        """Unsubscribe from flow updates.

        Args:
            session_id: Session identifier
            callback: Callback function to remove
        """
        if session_id in self._subscribers:
            self._subscribers[session_id].remove(callback)

    def _notify_subscribers(self, session_id: str, update: AgentFlowUpdate):
        """Notify all subscribers of an update.

        Args:
            session_id: Session identifier
            update: Update message
        """
        if session_id in self._subscribers:
            for callback in self._subscribers[session_id]:
                try:
                    callback(update)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")

    def clear_flow(self, session_id: str):
        """Clear a flow from memory.

        Args:
            session_id: Session identifier
        """
        if session_id in self._flows:
            del self._flows[session_id]
            logger.info(f"Cleared flow {session_id}")

        if session_id in self._subscribers:
            del self._subscribers[session_id]


# Global tracker instance
_tracker: Optional[AgentFlowTracker] = None


def get_tracker() -> AgentFlowTracker:
    """Get or create the global flow tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = AgentFlowTracker()
    return _tracker
