# Agent Execution Tracking

A real-time monitoring system for tracking multi-agent workflow execution in the RAG system. This feature provides visibility into agent decision-making, execution flow, and performance metrics.

## Overview

The Agent Execution Tracking system captures detailed information about each step in a multi-agent workflow, including:

- **Execution traces**: Complete records of workflow runs
- **Agent steps**: Individual agent invocations with inputs, outputs, and timing
- **Real-time streaming**: Server-Sent Events (SSE) for live updates
- **Performance metrics**: Duration, status, and error tracking

## Architecture

### Core Components

1. **AgentExecutionTracker** (`app/services/agent_execution_tracker.py`)
   - Thread-safe service for tracking executions
   - In-memory storage with TTL-based cleanup
   - Singleton pattern via `get_tracker()`

2. **Data Models** (`app/services/agent_execution_tracker.py`)
   - `ExecutionTrace`: Complete execution record
   - `AgentStep`: Individual agent step details

3. **API Endpoints** (`app/api/routes/agent_tracking.py`)
   - REST API for querying execution traces
   - SSE streaming for real-time updates

4. **Workflow Integration** (`app/graph/workflow.py`)
   - Non-invasive decorator-based tracking
   - Automatic execution ID propagation

## Usage

### Basic Tracking

```python
from app.graph.workflow import run_query
from app.services.agent_execution_tracker import get_tracker

# Run a query with tracking enabled (default)
result = run_query(
    question="What are the main features of RAG?",
    enable_tracking=True
)

# Get the execution ID
execution_id = result.get("execution_id")

# Retrieve the trace
tracker = get_tracker()
trace = tracker.get_execution(execution_id)

print(f"Status: {trace.status}")
print(f"Steps: {len(trace.steps)}")
for step in trace.steps:
    print(f"  - {step.agent_name}: {step.status} ({step.duration_seconds:.2f}s)")
```

### Custom Agent Tracking

Use the `@track_agent_execution` decorator to track custom agent functions:

```python
from app.services.agent_execution_tracker import track_agent_execution

@track_agent_execution(agent_name="CustomAgent")
def my_custom_agent(query: str, execution_id: str = None) -> dict:
    # Your agent logic here
    result = process_query(query)
    return {"output": result}

# The decorator automatically:
# - Records the step start
# - Captures input data
# - Tracks duration
# - Records output or errors
# - Updates step status
```

### Async Agent Tracking

The decorator also supports async functions:

```python
@track_agent_execution(agent_name="AsyncAgent")
async def my_async_agent(query: str, execution_id: str = None) -> dict:
    result = await async_process(query)
    return {"output": result}
```

## API Reference

### REST Endpoints

#### Get Execution Trace

```http
GET /api/agent-tracking/executions/{execution_id}
```

Returns the complete execution trace including all steps.

**Response:**
```json
{
  "execution_id": "uuid",
  "query": "What is RAG?",
  "start_time": "2026-05-15T10:30:00Z",
  "end_time": "2026-05-15T10:30:05Z",
  "status": "completed",
  "steps": [
    {
      "step_id": "uuid",
      "agent_name": "router",
      "start_time": "2026-05-15T10:30:00Z",
      "end_time": "2026-05-15T10:30:01Z",
      "status": "completed",
      "input_data": {"query": "What is RAG?"},
      "output_data": {"route": "vector"},
      "duration_seconds": 1.0
    }
  ]
}
```

#### Stream Execution Updates

```http
GET /api/agent-tracking/executions/{execution_id}/stream
```

Returns a Server-Sent Events (SSE) stream with real-time updates.

**Client Example:**
```javascript
const eventSource = new EventSource(
  `/api/agent-tracking/executions/${executionId}/stream`
);

eventSource.onmessage = (event) => {
  const trace = JSON.parse(event.data);
  console.log('New step:', trace.steps[trace.steps.length - 1]);
};

eventSource.onerror = () => {
  eventSource.close();
};
```

#### List Recent Executions

```http
GET /api/agent-tracking/executions?limit=10
```

Returns a list of recent execution traces.

**Query Parameters:**
- `limit` (optional): Maximum number of executions to return (default: 10)

#### Delete Execution

```http
DELETE /api/agent-tracking/executions/{execution_id}
```

Deletes a specific execution trace.

#### Cleanup Old Traces

```http
POST /api/agent-tracking/cleanup?hours_old=24
```

Removes execution traces older than the specified hours.

**Query Parameters:**
- `hours_old` (optional): Age threshold in hours (default: 24)

## Data Models

### ExecutionTrace

| Field | Type | Description |
|-------|------|-------------|
| `execution_id` | string | Unique identifier for the execution |
| `query` | string | The original user query |
| `start_time` | datetime | When execution started |
| `end_time` | datetime | When execution completed (null if running) |
| `status` | string | "running", "completed", or "failed" |
| `steps` | list | List of AgentStep objects |
| `result` | dict | Final workflow result (optional) |
| `error` | string | Error message if failed (optional) |

### AgentStep

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | string | Unique identifier for the step |
| `agent_name` | string | Name of the agent |
| `start_time` | datetime | When step started |
| `end_time` | datetime | When step completed (null if running) |
| `status` | string | "running", "completed", or "failed" |
| `input_data` | dict | Input parameters to the agent |
| `output_data` | dict | Output from the agent (optional) |
| `error` | string | Error message if failed (optional) |
| `duration_seconds` | float | Step duration in seconds (optional) |

## Configuration

### TTL (Time-To-Live)

By default, execution traces are kept for 24 hours. Configure this when initializing the tracker:

```python
from app.services.agent_execution_tracker import AgentExecutionTracker

tracker = AgentExecutionTracker(ttl_hours=48)  # Keep for 48 hours
```

### Disabling Tracking

To disable tracking for specific queries:

```python
result = run_query(
    question="What is RAG?",
    enable_tracking=False  # Disable tracking
)
```

## Frontend Integration

### TypeScript Types

```typescript
interface ExecutionTrace {
  execution_id: string;
  query: string;
  start_time: string;
  end_time: string | null;
  status: 'running' | 'completed' | 'failed';
  steps: AgentStep[];
  result?: any;
  error?: string;
}

interface AgentStep {
  step_id: string;
  agent_name: string;
  start_time: string;
  end_time: string | null;
  status: 'running' | 'completed' | 'failed';
  input_data: Record<string, any>;
  output_data?: Record<string, any>;
  error?: string;
  duration_seconds?: number;
}
```

### React Hook Example

```typescript
import { useEffect, useState } from 'react';

function useExecutionTracking(executionId: string) {
  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(
      `/api/agent-tracking/executions/${executionId}/stream`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        setError(data.error);
        eventSource.close();
      } else {
        setTrace(data);
        if (data.status === 'completed' || data.status === 'failed') {
          eventSource.close();
        }
      }
    };

    eventSource.onerror = () => {
      setError('Connection lost');
      eventSource.close();
    };

    return () => eventSource.close();
  }, [executionId]);

  return { trace, error };
}
```

## Testing

### Unit Tests

Run the unit tests:

```bash
pytest tests/unit/test_agent_execution_tracker.py -v
pytest tests/unit/test_agent_tracking_api.py -v
```

### Integration Testing

```python
from app.services.agent_execution_tracker import get_tracker
from app.graph.workflow import run_query

def test_end_to_end_tracking():
    tracker = get_tracker()
    
    # Run a query
    result = run_query("Test query", enable_tracking=True)
    execution_id = result.get("execution_id")
    
    # Verify tracking
    trace = tracker.get_execution(execution_id)
    assert trace is not None
    assert trace.status == "completed"
    assert len(trace.steps) > 0
    
    # Verify each step
    for step in trace.steps:
        assert step.agent_name in [
            "router", "adaptive_planner", "entry_decider",
            "vector", "vector_decider", "graph", "graph_decider",
            "web", "synthesis"
        ]
        assert step.status == "completed"
        assert step.duration_seconds is not None
```

## Performance Considerations

### Memory Usage

- Execution traces are stored in-memory
- Automatic cleanup after TTL expires (default: 24 hours)
- Manual cleanup via API: `POST /api/agent-tracking/cleanup`

### Overhead

- Minimal performance impact (~1-5ms per step)
- Thread-safe operations with fine-grained locking
- Non-blocking SSE streaming

### Scalability

For production deployments with high query volume:

1. **Reduce TTL**: Lower the retention period to reduce memory usage
2. **Selective Tracking**: Disable tracking for simple queries
3. **External Storage**: Consider persisting traces to a database
4. **Sampling**: Track only a percentage of executions

## Troubleshooting

### Execution ID Not Found

If `execution_id` is missing from the result:

```python
# Check if tracking is enabled
result = run_query(question="...", enable_tracking=True)

# Verify the tracker is initialized
from app.services.agent_execution_tracker import get_tracker
tracker = get_tracker()
print(f"Tracker initialized: {tracker is not None}")
```

### SSE Connection Issues

If the SSE stream disconnects:

1. Check network connectivity
2. Verify the execution ID exists
3. Ensure the execution hasn't already completed
4. Check browser console for errors

### Missing Steps

If some agent steps are not tracked:

1. Verify the agent function has the `@track_agent_execution` decorator
2. Ensure `execution_id` is passed to the agent function
3. Check that the decorator is applied correctly (before async def)

## Future Enhancements

Planned improvements:

- [ ] Persistent storage (PostgreSQL/MongoDB)
- [ ] Metrics aggregation and analytics
- [ ] Performance profiling and bottleneck detection
- [ ] Distributed tracing support (OpenTelemetry)
- [ ] Custom metadata and tags
- [ ] Execution replay and debugging tools
- [ ] Integration with monitoring systems (Prometheus, Grafana)

## Related Documentation

- [Performance Comparison Framework](performance_comparison_framework.md)
- [Workflow Architecture](workflow_architecture.md)
- [API Documentation](api_documentation.md)
