import { describe, expect, it } from "vitest";

import type { NormalizedQueryResult, SessionMessage } from "@/types/api";
import { applyStreamDraft, applyStreamResult, applyThinkingDraft } from "./useMessageActions";

/**
 * The streaming draft bubble looked like it "appeared all at once" instead of
 * growing token by token, even though the model underneath -- including the
 * offline `LocalEvidenceChatModel.stream()` stand-in, which paces its chunks
 * with a real delay -- was genuinely streaming.
 *
 * The cause was in the guard `onDraft` used to find its target message:
 * `message_id === "local-assistant-stream" && !message.content`. The second
 * half was true only for the very first fragment. `useExecutionTrace`'s
 * `draft` is cumulative (the reducer does `state.draft + action.text`), so
 * every fragment after the first sees a message with non-empty content and
 * the update was silently dropped -- one early snapshot, then a frozen bubble
 * until the final answer replaced it outright.
 *
 * `applyStreamDraft` fixes it by matching on id alone, the same way
 * `applyStreamResult`'s final replacement already does safely a few lines
 * above it in the same file.
 */

function messages(content = ""): SessionMessage[] {
  return [
    { message_id: "local-user-1", role: "user", content: "what is RAG?" },
    { message_id: "local-assistant-stream", role: "assistant", content },
  ];
}

describe("applyStreamDraft", () => {
  it("applies the first fragment to the empty placeholder", () => {
    const next = applyStreamDraft(messages(""), "Retrieval");

    expect(next[1].content).toBe("Retrieval");
  });

  it("keeps applying once the placeholder already holds earlier text", () => {
    // The bug: a second, larger cumulative draft must still land, not be
    // silently dropped because the message is no longer empty.
    const afterFirst = applyStreamDraft(messages(""), "Retrieval");
    const afterSecond = applyStreamDraft(afterFirst, "Retrieval augmented");
    const afterThird = applyStreamDraft(afterSecond, "Retrieval augmented generation");

    expect(afterSecond[1].content).toBe("Retrieval augmented");
    expect(afterThird[1].content).toBe("Retrieval augmented generation");
  });

  it("leaves every other message untouched", () => {
    const next = applyStreamDraft(messages("Retrieval"), "Retrieval augmented");

    expect(next[0]).toEqual(messages("Retrieval")[0]);
  });

  it("is a no-op when there is no streaming placeholder in the list", () => {
    const withoutPlaceholder: SessionMessage[] = [{ message_id: "local-user-1", role: "user", content: "hi" }];

    expect(applyStreamDraft(withoutPlaceholder, "some text")).toEqual(withoutPlaceholder);
  });
});

/**
 * Same shape and same bug class as `applyStreamDraft` above, for the
 * reasoning channel: matches on id alone (not "and content is still empty"),
 * so every fragment after the first still lands. The one difference is where
 * the text goes -- `metadata.reasoning`, not `.content`, since the answer's
 * own streaming placeholder content is a separate channel that starts once
 * reasoning ends.
 */
describe("applyThinkingDraft", () => {
  it("applies the first fragment to the empty placeholder's metadata", () => {
    const next = applyThinkingDraft(messages(""), "Step 1: analyze");

    expect(next[1].metadata?.reasoning).toBe("Step 1: analyze");
  });

  it("keeps applying as the cumulative reasoning text grows", () => {
    const afterFirst = applyThinkingDraft(messages(""), "Step 1: analyze");
    const afterSecond = applyThinkingDraft(afterFirst, "Step 1: analyze the question.");

    expect(afterSecond[1].metadata?.reasoning).toBe("Step 1: analyze the question.");
  });

  it("does not touch the answer's own content", () => {
    const next = applyThinkingDraft(messages(""), "Step 1: analyze");

    expect(next[1].content).toBe("");
  });

  it("leaves every other message untouched", () => {
    const next = applyThinkingDraft(messages("Retrieval"), "Step 1: analyze");

    expect(next[0]).toEqual(messages("Retrieval")[0]);
  });

  it("is a no-op when there is no streaming placeholder in the list", () => {
    const withoutPlaceholder: SessionMessage[] = [{ message_id: "local-user-1", role: "user", content: "hi" }];

    expect(applyThinkingDraft(withoutPlaceholder, "some reasoning")).toEqual(withoutPlaceholder);
  });
});

/**
 * The final replacement rebuilds `metadata` from EMPTY_METADATA, so every
 * field it does not explicitly carry over is erased. Assigning
 * `reasoning: result.reasoning` therefore did more than "prefer the persisted
 * copy": when the response carried no reasoning at all, it wiped the draft
 * `applyThinkingDraft` had been accumulating, and the panel the reader had
 * been watching vanished at the exact moment the answer landed.
 */
describe("applyStreamResult and the reasoning channel", () => {
  const streamed = (reasoning: string): SessionMessage[] => [
    { message_id: "local-user-1", role: "user", content: "what is RAG?" },
    {
      message_id: "local-assistant-stream",
      role: "assistant",
      content: "",
      metadata: { reasoning, reasoning_duration_ms: 3000 },
    },
  ];

  const result = (reasoning?: string): NormalizedQueryResult => ({
    answer: "The answer.",
    citations: [],
    status: "complete",
    pendingApproval: null,
    toolRuns: [],
    ...(reasoning === undefined ? {} : { reasoning }),
  });

  it("prefers the response's own reasoning, which is the redacted persisted copy", () => {
    const next = applyStreamResult(streamed("streamed draft"), result("persisted copy"));

    expect(next[1].metadata?.reasoning).toBe("persisted copy");
  });

  it("keeps the streamed reasoning when the response carries none", () => {
    const next = applyStreamResult(streamed("streamed draft"), result());

    expect(next[1].metadata?.reasoning).toBe("streamed draft");
    expect(next[1].metadata?.reasoning_duration_ms).toBe(3000);
  });

  it("leaves reasoning absent when there never was any", () => {
    const next = applyStreamResult(streamed(""), result());

    expect(next[1].metadata?.reasoning).toBeFalsy();
  });
});
