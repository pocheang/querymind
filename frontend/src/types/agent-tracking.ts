/**
 * TypeScript types for Agent Execution Tracking
 *
 * These types correspond to the Pydantic models in:
 * app/services/agent_execution_tracker.py
 */

/**
 * Status of an execution or step
 */
export type ExecutionStatus = 'running' | 'completed' | 'failed';

/**
 * Individual agent step in the workflow
 */
export interface AgentStep {
  /** Unique identifier for this step */
  step_id: string;

  /** Name of the agent that executed this step */
  agent_name: string;

  /** ISO 8601 timestamp when step started */
  start_time: string;

  /** ISO 8601 timestamp when step completed (null if still running) */
  end_time: string | null;

  /** Current status of the step */
  status: ExecutionStatus;

  /** Input data passed to the agent */
  input_data: Record<string, any>;

  /** Output data returned by the agent (null if not completed) */
  output_data?: Record<string, any> | null;

  /** Decision rationale for this step */
  decision_rationale?: string | null;

  /** Error message if step failed */
  error?: string | null;

  /** Duration in milliseconds (null if not completed) */
  duration_ms?: number | null;

  /** Additional metadata for the step */
  metadata?: Record<string, any>;
}

/**
 * Complete execution trace for a workflow run
 */
export interface ExecutionTrace {
  /** Unique identifier for this execution */
  execution_id: string;

  /** The original user query */
  query: string;

  /** User ID who initiated this execution (for data isolation) */
  user_id?: string | null;

  /** ISO 8601 timestamp when execution started */
  start_time: string;

  /** ISO 8601 timestamp when execution completed (null if still running) */
  end_time: string | null;

  /** Current status of the execution */
  status: ExecutionStatus;

  /** List of agent steps in execution order */
  steps: AgentStep[];

  /** Total duration in milliseconds (null if not completed) */
  total_duration_ms?: number | null;

  /** Additional metadata including final result */
  metadata?: Record<string, any>;

  /** Error message if execution failed */
  error?: string | null;
}

/**
 * Response from the list executions endpoint
 */
export interface ExecutionListResponse {
  executions: ExecutionTrace[];
  total: number;
}

/**
 * Response from the execution status endpoint
 */
export interface ExecutionStatusResponse {
  execution_id: string;
  status: ExecutionStatus;
  query: string;
  step_count: number;
  start_time: string;
  end_time?: string | null;
  total_duration_ms?: number | null;
}

/**
 * Request body for cleanup endpoint
 */
export interface CleanupRequest {
  hours_old?: number;
}

/**
 * Response from cleanup endpoint
 */
export interface CleanupResponse {
  deleted_count: number;
}

/**
 * Error response from API
 */
export interface ApiError {
  detail: string;
}

/**
 * SSE event data
 */
export interface SSEEvent {
  data: string;
  event?: string;
  id?: string;
}

/**
 * Visualization node for flow diagram
 */
export interface FlowNode {
  id: string;
  type: 'agent' | 'decision' | 'start' | 'end';
  data: {
    label: string;
    status?: ExecutionStatus;
    duration?: number;
    error?: string;
  };
  position: { x: number; y: number };
}

/**
 * Visualization edge for flow diagram
 */
export interface FlowEdge {
  id: string;
  source: string;
  target: string;
  animated?: boolean;
  label?: string;
}

/**
 * Timeline event for visualization
 */
export interface TimelineEvent {
  id: string;
  agent_name: string;
  start_time: Date;
  end_time: Date | null;
  duration: number | null;
  status: ExecutionStatus;
}

/**
 * Statistics for execution analysis
 */
export interface ExecutionStats {
  total_duration: number;
  step_count: number;
  completed_steps: number;
  failed_steps: number;
  average_step_duration: number;
  slowest_step: {
    agent_name: string;
    duration: number;
  } | null;
  fastest_step: {
    agent_name: string;
    duration: number;
  } | null;
}
