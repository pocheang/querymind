// @vitest-environment jsdom
import { createRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ChatComposer } from "@/pages/chat/components/ChatComposer";
import { useChatStore } from "@/stores/useChatStore";

/**
 * Escape had one meaning in the handler and a different one in the docs.
 *
 * `KeyboardHelp` called it "clear input"; the handler called `onStop()` and
 * only when `isSending`, so in the ordinary case -- a half-typed question,
 * nothing streaming -- the key did nothing. Both meanings are real and useful,
 * so both are implemented and both are documented; this pins which is which,
 * because a single `Escape` row that does two things is exactly the kind of
 * claim that drifts.
 */

afterEach(() => {
  cleanup();
  useChatStore.getState().reset();
});

function composer(overrides: Partial<React.ComponentProps<typeof ChatComposer>> = {}) {
  const noop = vi.fn();
  const props = {
    questionRef: createRef<HTMLTextAreaElement>() as React.MutableRefObject<HTMLTextAreaElement | null>,
    chatUploadInputRef: createRef<HTMLInputElement>() as React.MutableRefObject<HTMLInputElement | null>,
    isSending: false,
    quickPrompts: [],
    onAsk: vi.fn().mockResolvedValue(undefined),
    onStop: vi.fn(),
    onComposerDragEnter: noop,
    onComposerDragOver: noop,
    onComposerDragLeave: noop,
    onComposerDrop: vi.fn().mockResolvedValue(undefined),
    onChatUploadChange: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  } as React.ComponentProps<typeof ChatComposer>;
  render(<ChatComposer {...props} />);
  return props;
}

const textarea = () => screen.getByRole("textbox") as HTMLTextAreaElement;

describe("the composer's keys", () => {
  it("clears a draft on Escape when nothing is streaming", () => {
    useChatStore.getState().setQuestion("half a question");
    const props = composer({ isSending: false });

    fireEvent.keyDown(textarea(), { key: "Escape" });
    expect(useChatStore.getState().question).toBe("");
    expect(props.onStop).not.toHaveBeenCalled();
  });

  it("stops the run on Escape while one is streaming, and keeps the draft", () => {
    useChatStore.getState().setQuestion("half a question");
    const props = composer({ isSending: true });

    fireEvent.keyDown(textarea(), { key: "Escape" });
    expect(props.onStop).toHaveBeenCalledTimes(1);
    // Losing the draft as a side effect of cancelling would be the worse of
    // the two -- the run can be re-sent, the typing cannot.
    expect(useChatStore.getState().question).toBe("half a question");
  });

  it("leaves Escape alone when there is nothing to undo", () => {
    const props = composer({ isSending: false });
    const event = fireEvent.keyDown(textarea(), { key: "Escape", cancelable: true });
    // Not claimed, so a parent overlay can still take it.
    expect(event).toBe(true);
    expect(props.onStop).not.toHaveBeenCalled();
  });

  it("sends on Ctrl+Enter and on Cmd+Enter", () => {
    useChatStore.getState().setQuestion("ready");
    const props = composer({ isSending: false });

    fireEvent.keyDown(textarea(), { key: "Enter", ctrlKey: true });
    fireEvent.keyDown(textarea(), { key: "Enter", metaKey: true });
    expect(props.onAsk).toHaveBeenCalledTimes(2);
  });

  it("leaves a bare Enter to the textarea", () => {
    useChatStore.getState().setQuestion("ready");
    const props = composer({ isSending: false });

    fireEvent.keyDown(textarea(), { key: "Enter" });
    expect(props.onAsk).not.toHaveBeenCalled();
  });
});
