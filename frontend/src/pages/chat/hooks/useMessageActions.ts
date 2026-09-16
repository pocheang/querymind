import { useEffect, useRef } from "react";
import { appApi } from "@/lib/api";
import { useChatStore } from "@/stores/useChatStore";
import type { NormalizedQueryResult, PendingApproval, SessionMessage, SessionSummary } from "@/types/api";
import { EMPTY_METADATA, RUN_STATUS_PROCESSING } from "@/pages/chat/constants";
import { isAbortError, createInitialStreamMessages } from "./streamUtils";
import { createStreamMessageUpdater } from "./streamMessageUpdater";
import { createChatRunLifecycle } from "./chatStreamAdapter";
import { randomId } from "@/lib/randomId";

type RunLifecycle = ReturnType<typeof createChatRunLifecycle>;

/** Release everything one `ask` run holds: the "active run" marker, the abort
 *  controller slot, and -- only when this run is still the one in charge --
 *  the sending/status UI state. Shared by the two places a run ends: giving
 *  up before streaming starts, and the `finally` after it. */
function finishRun(
  active: boolean,
  run: number,
  runAbort: AbortController,
  refs: {
    activeRunRef: React.MutableRefObject<number | null>;
    streamAbortRef: React.MutableRefObject<AbortController | null>;
    runLifecycleRef: React.MutableRefObject<RunLifecycle>;
  },
  setIsSending: (sending: boolean) => void,
  setRunStatus: (status: string) => void
): void {
  if (active) {
    setIsSending(false);
    setRunStatus("");
    refs.runLifecycleRef.current.stop(run);
  }
  if (refs.activeRunRef.current === run) refs.activeRunRef.current = null;
  if (refs.streamAbortRef.current === runAbort) refs.streamAbortRef.current = null;
}

/** Replace the streaming placeholder with the finished, persisted answer.
 *  Exported for `streamDraft.test.ts`, which pins the one thing about it that
 *  is not obvious from reading it: the metadata block is rebuilt from
 *  EMPTY_METADATA, so every field the response does not carry is erased. */
export function applyStreamResult(messages: SessionMessage[], result: NormalizedQueryResult): SessionMessage[] {
  return messages.map((message) =>
    message.message_id === "local-assistant-stream"
      ? {
          ...message,
          content: result.answer,
          metadata: {
            ...EMPTY_METADATA,
            route: result.route || "",
            citations: result.citations,
            tool_runs: result.toolRuns,
            quality_report: result.qualityReport,
            // None unless `use_reasoning` was sent with this request. The
            // response's copy wins when there is one -- it is the persisted,
            // final-redaction-pass text, not the streamed draft. But this
            // whole metadata block is rebuilt from EMPTY_METADATA, so a plain
            // assignment ALSO erased an accumulated draft whenever the
            // response carried no reasoning of its own, and the panel the
            // reader had been watching vanished at the moment the answer
            // landed. Falling back to what was already on the message keeps
            // "the response did not report reasoning" from meaning "there was
            // none".
            reasoning: result.reasoning ?? message.metadata?.reasoning,
            reasoning_duration_ms: result.reasoningDurationMs ?? message.metadata?.reasoning_duration_ms,
          },
        }
      : message
  );
}

/** Apply one incremental streaming update to the draft placeholder.
 *
 * Matches by id alone, the same way `applyStreamResult` above matches the
 * final replacement. This used to also require the message's own content to
 * be empty -- which is true only for the very first fragment.
 * `useExecutionTrace`'s `draft` is the *cumulative* text (the reducer does
 * `state.draft + action.text`), so every fragment after the first already
 * has non-empty content and the update was silently dropped: the bubble
 * showed one early snapshot, then sat frozen until `applyStreamResult`
 * replaced it with the finished answer. That reads as "the answer appears
 * all at once", even though the model underneath is genuinely streaming --
 * `LocalEvidenceChatModel.stream()` paces its chunks with a real delay
 * between them, and nothing about that pacing ever reached the screen. */
export function applyStreamDraft(messages: SessionMessage[], text: string): SessionMessage[] {
  return messages.map((message) =>
    message.message_id === "local-assistant-stream" ? { ...message, content: text } : message
  );
}

/** Apply one incremental reasoning update to the draft placeholder.
 *
 * Same shape as `applyStreamDraft` above, same reason -- `text` is the
 * cumulative reasoning-so-far, matched by id alone. Held on
 * `metadata.reasoning` rather than a new top-level message field so
 * `ThinkingPanel` reads it the same way whether the message is still
 * streaming or already persisted and reloaded. */
export function applyThinkingDraft(messages: SessionMessage[], text: string): SessionMessage[] {
  return messages.map((message) =>
    message.message_id === "local-assistant-stream"
      ? { ...message, metadata: { ...(message.metadata || EMPTY_METADATA), reasoning: text } }
      : message
  );
}

interface ChatActions {
  notify: (message: string, type: "success" | "info" | "warn" | "error") => void;
  handleApiError: (e: unknown, fallback: string) => Promise<void>;
  createSession: (signal?: AbortSignal) => Promise<string | null>;
  editMessage: (msg: SessionMessage) => Promise<void>;
  removeMessage: (msg: SessionMessage) => Promise<void>;
  refreshSessions: (silent?: boolean, background?: boolean) => Promise<SessionSummary[]>;
}

interface UseMessageActionsParams {
  currentSessionId: string | null;
  actions: ChatActions;
  setRunStatus: (status: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<SessionMessage[]>>;
  setIsSending: (sending: boolean) => void;
  setQuestion: (question: string) => void;
  onExecutionId?: (executionId: string | null) => void;
  onCreditsChanged?: () => Promise<void>;
  /** Raised when a run produced a governed action it did not perform, together
   *  with the question that produced it. Confirming re-runs `ask` with that
   *  question and the token, which is what actually executes the action.
   *
   *  The question comes from here rather than being tracked alongside `ask`
   *  call sites: there are three of them, and one forgetting to record it means
   *  a confirmation silently resends a stale question. */
  onPendingApproval?: (pending: PendingApproval | null, question: string) => void;
}

interface UseMessageActionsReturn {
  editMessage: (msg: SessionMessage) => Promise<void>;
  removeMessage: (msg: SessionMessage) => Promise<void>;
  ensureSessionForAsk: () => Promise<string | null>;
  stopCurrentRun: (isSending: boolean) => void;
  ask: (params: { question: string; isSending: boolean; sessionId?: string; approvalToken?: string }) => Promise<void>;
}

type RunRefs = {
  activeRunRef: React.MutableRefObject<number | null>;
  streamAbortRef: React.MutableRefObject<AbortController | null>;
  runLifecycleRef: React.MutableRefObject<RunLifecycle>;
};

/** Reject an empty or already-in-flight question and claim a run slot, or
 *  hand back null for "there is nothing to start". Split out purely to keep
 *  this pair of checks out of `ask`'s own complexity count -- the ref
 *  mutations that follow (creating the abort controller, marking it as the
 *  active stream) stay inline in `ask` itself, on purpose: react-hooks'
 *  exhaustive-deps warns on a ref read inside the unmount cleanup below
 *  unless it can see, in this same component, where that ref is written --
 *  moving the write into an outer function hid it from that check. */
function claimRunSlot(
  q: string,
  isSending: boolean,
  runLifecycleRef: React.MutableRefObject<RunLifecycle>,
  activeRunRef: React.MutableRefObject<number | null>
): number | null {
  if (!q || isSending) return null;
  const run = runLifecycleRef.current.begin();
  if (run === null) return null;
  activeRunRef.current = run;
  return run;
}

interface ResolveSessionParams {
  run: number;
  sessionId: string | undefined;
  runAbort: AbortController;
  isRunActive: () => boolean;
  refs: RunRefs;
  ensureSessionForAsk: (signal?: AbortSignal) => Promise<string | null>;
  setIsSending: (sending: boolean) => void;
  setQuestion: (question: string) => void;
  setRunStatus: (status: string) => void;
  onExecutionId?: (executionId: string | null) => void;
}

/** The rest of `ask`'s old setup: bail if the run was already superseded,
 *  otherwise mark the UI as sending and resolve (or create) the session --
 *  giving the run slot back via `finishRun` if that resolution loses the
 *  race. Returns the session id to proceed with, or null to abandon. */
async function resolveSessionOrAbandon({
  run,
  sessionId,
  runAbort,
  isRunActive,
  refs,
  ensureSessionForAsk,
  setIsSending,
  setQuestion,
  setRunStatus,
  onExecutionId,
}: ResolveSessionParams): Promise<string | null> {
  if (!isRunActive()) return null;
  onExecutionId?.(null);
  setIsSending(true);
  setQuestion("");
  setRunStatus(RUN_STATUS_PROCESSING);
  const sid = sessionId || (await ensureSessionForAsk(runAbort.signal));
  if (!sid || !isRunActive()) {
    finishRun(isRunActive(), run, runAbort, refs, setIsSending, setRunStatus);
    return null;
  }
  return sid;
}

interface RunQueryStreamParams {
  q: string;
  sid: string;
  approvalToken: string | undefined;
  runAbort: AbortController;
  isRunActive: () => boolean;
  streamStoppedRef: React.MutableRefObject<boolean>;
  messageUpdater: ReturnType<typeof createStreamMessageUpdater>;
  setMessages: React.Dispatch<React.SetStateAction<SessionMessage[]>>;
  onExecutionId?: (executionId: string | null) => void;
  onPendingApproval?: (pending: PendingApproval | null, question: string) => void;
  onCreditsChanged?: () => Promise<void>;
  actions: ChatActions;
}

/** The request itself: call the API, apply a streamed answer, or resolve one
 *  of the ways it can fail. Split out of `ask` for the same reason
 *  `beginRun` was -- each branch here was paying a nesting cost for sitting
 *  inside `ask`'s own try/catch as well as its own. */
async function runQueryAndStream({
  q,
  sid,
  approvalToken,
  runAbort,
  isRunActive,
  streamStoppedRef,
  messageUpdater,
  setMessages,
  onExecutionId,
  onPendingApproval,
  onCreditsChanged,
  actions,
}: RunQueryStreamParams): Promise<void> {
  try {
    const { useWebSearch, showReasoning } = useChatStore.getState();
    // Generated here, not read from the response: `appApi.advanced` does not
    // resolve until the whole run has finished, so an id taken from its
    // result becomes known too late to watch the run live. Exposing our own
    // id up front lets the trace panel's SSE subscription open while this
    // request is still in flight.
    const executionId = randomId();
    onExecutionId?.(executionId);
    const result = await appApi.advanced({
      query: q,
      sessionId: sid,
      enableDecomposition: true,
      enableSelfRag: true,
      useWebFallback: useWebSearch,
      useReasoning: showReasoning,
      ...(approvalToken ? { approvalToken } : {}),
      executionId,
      signal: runAbort.signal,
    });
    if (!isRunActive()) return;
    // A resumed run either performed the action or reported why it could not;
    // either way the previous pending approval is spent.
    onPendingApproval?.(result.status === "pending_approval" ? result.pendingApproval : null, q);
    setMessages((prev) => applyStreamResult(prev, result));
    // The backend now persists both turns; reconcile the optimistic local
    // messages with what actually landed in the session history.
    await actions.refreshSessions(true, true);
    await onCreditsChanged?.();
  } catch (e) {
    if (!isRunActive()) return;
    if (isAbortError(e, streamStoppedRef.current)) {
      messageUpdater.replaceWithStoppedMessage("");
      actions.notify("Generation stopped", "info");
      return;
    }
    await actions.handleApiError(e, "Request failed. Please check backend/model status.");
    if (!isRunActive()) return;
    const message = e instanceof Error && e.message ? e.message : "Request failed";
    messageUpdater.replaceWithErrorMessage(message);
  }
}

export function useMessageActions({
  currentSessionId,
  actions,
  setRunStatus,
  setMessages,
  setIsSending,
  setQuestion,
  onExecutionId,
  onCreditsChanged,
  onPendingApproval,
}: UseMessageActionsParams): UseMessageActionsReturn {
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamStoppedRef = useRef(false);
  const runLifecycleRef = useRef(createChatRunLifecycle());
  const activeRunRef = useRef<number | null>(null);

  useEffect(() => {
    const lifecycle = runLifecycleRef.current;
    lifecycle.mount();
    return () => {
      streamStoppedRef.current = true;
      lifecycle.dispose();
      streamAbortRef.current?.abort();
    };
  }, []);

  const editMessage = async (msg: SessionMessage) => {
    if (!currentSessionId) return;
    if (msg.role === "user") setRunStatus("Re-running");
    await actions.editMessage(msg);
    if (msg.role === "user") await onCreditsChanged?.();
    setRunStatus("");
  };

  const removeMessage = async (msg: SessionMessage) => {
    await actions.removeMessage(msg);
  };

  const ensureSessionForAsk = async (signal?: AbortSignal) => {
    if (currentSessionId) return currentSessionId;
    return actions.createSession(signal);
  };

  const stopCurrentRun = (isSending: boolean) => {
    if (!isSending) return;
    streamStoppedRef.current = true;
    setRunStatus("Stopping...");
    try {
      streamAbortRef.current?.abort();
    } catch {
      // ignore abort errors
    }
  };

  const ask = async ({
    question,
    isSending,
    sessionId,
    approvalToken,
  }: {
    question: string;
    isSending: boolean;
    sessionId?: string;
    approvalToken?: string;
  }) => {
    const q = question.trim();
    const run = claimRunSlot(q, isSending, runLifecycleRef, activeRunRef);
    if (run === null) return;
    const isRunActive = () => runLifecycleRef.current.isActive(run);
    const runAbort = new AbortController();
    streamAbortRef.current = runAbort;
    streamStoppedRef.current = false;

    const refs = { activeRunRef, streamAbortRef, runLifecycleRef };
    const sid = await resolveSessionOrAbandon({
      run,
      sessionId,
      runAbort,
      isRunActive,
      refs,
      ensureSessionForAsk,
      setIsSending,
      setQuestion,
      setRunStatus,
      onExecutionId,
    });
    if (!sid) return;

    setMessages((prev) => [...prev, ...createInitialStreamMessages(q)]);
    const messageUpdater = createStreamMessageUpdater({ setMessages });

    try {
      await runQueryAndStream({
        q,
        sid,
        approvalToken,
        runAbort,
        isRunActive,
        streamStoppedRef,
        messageUpdater,
        setMessages,
        onExecutionId,
        onPendingApproval,
        onCreditsChanged,
        actions,
      });
    } finally {
      finishRun(
        isRunActive(),
        run,
        runAbort,
        { activeRunRef, streamAbortRef, runLifecycleRef },
        setIsSending,
        setRunStatus
      );
    }
  };

  return {
    editMessage,
    removeMessage,
    ensureSessionForAsk,
    stopCurrentRun,
    ask,
  };
}
