import { afterEach, describe, expect, it, vi } from "vitest";

// Only the network boundary is replaced; parseOrThrow and the rest of the
// client stay real, so the body asserted below is the one that would be sent.
const sent: Array<Record<string, unknown>> = [];
vi.mock("@/services/http/client", async () => {
  const actual = await vi.importActual<typeof import("@/services/http/client")>("@/services/http/client");
  return {
    ...actual,
    authFetch: vi.fn(async (_path: string, init: RequestInit = {}) => {
      sent.push(JSON.parse(String(init.body)));
      return new Response(JSON.stringify({ final_answer: "ok", metadata: {} }), {
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
