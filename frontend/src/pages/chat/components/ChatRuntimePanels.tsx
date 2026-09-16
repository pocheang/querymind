import { useEffect, useRef } from "react";

import { ExecutionTracePanel } from "@/features/execution-trace/ExecutionTracePanel";
import { useExecutionTrace } from "@/features/execution-trace/useExecutionTrace";
import { ToolApprovalPanel } from "@/features/tool-approval/ToolApprovalPanel";
import { GenerationStatusLine } from "@/pages/chat/components/GenerationStatusLine";
import type { PendingApproval } from "@/types/api";

/** The SSE stream's own end-of-run marker: `_terminal_event`
 *  (app/api/routes/public/orchestration.py) always emits exactly one event
 *  with this shape as the last thing it sends. */
function isRunFinished(events: readonly { stage: string }[]): boolean {
  return events.some((event) => event.stage === "complete" || event.stage === "failed");
}

type Props = {
  executionId: string | null;
  /** Whether a request is actually in flight. `executionId` alone is not
   *  enough to know when the live status line should stop: it is never
   *  cleared once a run finishes (the trace panel stays visible with its
   *  final step count), and a run that fails before its first trace event --
   *  a credit check rejecting it outright, for instance -- never emits the
   *  `complete`/`failed` terminal event `isRunFinished` looks for either. Without
   *  this, that combination left the status line frozen on "Getting started"
   *  forever after the request had already come back. */
  isSending: boolean;
  /** From the query response, not from the SSE trace: only the response path
   *  knows the question, and resuming means re-sending it with the token. */
  pendingApproval: PendingApproval | null;
  onApproved: (token: string) => Promise<void> | void;
  onDismissApproval: () => void;
  /** The answer as it streams in, already redacted server-side. A draft: the
   *  final answer replaces it once citation numbering and the reference list
   *  are decided. */
  onDraft?: (text: string) => void;
  /** The model's reasoning as it streams in, same draft caveats as `onDraft`.
   *  Only ever non-empty when the request opted in to visible reasoning. */
  onThinking?: (text: string) => void;
};

export function ChatRuntimePanels({
  executionId,
  isSending,
  pendingApproval,
  onApproved,
  onDismissApproval,
  onDraft,
  onThinking,
}: Readonly<Props>) {
  const executionTrace = useExecutionTrace(executionId);
  const draft = executionTrace.draft;
  const thinking = executionTrace.thinking;

  // The effect must fire when the *draft* changes, not when the parent
  // re-renders. Depending on `onDraft` directly makes an inline arrow -- which
  // is what the call site passes -- a new dependency on every render, so
  // publishing a draft re-renders the parent, which recreates the callback,
  // which re-fires the effect: "Maximum update depth exceeded", and the chat
  // error boundary catches it. Holding the latest callback in a ref keeps the
  // parent free to pass a fresh closure without that closing a loop.
  const onDraftRef = useRef(onDraft);
  useEffect(() => {
    onDraftRef.current = onDraft;
  });
  useEffect(() => {
    onDraftRef.current?.(draft);
  }, [draft]);
  // Same shape, same reason, for the reasoning channel.
  const onThinkingRef = useRef(onThinking);
  useEffect(() => {
    onThinkingRef.current = onThinking;
  });
  useEffect(() => {
    onThinkingRef.current?.(thinking);
  }, [thinking]);
  if (!executionId && !pendingApproval) return null;

  return (
    <>
      <GenerationStatusLine
        events={executionTrace.events}
        active={isSending && Boolean(executionId) && !isRunFinished(executionTrace.events)}
      />
      <ExecutionTracePanel trace={executionTrace} />
      <ToolApprovalPanel approval={pendingApproval} onApproved={onApproved} onDismiss={onDismissApproval} />
    </>
  );
}
