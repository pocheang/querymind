import type { ExecutionEvent, ExecutionStage } from "./types";

export type GenerationPhase =
  "getting_started" | "routing" | "retrieving" | "writing" | "verifying" | "finalizing" | "almost_done";

/** What stage finishing tells us the pipeline has moved on to next, in the
 *  fixed order of the 7 canonical LangGraph nodes (CLAUDE.md). `knowledge`,
 *  `rag` and `tool` all land on "writing": whichever of them a route takes,
 *  finishing it means synthesis is next. Stages with no entry here
 *  (`complete`, `failed`) are terminal wrappers, not phases to announce. */
const PHASE_AFTER_STAGE: Partial<Record<ExecutionStage, GenerationPhase>> = {
  privacy_permission: "routing",
  route: "retrieving",
  plan: "retrieving",
  knowledge_strategy: "retrieving",
  knowledge: "writing",
  rag: "writing",
  tool: "writing",
  synthesize: "verifying",
  verifier: "finalizing",
  finalize: "almost_done",
  output_filter: "almost_done",
};

/**
 * Guess what the run is doing right now, from the stages it has already
 * finished.
 *
 * The SSE stream only ever reports a stage's OUTCOME -- `EventStatus` in
 * app/domain/events.py is `"completed" | "failed" | "skipped"`, with no
 * "running" state -- so there is no literal "this is executing now" signal
 * to read. This is a forward-looking guess from the pipeline's fixed order
 * instead: the most recently finished stage implies which one is next. Good
 * enough for a progress phrase; do not rely on it for anything that needs
 * to be exact.
 */
export function describeCurrentPhase(events: readonly ExecutionEvent[]): GenerationPhase {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const phase = PHASE_AFTER_STAGE[events[i].stage];
    if (phase) return phase;
  }
  return "getting_started";
}
