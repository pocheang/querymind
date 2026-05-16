# Implementation Plan: Agent Execution Flow Visualization

**Date**: 2026-05-15  
**Estimated Duration**: 2 days  
**Dependencies**: Plan 1 (Performance Comparison Framework)  
**Related Spec**: [Interview Demo Improvements Design](../specs/2026-05-15-interview-demo-improvements-design.md)

## Objective

Build a real-time visualization system that displays the multi-agent workflow execution, showing how Router, Vector RAG, Graph RAG, Web Research, and Synthesis agents collaborate to answer queries. This provides transparency and demonstrates the system's sophisticated orchestration for interview presentation.

## Scope

### In Scope
- Backend execution tracking service with non-invasive decorator pattern
- Frontend visualization components (flow diagram + timeline views)
- Real-time updates via Server-Sent Events (SSE)
- Agent step details (input, output, decision rationale, timing)
- API endpoints for execution traces and history
- Integration with existing workflow without modifying core logic

### Out of Scope
- Historical execution analytics (future enhancement)
- Agent performance profiling (covered by evaluation framework)
- Interactive workflow debugging tools
- Execution replay functionality

## Architecture

```
app/services/
└── agent_execution_tracker.py   # Execution tracking service

app/api/routes/
└── agent_tracking.py             # API endpoints + SSE

frontend/src/components/agent-visualization/
├── AgentFlowVisualization.tsx    # Main container component
├── AgentFlowDiagram.tsx          # Flow diagram view
├── AgentTimeline.tsx             # Timeline view
├── AgentStepDetail.tsx           # Step detail panel
└── types.ts                      # TypeScript types

app/workflow/
└── orchestrator.py               # Integration point (decorator usage)
```

## File Details

### 1. `app/services/agent_execution_tracker.py` (~200 lines)
**Purpose**: Track agent execution steps and maintain execution traces  
**Key Components**:
- `AgentExecutionTracker` singleton class
- `ExecutionTrace` data model (execution_id, query, steps, status, timestamps)
- `AgentStep` data model (agent_name, start_time, end_time, input_data, output_data, decision_rationale, metadata, status)
- Methods:
  - `start_execution(query)`: Create new execution trace, return execution_id
  - `record_agent_step(execution_id, agent_name, input_data)`: Start tracking agent step
  - `complete_agent_step(execution_id, step_id, output_data, decision)`: Mark step complete
  - `get_execution_trace(execution_id)`: Retrieve full trace
  - `get_recent_executions(limit)`: Get execution history
- In-memory storage with TTL (1 hour) for demo purposes
- Thread-safe implementation using locks

### 2. `app/api/routes/agent_tracking.py` (~150 lines)
**Purpose**: API endpoints for execution tracking and SSE streaming  
**Endpoints**:
- `GET /api/agent-tracking/stream/{execution_id}`: SSE endpoint for real-time updates
- `GET /api/agent-tracking/trace/{execution_id}`: Get complete execution trace
- `GET /api/agent-tracking/history`: List recent executions
- `GET /api/agent-tracking/status/{execution_id}`: Get execution status

**SSE Implementation**:
- Stream agent steps as they complete
- Event format: `{event: "agent_step", data: {...}}`
- Heartbeat every 15 seconds to keep connection alive
- Auto-close on execution completion

### 3. `frontend/src/components/agent-visualization/types.ts` (~80 lines)
**Purpose**: TypeScript type definitions  
**Types**:
```typescript
interface AgentStep {
  stepId: string;
  agentName: 'Router' | 'VectorRAG' | 'GraphRAG' | 'WebResearch' | 'Synthesis';
  startTime: string;
  endTime?: string;
  duration?: number;
  inputData: Record<string, any>;
  outputData?: Record<string, any>;
  decisionRationale?: string;
  status: 'running' | 'completed' | 'failed';
  metadata?: Record<string, any>;
}

interface ExecutionTrace {
  executionId: string;
  query: string;
  steps: AgentStep[];
  status: 'running' | 'completed' | 'failed';
  startTime: string;
  endTime?: string;
  totalDuration?: number;
}

interface AgentNode {
  id: string;
  name: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  position: { x: number; y: number };
}

interface AgentEdge {
  from: string;
  to: string;
  active: boolean;
}
```

### 4. `frontend/src/components/agent-visualization/AgentFlowVisualization.tsx` (~200 lines)
**Purpose**: Main container component with view switching  
**Features**:
- View toggle: Flow Diagram vs Timeline
- SSE connection management
- State management for execution trace
- Error handling and reconnection logic
- Loading states

**State**:
```typescript
const [executionTrace, setExecutionTrace] = useState<ExecutionTrace | null>(null);
const [viewMode, setViewMode] = useState<'flow' | 'timeline'>('flow');
const [selectedStep, setSelectedStep] = useState<AgentStep | null>(null);
const [isConnected, setIsConnected] = useState(false);
```

**SSE Connection**:
- Connect on mount with execution_id from URL params
- Handle incoming agent_step events
- Update execution trace incrementally
- Reconnect on connection loss (max 3 retries)

### 5. `frontend/src/components/agent-visualization/AgentFlowDiagram.tsx` (~180 lines)
**Purpose**: Flow diagram visualization using React Flow  
**Features**:
- Visual representation of agent workflow
- Node states: idle (gray), running (blue pulse), completed (green), failed (red)
- Animated edges showing data flow
- Click on node to show step details
- Auto-layout using dagre algorithm

**Agent Nodes**:
- Router (top center)
- Vector RAG, Graph RAG, Web Research (middle row)
- Synthesis (bottom center)

**Styling**:
- Running agent: pulsing blue border
- Completed agent: green checkmark
- Failed agent: red X icon
- Active edge: animated dashed line

### 6. `frontend/src/components/agent-visualization/AgentTimeline.tsx` (~150 lines)
**Purpose**: Timeline view showing sequential execution  
**Features**:
- Horizontal timeline with agent steps
- Bar chart showing duration of each step
- Color-coded by agent type
- Hover to show step details
- Click to select step and show full details

**Layout**:
- X-axis: Time (relative to execution start)
- Y-axis: Agent names
- Bars: Agent execution periods
- Tooltips: Quick info on hover

### 7. `frontend/src/components/agent-visualization/AgentStepDetail.tsx` (~120 lines)
**Purpose**: Detailed view of selected agent step  
**Sections**:
- Agent name and status badge
- Execution timing (start, end, duration)
- Input data (formatted JSON)
- Output data (formatted JSON)
- Decision rationale (if available)
- Metadata (token usage, model, etc.)

**Styling**:
- Collapsible sections for input/output
- Syntax highlighting for JSON
- Copy button for data
- Status badge with color coding

## Implementation Tasks

### Task 1: Implement Execution Tracking Service
**Duration**: 3 hours  
**Steps**:
1. Create `app/services/agent_execution_tracker.py`
2. Define data models:
   - `AgentStep` (Pydantic model)
   - `ExecutionTrace` (Pydantic model)
3. Implement `AgentExecutionTracker` class:
   - Singleton pattern with `get_instance()`
   - In-memory storage: `Dict[str, ExecutionTrace]`
   - Thread lock for concurrent access
   - TTL cleanup (remove traces older than 1 hour)
4. Implement core methods:
   - `start_execution(query)`: Generate UUID, create trace
   - `record_agent_step(execution_id, agent_name, input_data)`: Add step
   - `complete_agent_step(execution_id, step_id, output_data, decision)`: Update step
   - `fail_agent_step(execution_id, step_id, error)`: Mark step as failed
   - `get_execution_trace(execution_id)`: Retrieve trace
   - `get_recent_executions(limit)`: List recent traces
5. Add logging for debugging
6. Write unit tests

**Verification**:
- [ ] Can create execution trace
- [ ] Can record and complete agent steps
- [ ] Thread-safe (test with concurrent access)
- [ ] TTL cleanup works correctly
- [ ] Unit tests pass

### Task 2: Create Tracking Decorator
**Duration**: 2 hours  
**Steps**:
1. Add decorator function to `agent_execution_tracker.py`:
   ```python
   def track_agent_execution(agent_name: str):
       def decorator(func):
           @wraps(func)
           async def wrapper(*args, **kwargs):
               tracker = AgentExecutionTracker.get_instance()
               execution_id = kwargs.get('execution_id')
               step_id = tracker.record_agent_step(
                   execution_id, agent_name, input_data=kwargs
               )
               try:
                   result = await func(*args, **kwargs)
                   tracker.complete_agent_step(
                       execution_id, step_id, 
                       output_data=result,
                       decision=result.get('decision_rationale')
                   )
                   return result
               except Exception as e:
                   tracker.fail_agent_step(execution_id, step_id, str(e))
                   raise
           return wrapper
       return decorator
   ```
2. Test decorator with mock agent function
3. Document usage in docstring

**Verification**:
- [ ] Decorator captures agent execution
- [ ] Handles both success and failure cases
- [ ] Doesn't interfere with agent logic
- [ ] Works with async functions

### Task 3: Integrate Tracking into Workflow
**Duration**: 2 hours  
**Steps**:
1. Read `app/workflow/orchestrator.py` to understand current structure
2. Add `execution_id` parameter to workflow entry point
3. Apply `@track_agent_execution` decorator to agent methods:
   - `@track_agent_execution("Router")` on router agent
   - `@track_agent_execution("VectorRAG")` on vector RAG agent
   - `@track_agent_execution("GraphRAG")` on graph RAG agent
   - `@track_agent_execution("WebResearch")` on web research agent
   - `@track_agent_execution("Synthesis")` on synthesis agent
4. Pass `execution_id` through workflow chain
5. Test with sample query
6. Verify execution trace is captured correctly

**Verification**:
- [ ] All agents are tracked
- [ ] Execution trace shows complete workflow
- [ ] Timing data is accurate
- [ ] No impact on workflow functionality

### Task 4: Implement API Endpoints
**Duration**: 3 hours  
**Steps**:
1. Create `app/api/routes/agent_tracking.py`
2. Implement SSE endpoint:
   ```python
   @router.get("/stream/{execution_id}")
   async def stream_execution(execution_id: str):
       async def event_generator():
           tracker = AgentExecutionTracker.get_instance()
           last_step_count = 0
           while True:
               trace = tracker.get_execution_trace(execution_id)
               if not trace:
                   yield f"data: {json.dumps({'error': 'Not found'})}\n\n"
                   break
               
               # Send new steps
               if len(trace.steps) > last_step_count:
                   for step in trace.steps[last_step_count:]:
                       yield f"event: agent_step\ndata: {step.json()}\n\n"
                   last_step_count = len(trace.steps)
               
               # Check if complete
               if trace.status in ['completed', 'failed']:
                   yield f"event: execution_complete\ndata: {trace.json()}\n\n"
                   break
               
               await asyncio.sleep(0.5)
       
       return StreamingResponse(event_generator(), media_type="text/event-stream")
   ```
3. Implement other endpoints:
   - `GET /trace/{execution_id}`: Return full trace as JSON
   - `GET /history`: Return recent executions (last 20)
   - `GET /status/{execution_id}`: Return execution status
4. Add error handling and validation
5. Register routes in `app/api/main.py`
6. Test endpoints with curl
7. Write API tests

**Verification**:
- [ ] SSE endpoint streams updates in real-time
- [ ] Can retrieve full execution trace
- [ ] History endpoint returns recent executions
- [ ] Error handling works correctly
- [ ] API tests pass

### Task 5: Implement Frontend Types and State Management
**Duration**: 2 hours  
**Steps**:
1. Create `frontend/src/components/agent-visualization/types.ts`
2. Define TypeScript interfaces (AgentStep, ExecutionTrace, AgentNode, AgentEdge)
3. Create `frontend/src/components/agent-visualization/hooks/useExecutionTrace.ts`:
   - Custom hook for SSE connection
   - State management for execution trace
   - Reconnection logic
4. Create `frontend/src/components/agent-visualization/utils/formatters.ts`:
   - Format duration (ms to human-readable)
   - Format timestamps
   - Format JSON with syntax highlighting
5. Test type definitions with sample data

**Verification**:
- [ ] Types compile without errors
- [ ] useExecutionTrace hook connects to SSE
- [ ] State updates correctly on new events
- [ ] Formatters produce correct output

### Task 6: Implement Flow Diagram Component
**Duration**: 4 hours  
**Steps**:
1. Install dependencies: `npm install reactflow dagre`
2. Create `frontend/src/components/agent-visualization/AgentFlowDiagram.tsx`
3. Define agent node positions:
   ```typescript
   const agentPositions = {
     Router: { x: 400, y: 50 },
     VectorRAG: { x: 200, y: 200 },
     GraphRAG: { x: 400, y: 200 },
     WebResearch: { x: 600, y: 200 },
     Synthesis: { x: 400, y: 350 }
   };
   ```
4. Implement node rendering:
   - Custom node component with status indicator
   - Pulsing animation for running state
   - Icon for completed/failed state
5. Implement edge rendering:
   - Animated edges for active connections
   - Static edges for inactive connections
6. Add click handlers:
   - Click node to show step details
   - Highlight active path
7. Style with Tailwind CSS
8. Test with sample execution trace

**Verification**:
- [ ] Flow diagram renders correctly
- [ ] Node states update in real-time
- [ ] Animations work smoothly
- [ ] Click handlers trigger correctly
- [ ] Responsive layout

### Task 7: Implement Timeline Component
**Duration**: 3 hours  
**Steps**:
1. Create `frontend/src/components/agent-visualization/AgentTimeline.tsx`
2. Use Recharts for timeline visualization:
   ```typescript
   <BarChart data={timelineData} layout="horizontal">
     <XAxis type="number" domain={[0, totalDuration]} />
     <YAxis type="category" dataKey="agentName" />
     <Bar dataKey="duration" fill="#3b82f6" />
     <Tooltip content={<CustomTooltip />} />
   </BarChart>
   ```
3. Transform execution trace to timeline data:
   - Calculate relative start times
   - Calculate durations
   - Color-code by agent
4. Implement custom tooltip:
   - Show agent name, start time, duration
   - Show status badge
5. Add click handler to select step
6. Style with Tailwind CSS
7. Test with sample execution trace

**Verification**:
- [ ] Timeline renders correctly
- [ ] Bars show correct durations
- [ ] Tooltip shows correct information
- [ ] Click selects step
- [ ] Responsive layout

### Task 8: Implement Step Detail Component
**Duration**: 2 hours  
**Steps**:
1. Create `frontend/src/components/agent-visualization/AgentStepDetail.tsx`
2. Implement collapsible sections:
   - Use Headless UI Disclosure component
   - Sections: Input, Output, Decision, Metadata
3. Add JSON syntax highlighting:
   - Use `react-json-view` library
   - Or implement custom syntax highlighting
4. Add copy-to-clipboard button:
   - Use `navigator.clipboard.writeText()`
   - Show toast notification on copy
5. Style with Tailwind CSS:
   - Status badge with color coding
   - Monospace font for JSON
   - Smooth transitions for collapsible sections
6. Test with sample agent step

**Verification**:
- [ ] All sections render correctly
- [ ] Collapsible sections work smoothly
- [ ] JSON is formatted and highlighted
- [ ] Copy button works
- [ ] Responsive layout

### Task 9: Implement Main Container Component
**Duration**: 3 hours  
**Steps**:
1. Create `frontend/src/components/agent-visualization/AgentFlowVisualization.tsx`
2. Implement view toggle:
   - Tabs for Flow Diagram and Timeline
   - Persist view preference in localStorage
3. Integrate SSE connection:
   - Use `useExecutionTrace` hook
   - Show connection status indicator
   - Handle reconnection
4. Implement layout:
   - Main visualization area (70% width)
   - Step detail sidebar (30% width)
   - Collapsible sidebar
5. Add loading and error states:
   - Loading spinner while connecting
   - Error message on connection failure
   - Retry button
6. Add header with execution info:
   - Query text
   - Execution status
   - Total duration
7. Style with Tailwind CSS
8. Test with real execution

**Verification**:
- [ ] View toggle works correctly
- [ ] SSE connection establishes successfully
- [ ] Real-time updates display correctly
- [ ] Step detail sidebar shows selected step
- [ ] Loading and error states work
- [ ] Responsive layout

### Task 10: Integration Testing
**Duration**: 2 hours  
**Steps**:
1. Start backend server
2. Run a test query through the workflow
3. Open visualization page with execution_id
4. Verify:
   - SSE connection establishes
   - Agent steps appear in real-time
   - Flow diagram updates correctly
   - Timeline shows accurate timing
   - Step details display correctly
5. Test edge cases:
   - Agent failure (simulate error)
   - Long-running execution
   - Multiple concurrent executions
6. Test on different browsers (Chrome, Firefox, Safari)
7. Test responsive layout on mobile
8. Fix any issues found

**Verification**:
- [ ] End-to-end flow works correctly
- [ ] Real-time updates are smooth
- [ ] All components display correctly
- [ ] Edge cases handled gracefully
- [ ] Works on all major browsers
- [ ] Responsive on mobile

## Testing Strategy

### Unit Tests
- Test execution tracker methods
- Test decorator functionality
- Test data model validation
- Test API endpoint logic (mock tracker)

### Integration Tests
- Test SSE streaming with real tracker
- Test workflow integration (end-to-end)
- Test frontend components with mock data

### Manual Testing
- Test real-time visualization with live queries
- Test different query types (simple, complex, multi-agent)
- Test error scenarios (agent failure, timeout)
- Test UI responsiveness and animations

## Acceptance Criteria

- [ ] Execution tracking service implemented and tested
- [ ] Decorator pattern integrated into workflow without modifying core logic
- [ ] API endpoints functional (SSE streaming, trace retrieval, history)
- [ ] Frontend components render correctly (flow diagram, timeline, step details)
- [ ] Real-time updates work smoothly via SSE
- [ ] Can visualize complete agent workflow execution
- [ ] Step details show input, output, decision rationale, and timing
- [ ] View toggle between flow diagram and timeline works
- [ ] Error handling and reconnection logic work correctly
- [ ] All unit and integration tests pass
- [ ] Code follows project style (type hints, docstrings, error handling)
- [ ] Documentation updated (README, API docs, component docs)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SSE connection drops during long executions | Medium | Implement reconnection logic with exponential backoff |
| Decorator adds overhead to agent execution | Low | Minimize tracking logic, use async operations |
| Frontend state management becomes complex | Medium | Use custom hook to encapsulate SSE logic |
| Flow diagram layout is hard to read | Low | Use dagre for auto-layout, allow manual adjustment |

## Dependencies

- Plan 1 (Performance Comparison Framework) for evaluation context
- Existing workflow orchestrator
- React Flow library for flow diagram
- Recharts library for timeline
- SSE support in FastAPI

## Next Steps

After completing this plan:
1. Proceed to Plan 3: Chinese NLP Optimization
2. Use execution traces to identify performance bottlenecks
3. Integrate visualization into demo page
4. Add execution trace export functionality (future enhancement)
