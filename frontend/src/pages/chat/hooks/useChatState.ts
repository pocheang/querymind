import { useState } from "react";
import type { SessionSummary, SessionMessage } from "@/types/api";
import type { Toast } from "@/pages/chat/types";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";
type RetrievalStrategy = "baseline" | "advanced" | "safe";

export function useChatState() {
  // UI state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [error, setError] = useState("");
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Session state
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [busySessionId, setBusySessionId] = useState<string | null>(null);

  // Message state
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [runStatus, setRunStatus] = useState("");

  // Query options
  const [useWeb, setUseWeb] = useState(false);
  const [useReasoning, setUseReasoning] = useState(false);
  const [agentClassHint, setAgentClassHint] = useState<AgentClassHint>("");
  const [retrievalStrategy, setRetrievalStrategy] = useState<RetrievalStrategy>("advanced");
  const [pdfTargetFile, setPdfTargetFile] = useState("");

  // Drop state
  const [composerDropActive, setComposerDropActive] = useState(false);

  return {
    // UI
    sidebarOpen,
    setSidebarOpen,
    settingsOpen,
    setSettingsOpen,
    error,
    setError,
    toasts,
    setToasts,

    // Session
    sessions,
    setSessions,
    sessionLoading,
    setSessionLoading,
    currentSessionId,
    setCurrentSessionId,
    busySessionId,
    setBusySessionId,

    // Message
    messages,
    setMessages,
    question,
    setQuestion,
    isSending,
    setIsSending,
    runStatus,
    setRunStatus,

    // Query options
    useWeb,
    setUseWeb,
    useReasoning,
    setUseReasoning,
    agentClassHint,
    setAgentClassHint,
    retrievalStrategy,
    setRetrievalStrategy,
    pdfTargetFile,
    setPdfTargetFile,

    // Drop
    composerDropActive,
    setComposerDropActive,
  };
}

export type ChatState = ReturnType<typeof useChatState>;
