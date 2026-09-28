import { afterEach, describe, expect, it, vi } from "vitest";

// Only the network boundary is replaced; parseOrThrow and the rest of the
// client stay real, so the body asserted below is the one that would be sent.
const sent: Array<Record<string, unknown>> = [];
let responseMetadata: Record<string, unknown> = {};
vi.mock("@/services/http/client", async () => {
  const actual = await vi.importActual<typeof import("@/services/http/client")>("@/services/http/client");
  return {
    ...actual,
    authFetch: vi.fn(async (_path: string, init: RequestInit = {}) => {
      sent.push(JSON.parse(String(init.body)));
      return new Response(JSON.stringify({ final_answer: "ok", metadata: responseMetadata }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  };
});

import { queryApi } from "./chat";

const base = { query: "q", enableDecomposition: true, enableSelfRag: true };

describe("the advanced query carries the agent mode", () => {
  afterEach(() => {
    sent.length = 0;
  });

  it("sends the picked agent class", async () => {
    // The sidebar picker used to stop at the store: it showed "locked" and the
    // request carried nothing, so every question was routed automatically.
    await queryApi.advanced({ ...base, agentClassHint: "cybersecurity" });

    expect(sent[0].agent_class_hint).toBe("cybersecurity");
  });

  it("sends nothing for Auto Router", async () => {
    await queryApi.advanced({ ...base, agentClassHint: "" });
    await queryApi.advanced(base);

    expect(sent).toHaveLength(2);
    for (const body of sent) expect(body).not.toHaveProperty("agent_class_hint");
  });
});

describe("the normalized result names the specialist and keeps what a reload shows", () => {
  afterEach(() => {
    sent.length = 0;
    responseMetadata = {};
  });

  it("reads the specialist, the answer shape and the retrieval outcome", async () => {
    responseMetadata = {
      agent_class: "cybersecurity",
      skill: "vulnerability_exposure_assessment",
      web_used: true,
      sources: [{ source: "web", status: "completed", count: 3, reason: null }],
    };

    const result = await queryApi.advanced(base);

    expect(result.agentClass).toBe("cybersecurity");
    expect(result.skill).toBe("vulnerability_exposure_assessment");
    expect(result.webUsed).toBe(true);
    expect(result.sources).toEqual([{ source: "web", status: "completed", count: 3, reason: null }]);
  });

  it("keeps the marker a cited tool run carries, and nothing for one that is not cited", async () => {
    responseMetadata = {
      tool_runs: [
        { tool_id: "querymind_cyber_product_exposure", status: "succeeded", summary: "s", marker: "T1" },
        { tool_id: "querymind_cyber_cve_lookup", status: "succeeded", summary: "s", marker: null },
      ],
    };

    const result = await queryApi.advanced(base);

    expect(result.toolRuns[0].marker).toBe("T1");
    expect(result.toolRuns[1]).not.toHaveProperty("marker");
  });

  it("drops a source outcome that is not the shape it claims to be", async () => {
    responseMetadata = { sources: [{ source: "web" }, "vector", { source: "bm25", status: "completed", count: 2 }] };

    const result = await queryApi.advanced(base);

    expect(result.sources).toEqual([{ source: "bm25", status: "completed", count: 2, reason: null }]);
  });
});
