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
    if (item?.key) {
      result[item.key] = item.value;
    }
  }
  return result;
}

const RETRIEVAL_OUTCOME_RE = /^(\w+)\s+retrieval\s+(completed|skipped|failed)$/i;

function parseSubSourceItem(
  event: ExecutionEvent,
  meta: Record<string, string>,
  index: number,
): SubSourceItem | null {
  if (event.stage !== "knowledge") return null;
  const sourceMatch = event.message ? RETRIEVAL_OUTCOME_RE.exec(event.message) : null;
  const sourceName = meta.source || (sourceMatch ? sourceMatch[1] : null);
  if (!sourceName || sourceName.toLowerCase() === "completed") return null;

  const resultCountStr = meta.result_count;
  const resultCount = resultCountStr ? Number.parseInt(resultCountStr, 10) : undefined;

  return {
    id: `${event.occurred_at}-${index}`,
    sourceKey: sourceName.toLowerCase(),
    status: event.status,
    duration_ms: event.duration_ms,
    resultCount: Number.isFinite(resultCount) ? resultCount : undefined,
    rawMessage: event.message,
  };
}

function updateRoundState(
  event: ExecutionEvent,
  seenVerifier: boolean,
): { newRound: boolean; newSeenVerifier: boolean } {
  if (event.stage === "verifier") {
    return { newRound: false, newSeenVerifier: true };
  }
  if (seenVerifier && (event.stage === "knowledge_strategy" || event.stage === "knowledge" || event.stage === "synthesize")) {
    return { newRound: true, newSeenVerifier: false };
  }
  return { newRound: false, newSeenVerifier: seenVerifier };
}

function attachLeftoverSubSources(stages: StructuredStage[], pendingSubSources: SubSourceItem[]): void {
  if (pendingSubSources.length === 0) return;
  const lastKnowledge = stages.slice().reverse().find((s) => s.stage === "knowledge" || s.stage === "rag");
  if (lastKnowledge && !lastKnowledge.subSources) {
    lastKnowledge.subSources = [...pendingSubSources];
  }
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
  let pendingSubSources: SubSourceItem[] = [];

  const terminalCompleteEvents = events.filter((e) => e.stage === "complete");
  const finalCompleteEvent = terminalCompleteEvents.length > 0
    ? terminalCompleteEvents[terminalCompleteEvents.length - 1]
    : null;

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    const meta = metadataToDict(event.metadata);

    if (event.stage === "complete") {
      if (event === finalCompleteEvent) {
        isComplete = true;
        totalDurationMs = Math.max(totalDurationMs, event.duration_ms);
      }
      continue;
    }

    if (event.status === "failed") {
      hasFailed = true;
    }

    const roundUpdate = updateRoundState(event, seenVerifier);
    if (roundUpdate.newRound) {
      currentRound++;
    }
    seenVerifier = roundUpdate.newSeenVerifier;

    const subSource = parseSubSourceItem(event, meta, i);
    if (subSource) {
      pendingSubSources.push(subSource);
      continue;
    }

    const stageItem: StructuredStage = {
      id: `${event.stage}-${currentRound}-${i}`,
      stage: event.stage,
      status: event.status,
      duration_ms: event.duration_ms,
      labelKey: `features.executionTrace.stages.${event.stage}`,
      message: event.message || undefined,
      round: currentRound,
      isRefinement: currentRound > 1,
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

  attachLeftoverSubSources(stages, pendingSubSources);

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
