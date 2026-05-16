/**
 * React hooks for Agent Execution Tracking
 *
 * Provides hooks for:
 * - Real-time execution tracking via SSE
 * - Fetching execution traces
 * - Managing execution history
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import {
  ExecutionTrace,
  ExecutionListResponse,
  ExecutionStatusResponse,
  ExecutionStats,
  TimelineEvent,
} from '../types/agent-tracking';

const API_BASE = '/api/agent-tracking';

/**
 * Hook for tracking a single execution in real-time via SSE
 *
 * @param executionId - The execution ID to track
 * @param enabled - Whether to enable tracking (default: true)
 * @returns Execution trace, loading state, and error
 *
 * @example
 * ```tsx
 * function ExecutionViewer({ executionId }: { executionId: string }) {
 *   const { trace, isLoading, error } = useExecutionTracking(executionId);
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error}</div>;
 *   if (!trace) return null;
 *
 *   return (
 *     <div>
 *       <h2>Status: {trace.status}</h2>
 *       <p>Steps: {trace.steps.length}</p>
 *     </div>
 *   );
 * }
 * ```
 */
export function useExecutionTracking(executionId: string, enabled: boolean = true) {
  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !executionId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    // Create SSE connection
    const eventSource = new EventSource(
      `${API_BASE}/executions/${executionId}/stream`
    );
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          setError(data.error);
          setIsLoading(false);
          eventSource.close();
          return;
        }

        setTrace(data);
        setIsLoading(false);

        // Close connection when execution completes
        if (data.status === 'completed' || data.status === 'failed') {
          eventSource.close();
        }
      } catch (err) {
        setError('Failed to parse execution data');
        setIsLoading(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setError('Connection lost');
      setIsLoading(false);
      eventSource.close();
    };

    // Cleanup on unmount
    return () => {
      eventSource.close();
    };
  }, [executionId, enabled]);

  return { trace, isLoading, error };
}

/**
 * Hook for fetching a single execution trace (non-streaming)
 *
 * @param executionId - The execution ID to fetch
 * @returns Execution trace, loading state, error, and refetch function
 *
 * @example
 * ```tsx
 * function ExecutionDetails({ executionId }: { executionId: string }) {
 *   const { trace, isLoading, error, refetch } = useExecutionTrace(executionId);
 *
 *   return (
 *     <div>
 *       <button onClick={refetch}>Refresh</button>
 *       {trace && <ExecutionView trace={trace} />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useExecutionTrace(executionId: string) {
  const [trace, setTrace] = useState<ExecutionTrace | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrace = useCallback(async () => {
    if (!executionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/executions/${executionId}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Execution not found');
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setTrace(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch execution');
    } finally {
      setIsLoading(false);
    }
  }, [executionId]);

  useEffect(() => {
    fetchTrace();
  }, [fetchTrace]);

  return { trace, isLoading, error, refetch: fetchTrace };
}

/**
 * Hook for fetching recent execution history
 *
 * @param limit - Maximum number of executions to fetch (default: 10)
 * @returns List of executions, loading state, error, and refetch function
 *
 * @example
 * ```tsx
 * function ExecutionHistory() {
 *   const { executions, isLoading, error, refetch } = useExecutionHistory(20);
 *
 *   return (
 *     <div>
 *       <button onClick={refetch}>Refresh</button>
 *       {executions.map(exec => (
 *         <ExecutionCard key={exec.execution_id} execution={exec} />
 *       ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useExecutionHistory(limit: number = 10) {
  const [executions, setExecutions] = useState<ExecutionTrace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/executions?limit=${limit}`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: ExecutionListResponse = await response.json();
      setExecutions(data.executions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return { executions, isLoading, error, refetch: fetchHistory };
}

/**
 * Hook for deleting an execution trace
 *
 * @returns Delete function, loading state, and error
 *
 * @example
 * ```tsx
 * function ExecutionCard({ executionId }: { executionId: string }) {
 *   const { deleteExecution, isDeleting, error } = useDeleteExecution();
 *
 *   const handleDelete = async () => {
 *     await deleteExecution(executionId);
 *     // Refresh list or navigate away
 *   };
 *
 *   return <button onClick={handleDelete} disabled={isDeleting}>Delete</button>;
 * }
 * ```
 */
export function useDeleteExecution() {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deleteExecution = useCallback(async (executionId: string) => {
    setIsDeleting(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/executions/${executionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete execution');
      return false;
    } finally {
      setIsDeleting(false);
    }
  }, []);

  return { deleteExecution, isDeleting, error };
}

/**
 * Hook for computing execution statistics
 *
 * @param trace - The execution trace to analyze
 * @returns Computed statistics
 *
 * @example
 * ```tsx
 * function ExecutionStats({ trace }: { trace: ExecutionTrace }) {
 *   const stats = useExecutionStats(trace);
 *
 *   return (
 *     <div>
 *       <p>Total Duration: {stats.total_duration.toFixed(2)}s</p>
 *       <p>Average Step: {stats.average_step_duration.toFixed(2)}s</p>
 *       {stats.slowest_step && (
 *         <p>Slowest: {stats.slowest_step.agent_name} ({stats.slowest_step.duration.toFixed(2)}s)</p>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useExecutionStats(trace: ExecutionTrace | null): ExecutionStats | null {
  return useState(() => {
    if (!trace) return null;

    const completedSteps = trace.steps.filter(s => s.status === 'completed');
    const failedSteps = trace.steps.filter(s => s.status === 'failed');

    const durations = completedSteps
      .map(s => s.duration_seconds)
      .filter((d): d is number => d !== null && d !== undefined);

    const totalDuration = trace.end_time && trace.start_time
      ? (new Date(trace.end_time).getTime() - new Date(trace.start_time).getTime()) / 1000
      : 0;

    const averageDuration = durations.length > 0
      ? durations.reduce((sum, d) => sum + d, 0) / durations.length
      : 0;

    let slowestStep = null;
    let fastestStep = null;

    if (durations.length > 0) {
      const maxDuration = Math.max(...durations);
      const minDuration = Math.min(...durations);

      const slowest = completedSteps.find(s => s.duration_seconds === maxDuration);
      const fastest = completedSteps.find(s => s.duration_seconds === minDuration);

      if (slowest) {
        slowestStep = {
          agent_name: slowest.agent_name,
          duration: maxDuration,
        };
      }

      if (fastest) {
        fastestStep = {
          agent_name: fastest.agent_name,
          duration: minDuration,
        };
      }
    }

    return {
      total_duration: totalDuration,
      step_count: trace.steps.length,
      completed_steps: completedSteps.length,
      failed_steps: failedSteps.length,
      average_step_duration: averageDuration,
      slowest_step: slowestStep,
      fastest_step: fastestStep,
    };
  })[0];
}

/**
 * Hook for converting execution trace to timeline events
 *
 * @param trace - The execution trace
 * @returns Array of timeline events
 *
 * @example
 * ```tsx
 * function ExecutionTimeline({ trace }: { trace: ExecutionTrace }) {
 *   const events = useTimelineEvents(trace);
 *
 *   return (
 *     <Timeline>
 *       {events.map(event => (
 *         <TimelineItem key={event.id} event={event} />
 *       ))}
 *     </Timeline>
 *   );
 * }
 * ```
 */
export function useTimelineEvents(trace: ExecutionTrace | null): TimelineEvent[] {
  return useState(() => {
    if (!trace) return [];

    return trace.steps.map(step => ({
      id: step.step_id,
      agent_name: step.agent_name,
      start_time: new Date(step.start_time),
      end_time: step.end_time ? new Date(step.end_time) : null,
      duration: step.duration_seconds,
      status: step.status,
    }));
  })[0];
}
