import { describe, expect, it } from "vitest";

import { describeCurrentPhase } from "./currentPhase";
import type { ExecutionEvent, ExecutionStage } from "./types";

function event(stage: ExecutionStage): ExecutionEvent {
  return {
    version: "1",
    stage,
    status: "completed",
    duration_ms: 1,
    message: "",
    metadata: [],
    occurred_at: "2026-09-15T00:00:00Z",
  };
}

describe("describeCurrentPhase", () => {
  it("guesses getting_started before anything has finished", () => {
    expect(describeCurrentPhase([])).toBe("getting_started");
  });

  it("maps each finished stage to what comes after it", () => {
    expect(describeCurrentPhase([event("privacy_permission")])).toBe("routing");
    expect(describeCurrentPhase([event("route")])).toBe("retrieving");
    expect(describeCurrentPhase([event("knowledge")])).toBe("writing");
    expect(describeCurrentPhase([event("synthesize")])).toBe("verifying");
    expect(describeCurrentPhase([event("verifier")])).toBe("finalizing");
    expect(describeCurrentPhase([event("output_filter")])).toBe("almost_done");
  });

  it("reads the most recently finished stage, not the first", () => {
    const events = [event("privacy_permission"), event("route"), event("knowledge")];

    expect(describeCurrentPhase(events)).toBe("writing");
  });

  it("skips the terminal complete/failed wrapper stages and reports the last real one", () => {
    const events = [event("synthesize"), event("complete")];

    expect(describeCurrentPhase(events)).toBe("verifying");
  });

  it("reflects a verifier retry looping back to retrieval, not a stale later phase", () => {
    const events = [event("synthesize"), event("verifier"), event("knowledge")];

    expect(describeCurrentPhase(events)).toBe("writing");
  });
});
