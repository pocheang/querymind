// @vitest-environment jsdom
import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatRuntimePanels } from "./ChatRuntimePanels";

/**
 * The streaming draft is published to the parent from an effect. Depending on
 * the callback itself made an inline arrow -- which is what ChatPage passes -- a
 * new dependency on every render, so publishing a draft re-rendered the parent,
 * which recreated the callback, which re-fired the effect. In the browser that
 * surfaced as "Maximum update depth exceeded" and the chat error boundary
 * replacing the whole conversation with an error card.
 */
let draft = "";
let thinking = "";
let traceEvents: readonly { stage: string }[] = [];
const statusLineActiveCalls: boolean[] = [];
const lastActiveCall = () => statusLineActiveCalls[statusLineActiveCalls.length - 1];

vi.mock("@/features/execution-trace/useExecutionTrace", () => ({
  useExecutionTrace: () => ({ events: traceEvents, draft, thinking, connected: true, error: null }),
}));
vi.mock("@/features/execution-trace/ExecutionTracePanel", () => ({
  ExecutionTracePanel: () => null,
}));
vi.mock("@/pages/chat/components/GenerationStatusLine", () => ({
  GenerationStatusLine: ({ active }: { active: boolean }) => {
    statusLineActiveCalls.push(active);
    return null;
  },
}));
vi.mock("@/features/tool-approval/ToolApprovalPanel", () => ({
  ToolApprovalPanel: () => null,
}));

afterEach(() => {
  draft = "";
  thinking = "";
  traceEvents = [];
  statusLineActiveCalls.length = 0;
});

const props = {
  executionId: "exec-1",
  isSending: true,
  pendingApproval: null,
  onApproved: () => {},
  onDismissApproval: () => {},
};

describe("publishing the draft", () => {
  it("does not re-fire when the parent passes a new callback identity", () => {
    const calls: string[] = [];
    const { rerender } = render(<ChatRuntimePanels {...props} onDraft={(t) => calls.push(t)} />);

    // Every rerender passes a *different* arrow, exactly as ChatPage does.
    for (let i = 0; i < 5; i += 1) {
      rerender(<ChatRuntimePanels {...props} onDraft={(t) => calls.push(t)} />);
    }

    expect(calls).toHaveLength(1);
  });

  it("still fires when the draft itself changes", () => {
    const calls: string[] = [];
    const { rerender } = render(<ChatRuntimePanels {...props} onDraft={(t) => calls.push(t)} />);

    draft = "Revenue grew";
    rerender(<ChatRuntimePanels {...props} onDraft={(t) => calls.push(t)} />);
    draft = "Revenue grew twelve percent.";
    rerender(<ChatRuntimePanels {...props} onDraft={(t) => calls.push(t)} />);

    expect(calls).toEqual(["", "Revenue grew", "Revenue grew twelve percent."]);
  });

  it("uses the newest callback, not the one from the first render", () => {
    /** A ref that is never updated would be the other way to break this. */
    const first: string[] = [];
    const latest: string[] = [];
    const { rerender } = render(<ChatRuntimePanels {...props} onDraft={(t) => first.push(t)} />);

    rerender(<ChatRuntimePanels {...props} onDraft={(t) => latest.push(t)} />);
    draft = "written by the newest closure";
    rerender(<ChatRuntimePanels {...props} onDraft={(t) => latest.push(t)} />);

    expect(latest).toContain("written by the newest closure");
    expect(first).toEqual([""]);
  });
});

describe("publishing the reasoning draft", () => {
  /** Same effect shape as `onDraft` above, same risk: a fresh `onThinking`
   *  arrow every render must not re-fire the publish effect. */
  it("does not re-fire when the parent passes a new callback identity", () => {
    const calls: string[] = [];
    const { rerender } = render(<ChatRuntimePanels {...props} onThinking={(t) => calls.push(t)} />);

    for (let i = 0; i < 5; i += 1) {
      rerender(<ChatRuntimePanels {...props} onThinking={(t) => calls.push(t)} />);
    }

    expect(calls).toHaveLength(1);
  });

  it("still fires when the reasoning draft itself changes, independent of the answer draft", () => {
    const calls: string[] = [];
    const { rerender } = render(<ChatRuntimePanels {...props} onThinking={(t) => calls.push(t)} />);

    thinking = "Step 1: analyze";
    rerender(<ChatRuntimePanels {...props} onThinking={(t) => calls.push(t)} />);
    draft = "unrelated answer text";
    rerender(<ChatRuntimePanels {...props} onThinking={(t) => calls.push(t)} />);

    expect(calls).toEqual(["", "Step 1: analyze"]);
  });
});

describe("the live status line's active flag", () => {
  /**
   * Observed live (2026-09-15): a request rejected before its first trace
   * event -- an insufficient-credits guard, in this case -- never emits the
   * `complete`/`failed` terminal event `isRunFinished` looks for, and
   * `executionId` is never cleared once a run ends (the trace panel keeps
   * showing its final step count). Driving `active` off those two alone left
   * `GenerationStatusLine` stuck on "Getting started" forever after the
   * composer had already gone back to idle. `isSending` is the one signal
   * that actually tracks "is a request in flight," so it has to gate `active`
   * too, not just the trace-derived pieces.
   */
  it("stops once isSending goes false, even with no terminal trace event", () => {
    const { rerender } = render(<ChatRuntimePanels {...props} isSending={true} />);
    expect(lastActiveCall()).toBe(true);

    rerender(<ChatRuntimePanels {...props} isSending={false} />);

    expect(lastActiveCall()).toBe(false);
  });

  it("stops once the trace reports its own terminal event", () => {
    const { rerender } = render(<ChatRuntimePanels {...props} isSending={true} />);
    expect(lastActiveCall()).toBe(true);

    traceEvents = [{ stage: "complete" }];
    rerender(<ChatRuntimePanels {...props} isSending={true} />);

    expect(lastActiveCall()).toBe(false);
  });

  it("is not active with no execution id, even while isSending is true", () => {
    // A bare `executionId: null` would hit the component's own early return
    // (no execution id and no pending approval -- nothing to show at all),
    // which would make this pass for the wrong reason: the status line
    // never rendering is not the same claim as it rendering with
    // `active: false`. A pending approval keeps the component rendering
    // without an execution id to isolate that.
    render(
      <ChatRuntimePanels
        {...props}
        executionId={null}
        isSending={true}
        pendingApproval={{ tool_id: "t1", token: "tok", summary: "" }}
      />
    );

    expect(lastActiveCall()).toBe(false);
  });
});
