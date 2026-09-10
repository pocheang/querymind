import { useEffect, useRef } from "react";
import { appApi } from "@/lib/api";
import type { NormalizedQueryResult, PendingApproval, SessionMessage, SessionSummary } from "@/types/api";
import { EMPTY_METADATA } from "@/pages/chat/constants";
import { isAbortError, createInitialStreamMessages } from "./streamUtils";
import { createStreamMessageUpdater } from "./streamMessageUpdater";
import { createChatRunLifecycle } from "./chatStreamAdapter";

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
  setRunStatus: (status: string) => void,
): void {
  if (active) {
    setIsSending(false);
    setRunStatus("");
    refs.runLifecycleRef.current.stop(run);
  }
  if (refs.activeRunRef.current === run) refs.activeRunRef.current = null;
  if (refs.streamAbortRef.current === runAbort) refs.streamAbortRef.current = null;
}

function applyStreamResult(messages: SessionMessage[], result: NormalizedQueryResult): SessionMessage[] {
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
          },
        }
      : message,
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
  ask: (params: {
    question: string;
    isSending: boolean;
    sessionId?: string;
    approvalToken?: string;
  }) => Promise<void>;
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
    if (!q || isSending) return;
    const run = runLifecycleRef.current.begin();
    if (run === null) return;
    activeRunRef.current = run;
    const isRunActive = () => runLifecycleRef.current.isActive(run);
    const runAbort = new AbortController();
    streamAbortRef.current = runAbort;
    streamStoppedRef.current = false;
    if (!isRunActive()) return;
    onExecutionId?.(null);
    setIsSending(true);
    setQuestion("");
    setRunStatus("Processing");
    const sid = sessionId || await ensureSessionForAsk(runAbort.signal);
    if (!sid || !isRunActive()) {
      finishRun(
        isRunActive(),
        run,
        runAbort,
        { activeRunRef, streamAbortRef, runLifecycleRef },
        setIsSending,
        setRunStatus,
      );
      return;
    }

    setMessages((prev) => [...prev, ...createInitialStreamMessages(q)]);
    const messageUpdater = createStreamMessageUpdater({ setMessages });

    try {
      const result = await appApi.advanced({
        query: q,
        sessionId: sid,
        enableDecomposition: true,
        enableSelfRag: true,
        ...(approvalToken ? { approvalToken } : {}),
        signal: runAbort.signal,
      });
      if (!isRunActive()) return;
      if (result.executionId) onExecutionId?.(result.executionId);
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
    } finally {
      finishRun(
        isRunActive(),
        run,
        runAbort,
        { activeRunRef, streamAbortRef, runLifecycleRef },
        setIsSending,
        setRunStatus,
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
