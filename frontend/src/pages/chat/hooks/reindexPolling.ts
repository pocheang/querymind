import type { IndexedFileSummary } from "@/types/api";

/**
 * How a queued reindex ended, as far as this client could see.
 *
 * A reindex is a job now (ARC-01 phase 5): the server answers 202 and the
 * ingest worker -- or the server's own pool -- runs it. The only record of how
 * it went is the document's `indexing_status` in the document list, so this
 * polls that one document until it settles.
 */
export type ReindexOutcome =
  | { kind: "ready"; document: IndexedFileSummary }
  | { kind: "failed"; document: IndexedFileSummary }
  | { kind: "gone" }
  | { kind: "timeout" };

const SETTLED_FAILED = new Set(["failed", "error"]);

export interface PollOptions {
  intervalMs?: number;
  timeoutMs?: number;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
}

function outcomeOf(document: IndexedFileSummary | undefined): ReindexOutcome | null {
  if (!document) return { kind: "gone" };
  const status = String(document.indexing_status || "");
  if (status === "ready") return { kind: "ready", document };
  if (SETTLED_FAILED.has(status)) return { kind: "failed", document };
  return null;
}

export async function waitForReindex(
  documentId: string,
  fetchDocuments: () => Promise<IndexedFileSummary[]>,
  { intervalMs = 2000, timeoutMs = 10 * 60_000, sleep, now = Date.now }: PollOptions = {}
): Promise<ReindexOutcome> {
  const pause = sleep ?? ((ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms)));
  const deadline = now() + timeoutMs;
  while (now() < deadline) {
    await pause(intervalMs);
    let documents: IndexedFileSummary[];
    try {
      documents = await fetchDocuments();
    } catch {
      // A failed poll is not a failed reindex: the job is still the server's.
      continue;
    }
    const outcome = outcomeOf(documents.find((doc) => doc.document_id === documentId));
    if (outcome) return outcome;
  }
  return { kind: "timeout" };
}
