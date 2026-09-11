import { describe, expect, it } from "vitest";
import { formatDuration, groupExecutionEvents } from "./traceFormatter";
import type { ExecutionEvent } from "./types";

describe("formatDuration", () => {
  it("formats zero or negative durations", () => {
    expect(formatDuration(0)).toBe("< 1ms");
    expect(formatDuration(-5)).toBe("< 1ms");
  });

  it("formats sub-second durations", () => {
    expect(formatDuration(1)).toBe("1ms");
    expect(formatDuration(500)).toBe("500ms");
    expect(formatDuration(999)).toBe("999ms");
  });

  it("formats multi-second durations with appropriate precision", () => {
    expect(formatDuration(1696)).toBe("1.70s");
    expect(formatDuration(3404)).toBe("3.40s");
    expect(formatDuration(15225)).toBe("15.2s");
    expect(formatDuration(40786)).toBe("40.8s");
  });
});

describe("groupExecutionEvents", () => {
  const createEvent = (
    stage: ExecutionEvent["stage"],
    status: ExecutionEvent["status"],
    duration_ms: number,
    message = "",
    metadata: { key: string; value: string }[] = []
  ): ExecutionEvent => ({
    version: "1",
    stage,
    status,
    duration_ms,
    message,
    metadata,
    occurred_at: new Date().toISOString(),
  });

  it("handles empty events", () => {
    const { stages, summary } = groupExecutionEvents([]);
    expect(stages).toHaveLength(0);
    expect(summary.stagesCount).toBe(0);
  });

  it("correctly groups events matching the user scenario with refinement and sub-sources", () => {
    const userEvents: ExecutionEvent[] = [
      createEvent("privacy_permission", "completed", 1),
      createEvent("route", "completed", 0),
      createEvent("knowledge_strategy", "completed", 1),
      createEvent("knowledge", "skipped", 0, "vector retrieval skipped", [{ key: "source", value: "vector" }]),
      createEvent("knowledge", "skipped", 0, "bm25 retrieval skipped", [{ key: "source", value: "bm25" }]),
      createEvent("knowledge", "completed", 1696, "web retrieval completed", [{ key: "source", value: "web" }]),
      createEvent("knowledge", "completed", 1697),
      createEvent("synthesize", "completed", 0),
      createEvent("verifier", "completed", 3),
      // Round 2
      createEvent("knowledge_strategy", "completed", 0),
      createEvent("knowledge", "skipped", 0, "vector retrieval skipped", [{ key: "source", value: "vector" }]),
      createEvent("knowledge", "skipped", 0, "bm25 retrieval skipped", [{ key: "source", value: "bm25" }]),
      createEvent("knowledge", "completed", 1286, "web retrieval completed", [{ key: "source", value: "web" }]),
      createEvent("knowledge", "completed", 3404),
      createEvent("synthesize", "completed", 7085),
      createEvent("verifier", "completed", 3023),
      // Delivery
      createEvent("finalize", "completed", 8),
      createEvent("output_filter", "completed", 3),
      // Terminal complete events (duplicate)
      createEvent("complete", "completed", 15225),
      createEvent("complete", "completed", 40786),
    ];

    const { stages, summary } = groupExecutionEvents(userEvents);

    // Terminal duplicate complete is merged, knowledge sub-sources are attached to parent knowledge
    expect(summary.isComplete).toBe(true);
    expect(summary.totalDurationMs).toBe(40786);
    expect(summary.roundsCount).toBe(2);

    // Check round 1 retrieval has sub-sources
    const round1Knowledge = stages.find((s) => s.stage === "knowledge" && s.round === 1);
    expect(round1Knowledge).toBeDefined();
    expect(round1Knowledge?.subSources).toHaveLength(3);
    expect(round1Knowledge?.subSources?.[0].sourceKey).toBe("vector");
    expect(round1Knowledge?.subSources?.[0].status).toBe("skipped");
    expect(round1Knowledge?.subSources?.[2].sourceKey).toBe("web");
    expect(round1Knowledge?.subSources?.[2].status).toBe("completed");

    // Check round 2 stages
    const round2Synthesize = stages.find((s) => s.stage === "synthesize" && s.round === 2);
    expect(round2Synthesize).toBeDefined();
    expect(round2Synthesize?.isRefinement).toBe(true);
    expect(round2Synthesize?.duration_ms).toBe(7085);
  });
});
