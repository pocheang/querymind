"""Agent flow tracking models and data structures."""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class AgentNode(BaseModel):
    """Represents a single agent node in the execution flow."""

    id: str = Field(..., description="Unique identifier for the node")
    name: str = Field(..., description="Display name of the agent")
    type: Literal["router", "retriever", "generator", "evaluator", "tool"] = Field(
        ..., description="Type of agent"
    )
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending", description="Current execution status"
    )
    start_time: Optional[float] = Field(None, description="Start timestamp in milliseconds")
    end_time: Optional[float] = Field(None, description="End timestamp in milliseconds")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Input data to the agent")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data from the agent")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class AgentEdge(BaseModel):
    """Represents a connection between two agent nodes."""

    from_node: str = Field(..., alias="from", description="Source node ID")
    to_node: str = Field(..., alias="to", description="Target node ID")
    label: Optional[str] = Field(None, description="Edge label")
    condition: Optional[str] = Field(None, description="Condition for this edge")

    class Config:
        populate_by_name = True


class AgentFlowData(BaseModel):
    """Complete agent flow execution data."""

    session_id: str = Field(..., description="Session identifier")
    nodes: List[AgentNode] = Field(default_factory=list, description="List of agent nodes")
    edges: List[AgentEdge] = Field(default_factory=list, description="List of edges between nodes")
    current_node: Optional[str] = Field(None, description="Currently executing node ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Flow creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")


class AgentFlowUpdate(BaseModel):
    """Update message for agent flow changes."""

    type: Literal["flow_init", "node_update", "node_add", "edge_add", "flow_complete"] = Field(
        ..., description="Type of update"
    )
    data: Dict[str, Any] = Field(..., description="Update data")
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp() * 1000)


class AgentFlowSummary(BaseModel):
    """Summary statistics for an agent flow execution."""

    session_id: str
    total_nodes: int
    completed_nodes: int
    running_nodes: int
    failed_nodes: int
    pending_nodes: int
    total_duration_ms: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
