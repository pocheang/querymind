/**
 * React hooks for Agent Execution Tracking
 *
 * Provides hooks for:
 * - Real-time execution tracking via SSE
 * - Fetching execution traces
 * - Managing execution history
 */

import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import type {
  ExecutionTrace,
  ExecutionStats,
  TimelineEvent,
} from '../types/agent-tracking';
import { authRequest, toUrl } from '@/lib/api-client';

const API_BASE = '/agent-tracking';

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
    let cancelled = false;

    authRequest<ExecutionTrace>(`${API_BASE}/trace/${encodeURIComponent(executionId)}`)
      .then((initialTrace) => {
        if (!cancelled) setTrace(initialTrace);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch execution');
          setIsLoading(false);
        }
      });

    // Create SSE connection
    const eventSource = new EventSource(
      toUrl(`${API_BASE}/stream/${encodeURIComponent(executionId)}`),
      { withCredentials: true },
    );
    eventSourceRef.current = eventSource;

    const readEventData = (event: Event): string => {
      return event instanceof MessageEvent ? String(event.data) : "{}";
    };

    const handleComplete = (event: Event) => {
      try {
        const data = JSON.parse(readEventData(event)) as ExecutionTrace & { error?: string };

        if (data.error) {
          setError(data.error);
          setIsLoading(false);
          eventSource.close();
          return;
        }

        setTrace(data);
        setIsLoading(false);
        eventSource.close();
      } catch (err) {
        setError('Failed to parse execution data');
        setIsLoading(false);
        eventSource.close();
      }
    };

    const handleStep = (event: Event) => {
      try {
        const step = JSON.parse(readEventData(event)) as ExecutionTrace['steps'][number];
        setTrace((current) => {
          if (!current || current.steps.some((item) => item.step_id === step.step_id)) {
            return current;
          }
          return { ...current, steps: [...current.steps, step] };
        });
        setIsLoading(false);
      } catch {
        setError('Failed to parse execution step');
        setIsLoading(false);
      }
    };

    const handleError = (event: Event) => {
      try {
        const data = JSON.parse(readEventData(event)) as { error?: string };
        setError(data.error || 'Execution stream failed');
      } catch {
        setError('Execution stream failed');
      }
      setIsLoading(false);
      eventSource.close();
    };

    const handleTimeout = (event: Event) => {
      try {
        const data = JSON.parse(readEventData(event)) as { message?: string };
        setError(data.message || 'Execution stream timed out');
      } catch {
        setError('Execution stream timed out');
      }
      setIsLoading(false);
      eventSource.close();
    };

    eventSource.addEventListener('agent_step', handleStep);
    eventSource.addEventListener('execution_complete', handleComplete);
    eventSource.addEventListener('error', handleError);
    eventSource.addEventListener('timeout', handleTimeout);

    eventSource.onerror = () => {
      setError('Connection lost');
      setIsLoading(false);
      eventSource.close();
    };

    // Cleanup on unmount
    return () => {
      cancelled = true;
      eventSource.removeEventListener('agent_step', handleStep);
      eventSource.removeEventListener('execution_complete', handleComplete);
      eventSource.removeEventListener('error', handleError);
      eventSource.removeEventListener('timeout', handleTimeout);
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
      const data = await authRequest<ExecutionTrace>(`${API_BASE}/trace/${encodeURIComponent(executionId)}`);
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
      const data = await authRequest<ExecutionTrace[]>(`${API_BASE}/history?limit=${limit}`);
      setExecutions(data);
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
      await authRequest(`${API_BASE}/trace/${encodeURIComponent(executionId)}`, { method: 'DELETE' });
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
  return useMemo(() => {
    if (!trace) return null;

    const completedSteps = trace.steps.filter(s => s.status === 'completed');
    const failedSteps = trace.steps.filter(s => s.status === 'failed');

    // Convert duration_ms to seconds for display
    const durations = completedSteps
      .map(s => s.duration_ms ? s.duration_ms / 1000 : null)
      .filter((d): d is number => d !== null && d !== undefined);

    // Use total_duration_ms if available, otherwise calculate from timestamps
    const totalDuration = trace.total_duration_ms
      ? trace.total_duration_ms / 1000
      : (trace.end_time && trace.start_time
        ? (new Date(trace.end_time).getTime() - new Date(trace.start_time).getTime()) / 1000
        : 0);

    const averageDuration = durations.length > 0
      ? durations.reduce((sum, d) => sum + d, 0) / durations.length
      : 0;

    let slowestStep = null;
    let fastestStep = null;

    if (durations.length > 0) {
      const maxDuration = Math.max(...durations);
      const minDuration = Math.min(...durations);

      const slowestIndex = durations.indexOf(maxDuration);
      const fastestIndex = durations.indexOf(minDuration);

      if (slowestIndex !== -1) {
        slowestStep = {
          agent_name: completedSteps[slowestIndex].agent_name,
          duration: maxDuration,
        };
      }

      if (fastestIndex !== -1) {
        fastestStep = {
          agent_name: completedSteps[fastestIndex].agent_name,
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
  }, [trace]);
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
  return useMemo(() => {
    if (!trace) return [];

    return trace.steps.map(step => ({
      id: step.step_id,
      agent_name: step.agent_name,
      start_time: new Date(step.start_time),
      end_time: step.end_time ? new Date(step.end_time) : null,
      duration: step.duration_ms ? step.duration_ms / 1000 : null,
      status: step.status,
    }));
  }, [trace]);
}
