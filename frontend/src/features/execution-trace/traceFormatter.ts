import type { ExecutionEvent, ExecutionStage, ExecutionStatus } from "./types";

export type SubSourceItem = {
  id: string;
  sourceKey: string;
  status: ExecutionStatus;
  duration_ms: number;
  resultCount?: number;
  rawMessage: string;
};

export type StructuredStage = {
  id: string;
  stage: ExecutionStage;
  status: ExecutionStatus;
  duration_ms: number;
  labelKey: string;
  message?: string;
  round?: number;
  isRefinement?: boolean;
  subSources?: SubSourceItem[];
  metadata?: Record<string, string>;
};

export type ExecutionTraceSummary = {
  totalDurationMs: number;
  stagesCount: number;
  roundsCount: number;
  isComplete: boolean;
  hasFailed: boolean;
};

/**
 * Format milliseconds into a human-friendly string (e.g. 0 -> "< 1ms", 1696 -> "1.70s", 40786 -> "40.8s").
 */
export function formatDuration(ms: number): string {
  if (ms <= 0) return "< 1ms";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 10000) return `${(ms / 1000).toFixed(2)}s`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * Parse metadata array into a key-value dictionary for easy lookups.
 */
function metadataToDict(metadata?: readonly { key: string; value: string }[]): Record<string, string> {
  if (!metadata || !Array.isArray(metadata)) return {};
  const result: Record<string, string> = {};
  for (const item of metadata) {
    if (item && item.key) {
      result[item.key] = item.value;
    }
  }
  return result;
}

/**
 * Group flat execution events into structured, readable stages and detect refinement rounds.
 */
export function groupExecutionEvents(events: readonly ExecutionEvent[]): {
  stages: StructuredStage[];
  summary: ExecutionTraceSummary;
} {
  if (!events || events.length === 0) {
    return {
      stages: [],
      summary: {
        totalDurationMs: 0,
        stagesCount: 0,
        roundsCount: 0,
        isComplete: false,
        hasFailed: false,
      },
    };
  }

  const stages: StructuredStage[] = [];
  let currentRound = 1;
  let seenVerifier = false;
  let totalDurationMs = 0;
  let isComplete = false;
  let hasFailed = false;

  // Track sub-sources for pending knowledge retrieval stages
  let pendingSubSources: SubSourceItem[] = [];

  // Filter and deduplicate events
  // Keep only the final terminal 'complete' event if multiple arrive
  const terminalCompleteEvents = events.filter((e) => e.stage === "complete");
  const finalCompleteEvent = terminalCompleteEvents.length > 0
    ? terminalCompleteEvents[terminalCompleteEvents.length - 1]
    : null;

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    const meta = metadataToDict(event.metadata);

    // If this is a terminal complete event and it's not the final one, skip it
    if (event.stage === "complete") {
      if (event !== finalCompleteEvent) continue;
      isComplete = true;
      totalDurationMs = Math.max(totalDurationMs, event.duration_ms);
      continue;
    }

    if (event.status === "failed") {
      hasFailed = true;
    }

    // Detect refinement rounds: when retrieval / synthesis starts again after verifier
    if (seenVerifier && (event.stage === "knowledge_strategy" || event.stage === "knowledge" || event.stage === "synthesize")) {
      currentRound++;
      seenVerifier = false;
    }

    if (event.stage === "verifier") {
      seenVerifier = true;
    }

    // Check if this event is an individual knowledge source outcome (e.g. vector, bm25, web)
    // Produced by _outcome_event in app/knowledge/orchestrator.py
    const sourceMatch = event.message ? event.message.match(/^(\w+)\s+retrieval\s+(completed|skipped|failed)$/i) : null;
    const sourceName = meta.source || (sourceMatch ? sourceMatch[1] : null);

    if (event.stage === "knowledge" && sourceName && sourceName.toLowerCase() !== "completed") {
      const resultCountStr = meta.result_count;
      const resultCount = resultCountStr ? Number.parseInt(resultCountStr, 10) : undefined;

      pendingSubSources.push({
        id: `${event.occurred_at}-${i}`,
        sourceKey: sourceName.toLowerCase(),
        status: event.status,
        duration_ms: event.duration_ms,
        resultCount: Number.isFinite(resultCount) ? resultCount : undefined,
        rawMessage: event.message,
      });
      continue;
    }

    // Regular stage event or aggregated knowledge stage completion
    const isRefinement = currentRound > 1;
    const stageId = `${event.stage}-${currentRound}-${i}`;

    const stageItem: StructuredStage = {
      id: stageId,
      stage: event.stage,
      status: event.status,
      duration_ms: event.duration_ms,
      labelKey: `features.executionTrace.stages.${event.stage}`,
      message: event.message || undefined,
      round: currentRound,
      isRefinement,
      metadata: Object.keys(meta).length > 0 ? meta : undefined,
    };

    if (event.stage === "knowledge" || event.stage === "rag") {
      if (pendingSubSources.length > 0) {
        stageItem.subSources = [...pendingSubSources];
        pendingSubSources = [];
      }
    }

    stages.push(stageItem);
  }

  // If there are leftover pending sub-sources that didn't get attached to a parent knowledge event
  if (pendingSubSources.length > 0) {
    const lastKnowledge = stages.slice().reverse().find((s) => s.stage === "knowledge" || s.stage === "rag");
    if (lastKnowledge && !lastKnowledge.subSources) {
      lastKnowledge.subSources = [...pendingSubSources];
    }
  }

  // Calculate total duration if no complete event provided it
  if (totalDurationMs === 0) {
    totalDurationMs = stages.reduce((acc, s) => acc + s.duration_ms, 0);
  }

  return {
    stages,
    summary: {
      totalDurationMs,
      stagesCount: stages.length,
      roundsCount: currentRound,
      isComplete,
      hasFailed,
    },
  };
}
