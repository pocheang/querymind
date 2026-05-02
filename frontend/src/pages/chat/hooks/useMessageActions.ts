import { useRef } from "react";
import { appApi } from "@/lib/api";
import type { SessionMessage } from "@/types/api";
import { EMPTY_METADATA } from "@/pages/chat/constants";
import {
  isAbortError,
  isNetworkError,
  parseStreamError,
  createInitialStreamMessages,
} from "./streamUtils";
import {
  createStreamEventHandlers,
  type StreamEventContext,
  type StreamMetadata,
} from "./streamEventHandlers";
import { createStreamMessageUpdater } from "./streamMessageUpdater";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";
type RetrievalStrategy = "baseline" | "advanced" | "safe";

interface ChatActions {
  notify: (message: string, type: "success" | "info" | "warn" | "error") => void;
  handleApiError: (e: unknown, fallback: string) => Promise<void>;
  createSession: () => Promise<string | null>;
  editMessage: (msg: SessionMessage, useWeb: boolean, useReasoning: boolean) => Promise<void>;
  removeMessage: (msg: SessionMessage) => Promise<void>;
  refreshSessions: (silent?: boolean, background?: boolean) => Promise<any[]>;
}

interface UseMessageActionsParams {
  currentSessionId: string | null;
  actions: ChatActions;
  setRunStatus: (status: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<SessionMessage[]>>;
  setIsSending: (sending: boolean) => void;
  setQuestion: (question: string) => void;
}

interface UseMessageActionsReturn {
  editMessage: (msg: SessionMessage, useWeb: boolean, useReasoning: boolean) => Promise<void>;
  removeMessage: (msg: SessionMessage) => Promise<void>;
  ensureSessionForAsk: () => Promise<string | null>;
  stopCurrentRun: (isSending: boolean) => void;
  ask: (params: {
    question: string;
    isSending: boolean;
    useWeb: boolean;
    useReasoning: boolean;
    agentClassHint: AgentClassHint;
    retrievalStrategy: RetrievalStrategy;
  }) => Promise<void>;
}

export function useMessageActions({
  currentSessionId,
  actions,
  setRunStatus,
  setMessages,
  setIsSending,
  setQuestion,
}: UseMessageActionsParams): UseMessageActionsReturn {
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamStoppedRef = useRef(false);

  const editMessage = async (msg: SessionMessage, useWeb: boolean, useReasoning: boolean) => {
    if (!currentSessionId) return;
    if (msg.role === "user") setRunStatus("Re-running");
    await actions.editMessage(msg, useWeb, useReasoning);
    setRunStatus("");
  };

  const removeMessage = async (msg: SessionMessage) => {
    await actions.removeMessage(msg);
  };

  const ensureSessionForAsk = async () => {
    if (currentSessionId) return currentSessionId;
    return actions.createSession();
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
    useWeb,
    useReasoning,
    agentClassHint,
    retrievalStrategy,
  }: {
    question: string;
    isSending: boolean;
    useWeb: boolean;
    useReasoning: boolean;
    agentClassHint: AgentClassHint;
    retrievalStrategy: RetrievalStrategy;
  }) => {
    const q = question.trim();
    if (!q || isSending) return;
    streamStoppedRef.current = false;
    const sid = await ensureSessionForAsk();
    if (!sid) return;

    setIsSending(true);
    setQuestion("");
    setRunStatus("Processing");
    setMessages((prev) => [...prev, ...createInitialStreamMessages(q)]);

    const eventHandlers = createStreamEventHandlers();
    const messageUpdater = createStreamMessageUpdater({ setMessages });

    try {
      const runStartedAt = performance.now();
      const elapsedMs = () => Math.max(1, Math.round(performance.now() - runStartedAt));
      const streamAbort = new AbortController();
      streamAbortRef.current = streamAbort;

      const res = await appApi.streamQuery({
        question: q,
        useWebFallback: useWeb,
        useReasoning,
        sessionId: sid,
        agentClassHint: agentClassHint || undefined,
        retrievalStrategy,
        signal: streamAbort.signal,
      });

      if (!res.ok || !res.body) {
        const raw = await res.text();
        throw new Error(parseStreamError(raw));
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      let ctx: StreamEventContext = {
        answer: "",
        thoughts: [],
        meta: { ...EMPTY_METADATA } as StreamMetadata,
        executionSteps: [...(EMPTY_METADATA.execution_steps || [])],
        elapsedMs,
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const line = part.split("\n").find((x) => x.startsWith("data: "));
          if (!line) continue;

          let evt: any;
          try {
            evt = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (evt.type === "status") {
            const { nextStatus, updatedCtx } = eventHandlers.handleStatusEvent(evt, ctx);
            ctx = updatedCtx;
            setRunStatus(nextStatus);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "route") {
            ctx = eventHandlers.handleRouteEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "thought") {
            ctx = eventHandlers.handleThoughtEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "error") {
            const { error, updatedCtx } = eventHandlers.handleErrorEvent(evt, ctx);
            ctx = updatedCtx;
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
            throw error;
          } else if (evt.type === "vector_result") {
            ctx = eventHandlers.handleVectorResultEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "graph_result") {
            ctx = eventHandlers.handleGraphResultEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "web_result") {
            ctx = eventHandlers.handleWebResultEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "answer_chunk") {
            ctx = eventHandlers.handleAnswerChunkEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "answer_reset") {
            ctx = eventHandlers.handleAnswerResetEvent(evt, ctx);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          } else if (evt.type === "done") {
            ctx = eventHandlers.handleDoneEvent(evt, ctx, retrievalStrategy);
            messageUpdater.patchStreamMessage(ctx.answer, ctx.meta);
          }
        }
      }

      const detail = await appApi.sessionDetail(sid);
      messageUpdater.updateFinalMessage(detail.messages || [], ctx.meta);
      await actions.refreshSessions();
    } catch (e) {
      if (isAbortError(e, streamStoppedRef.current)) {
        messageUpdater.replaceWithStoppedMessage("");
        actions.notify("Generation stopped", "info");
        return;
      }

      const fallback = "Request failed. Please check backend/model status.";
      await actions.handleApiError(e, fallback);
      const rawErrorText = e instanceof Error && e.message ? e.message : fallback;
      const isNetworkDisconnect = isNetworkError(rawErrorText);
      let visibleError = isNetworkDisconnect
        ? "NetworkError: stream disconnected. Retrying with non-stream mode..."
        : rawErrorText;

      if (isNetworkDisconnect && sid) {
        try {
          const fallbackRes = await appApi.query({
            question: q,
            useWebFallback: useWeb,
            useReasoning,
            sessionId: sid,
            agentClassHint: agentClassHint || undefined,
            retrievalStrategy,
          });
          visibleError = String(fallbackRes.answer || "No answer returned");
        } catch {
          visibleError = "NetworkError: stream disconnected. Please verify backend(8000), Ollama(11434), then retry.";
        }
      }

      messageUpdater.replaceWithErrorMessage(visibleError);
    } finally {
      streamAbortRef.current = null;
      streamStoppedRef.current = false;
      setIsSending(false);
      setRunStatus("");
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
