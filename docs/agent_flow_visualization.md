# Agent Execution Flow Visualization

This document describes the agent execution flow visualization feature, which provides real-time tracking and visualization of multi-agent workflow execution.

## Overview

The agent flow visualization system tracks the execution of agents in the LangGraph workflow and provides:

- Real-time visualization of agent execution flow
- Node status tracking (pending, running, completed, failed)
- Execution timing and performance metrics
- WebSocket-based live updates
- Interactive flow diagram in the frontend

## Architecture

### Backend Components

#### 1. Data Models (`app/models/agent_flow.py`)

**AgentNode**: Represents a single agent in the execution flow
- `id`: Unique identifier
- `name`: Display name
- `type`: Agent type (router, retriever, generator, evaluator, tool)
- `status`: Execution status (pending, running, completed, failed)
- `start_time`, `end_time`: Timing information
- `input_data`, `output_data`: Agent I/O
- `error`: Error message if failed

**AgentEdge**: Represents connections between agents
- `from_node`, `to_node`: Source and target node IDs
- `label`: Edge description
- `condition`: Conditional routing logic

**AgentFlowData**: Complete flow execution data
- `session_id`: Session identifier
- `nodes`: List of agent nodes
- `edges`: List of edges
- `current_node`: Currently executing node

#### 2. Flow Tracker Service (`app/services/agent_flow_tracker.py`)

The `AgentFlowTracker` class manages flow state and provides methods for:

- `create_flow(session_id)`: Initialize a new flow
- `add_node(...)`: Add an agent node to the flow
- `start_node(session_id, node_id)`: Mark node as running
- `complete_node(session_id, node_id, output_data)`: Mark node as completed
- `fail_node(session_id, node_id, error)`: Mark node as failed
- `add_edge(...)`: Add connection between nodes
- `get_summary(session_id)`: Get flow statistics
- `subscribe(session_id, callback)`: Subscribe to flow updates

#### 3. API Routes (`app/api/routes/agent_flow.py`)

**REST Endpoints:**
- `GET /api/agent-flow/{session_id}`: Get complete flow data
- `GET /api/agent-flow/{session_id}/summary`: Get flow summary statistics
- `DELETE /api/agent-flow/{session_id}`: Clear flow data

**WebSocket Endpoint:**
- `WS /api/agent-flow/ws/{session_id}`: Real-time flow updates

#### 4. LangGraph Instrumentation (`app/graph/flow_instrumentation.py`)

**Decorator for Agent Nodes:**
```python
@track_agent_node("Router Agent", "router")
async def router_node(state):
    # Agent logic here
    return updated_state
```

**Edge Tracking:**
```python
track_edge("router", "retriever", condition="route == 'vector_rag'")(state)
```

**Context Manager:**
```python
async with FlowInstrumentationContext(session_id):
    # Run workflow
    result = await workflow.ainvoke(state)
```

### Frontend Components

#### 1. Main Visualization Component (`frontend/src/components/AgentFlowVisualization.tsx`)

React component that renders the agent execution flow:

```typescript
<AgentFlowVisualization
  executionData={flowData}
  onNodeClick={(nodeId) => console.log(nodeId)}
/>
```

**Features:**
- Displays all agent nodes with status indicators
- Shows connections between agents
- Highlights currently executing node
- Provides execution statistics
- Supports node click interactions

#### 2. Flow Tracker Hook (`frontend/src/hooks/useAgentFlowTracker.ts`)

Custom React hook for tracking flow execution:

```typescript
const { executionData, isTracking, startTracking, stopTracking } = 
  useAgentFlowTracker(sessionId);
```

**Features:**
- WebSocket connection management
- Real-time data updates
- Automatic reconnection
- State management

## Usage Guide

### Backend Integration

#### Step 1: Instrument Your Workflow

Add the `session_id` to your workflow state:

```python
from app.graph.flow_instrumentation import instrument_workflow_state

state = {
    "question": "What is RAG?",
    # ... other state
}

state = instrument_workflow_state(state, session_id="user-session-123")
```

#### Step 2: Decorate Agent Nodes

Wrap your agent functions with the tracking decorator:

```python
from app.graph.flow_instrumentation import track_agent_node

@track_agent_node("Router Agent", "router")
async def router_agent(state):
    # Determine routing
    route = classify_query(state["question"])
    return {"route": route}

@track_agent_node("Vector RAG Agent", "retriever")
async def vector_rag_agent(state):
    # Retrieve documents
    docs = await retrieve_documents(state["question"])
    return {"documents": docs}

@track_agent_node("Answer Generator", "generator")
async def generator_agent(state):
    # Generate answer
    answer = await generate_answer(state["question"], state["documents"])
    return {"answer": answer}
```

#### Step 3: Track Edges (Optional)

Add edge tracking for conditional routing:

```python
from app.graph.flow_instrumentation import track_edge

# After routing decision
if route == "vector_rag":
    track_edge("router", "vector_rag", condition="route == 'vector_rag'")(state)
elif route == "web_search":
    track_edge("router", "web_search", condition="route == 'web_search'")(state)
```

#### Step 4: Use Context Manager

Wrap your workflow execution:

```python
from app.graph.flow_instrumentation import FlowInstrumentationContext

async with FlowInstrumentationContext(session_id):
    result = await workflow.ainvoke(state)
```

### Frontend Integration

#### Step 1: Import Components

```typescript
import { AgentFlowVisualization } from '@/components/AgentFlowVisualization';
import { useAgentFlowTracker } from '@/hooks/useAgentFlowTracker';
```

#### Step 2: Use the Hook

```typescript
function ChatInterface() {
  const [sessionId, setSessionId] = useState<string>('');
  const { executionData, isTracking, startTracking, stopTracking } = 
    useAgentFlowTracker(sessionId);

  const handleQuerySubmit = async (question: string) => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    startTracking();
    
    // Submit query to backend
    await submitQuery(question, newSessionId);
  };

  return (
    <div>
      {executionData && (
        <AgentFlowVisualization
          executionData={executionData}
          onNodeClick={(nodeId) => console.log('Clicked:', nodeId)}
        />
      )}
    </div>
  );
}
```

## API Reference

### REST API

#### Get Flow Data

```http
GET /api/agent-flow/{session_id}
```

**Response:**
```json
{
  "session_id": "session-123",
  "nodes": [
    {
      "id": "router-1",
      "name": "Router Agent",
      "type": "router",
      "status": "completed",
      "start_time": 1234567890000,
      "end_time": 1234567891000,
      "input_data": {"question": "What is RAG?"},
      "output_data": {"route": "vector_rag"}
    }
  ],
  "edges": [
    {
      "from": "router-1",
      "to": "retriever-1",
      "label": "route to vector RAG",
      "condition": "route == 'vector_rag'"
    }
  ],
  "current_node": null,
  "created_at": "2026-05-16T10:00:00Z",
  "updated_at": "2026-05-16T10:00:05Z"
}
```

#### Get Flow Summary

```http
GET /api/agent-flow/{session_id}/summary
```

**Response:**
```json
{
  "session_id": "session-123",
  "total_nodes": 4,
  "completed_nodes": 3,
  "running_nodes": 1,
  "failed_nodes": 0,
  "pending_nodes": 0,
  "total_duration_ms": 5000,
  "start_time": "2026-05-16T10:00:00Z",
  "end_time": "2026-05-16T10:00:05Z"
}
```

### WebSocket API

#### Connect

```javascript
const ws = new WebSocket('ws://localhost:8000/api/agent-flow/ws/session-123');
```

#### Message Types

**Flow Initialization:**
```json
{
  "type": "flow_init",
  "data": { /* AgentFlowData */ },
  "timestamp": 1234567890000
}
```

**Node Added:**
```json
{
  "type": "node_add",
  "data": { /* AgentNode */ },
  "timestamp": 1234567890000
}
```

**Node Updated:**
```json
{
  "type": "node_update",
  "data": { /* AgentNode */ },
  "timestamp": 1234567890000
}
```

**Edge Added:**
```json
{
  "type": "edge_add",
  "data": { /* AgentEdge */ },
  "timestamp": 1234567890000
}
```

## Performance Considerations

1. **Memory Management**: Flows are stored in memory. Use `clear_flow()` to clean up old sessions.

2. **WebSocket Connections**: Each session can have multiple WebSocket subscribers. Connections are automatically cleaned up on disconnect.

3. **Update Frequency**: Updates are sent immediately when node status changes. No polling required.

4. **Scalability**: For production deployments with many concurrent users, consider:
   - Using Redis for flow state storage
   - Implementing flow data expiration
   - Rate limiting WebSocket connections

## Testing

Run the unit tests:

```bash
pytest tests/unit/test_agent_flow_tracker.py
pytest tests/unit/test_flow_instrumentation.py
```

## Example: Complete Integration

```python
# Backend: app/graph/workflow.py
from app.graph.flow_instrumentation import (
    track_agent_node,
    track_edge,
    FlowInstrumentationContext,
    instrument_workflow_state
)

@track_agent_node("Router", "router")
async def router_node(state):
    route = await classify_query(state["question"])
    return {"route": route}

@track_agent_node("Vector RAG", "retriever")
async def vector_rag_node(state):
    docs = await retrieve_documents(state["question"])
    return {"documents": docs}

@track_agent_node("Generator", "generator")
async def generator_node(state):
    answer = await generate_answer(state["question"], state["documents"])
    return {"answer": answer}

async def run_workflow(question: str, session_id: str):
    state = {"question": question}
    state = instrument_workflow_state(state, session_id)
    
    async with FlowInstrumentationContext(session_id):
        # Build workflow
        workflow = StateGraph(...)
        workflow.add_node("router", router_node)
        workflow.add_node("vector_rag", vector_rag_node)
        workflow.add_node("generator", generator_node)
        
        # Add edges with tracking
        workflow.add_conditional_edges(
            "router",
            lambda s: s["route"],
            {
                "vector_rag": "vector_rag",
                "web_search": "web_search"
            }
        )
        
        # Execute
        result = await workflow.ainvoke(state)
        return result
```

## Troubleshooting

### WebSocket Connection Issues

If WebSocket connections fail:
1. Check CORS settings in `app/api/main.py`
2. Verify WebSocket URL matches your backend
3. Check browser console for connection errors

### Missing Flow Data

If flow data is not appearing:
1. Ensure `session_id` is added to workflow state
2. Verify decorators are applied to agent functions
3. Check that `FlowInstrumentationContext` wraps execution

### Performance Issues

If visualization is slow:
1. Reduce update frequency by batching node updates
2. Limit number of nodes displayed
3. Clear old flow data regularly

## Future Enhancements

- [ ] Persistent flow storage (database)
- [ ] Flow replay functionality
- [ ] Performance analytics dashboard
- [ ] Export flow diagrams as images
- [ ] Flow comparison between sessions
- [ ] Advanced filtering and search
