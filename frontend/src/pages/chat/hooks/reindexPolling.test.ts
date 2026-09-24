import { describe, expect, it } from "vitest";
import type { IndexedFileSummary } from "@/types/api";
import { waitForReindex } from "./reindexPolling";

function doc(status: string): IndexedFileSummary {
  return { filename: "a.pdf", source: "/u/a.pdf", chunks: 3, document_id: "doc-1", indexing_status: status as never };
}

function clock() {
  let t = 0;
  return { now: () => t, sleep: async (ms: number) => void (t += ms) };
}

describe("waitForReindex", () => {
  it("keeps polling while the document is queued or indexing, and settles on ready", async () => {
    const seen = ["queued", "indexing", "ready"];
    const { now, sleep } = clock();
    const outcome = await waitForReindex("doc-1", async () => [doc(seen.shift() as string)], { now, sleep });
    expect(outcome.kind).toBe("ready");
    expect(seen).toEqual([]);
  });

  it("reports a failed reindex with the document, so its error can be shown", async () => {
    const { now, sleep } = clock();
    const outcome = await waitForReindex("doc-1", async () => [{ ...doc("failed"), indexing_error: "boom" }], {
      now,
      sleep,
    });
    expect(outcome).toMatchObject({ kind: "failed", document: { indexing_error: "boom" } });
  });

  it("reports a document that disappeared rather than waiting for it forever", async () => {
    const { now, sleep } = clock();
    expect((await waitForReindex("doc-1", async () => [], { now, sleep })).kind).toBe("gone");
  });

  it("treats a failed poll as a reason to poll again, not as a failed reindex", async () => {
    const replies: Array<() => Promise<IndexedFileSummary[]>> = [
      () => Promise.reject(new Error("network")),
      async () => [doc("ready")],
    ];
    const { now, sleep } = clock();
    const outcome = await waitForReindex("doc-1", () => (replies.shift() as () => Promise<IndexedFileSummary[]>)(), {
      now,
      sleep,
    });
    expect(outcome.kind).toBe("ready");
  });

  it("gives up at the deadline", async () => {
    const { now, sleep } = clock();
    const outcome = await waitForReindex("doc-1", async () => [doc("indexing")], {
      now,
      sleep,
      intervalMs: 1000,
      timeoutMs: 5000,
    });
    expect(outcome.kind).toBe("timeout");
  });

  it("follows the one document it was asked about, not the first in the list", async () => {
    const { now, sleep } = clock();
    const other = { ...doc("ready"), document_id: "doc-2" };
    const replies = [
      [other, doc("indexing")],
      [other, doc("failed")],
    ];
    const outcome = await waitForReindex("doc-1", async () => replies.shift() as IndexedFileSummary[], { now, sleep });
    expect(outcome.kind).toBe("failed");
  });
});
