import { create } from "zustand";
import type { IndexedFileSummary, PromptTemplate, SessionMessage, SessionSummary } from "@/types/api";
import type { Toast } from "@/pages/chat/types";
import type { AgentClassHint } from "@/pages/chat/constants";

/** A setter that accepts a value directly or a `(prev) => next` updater, as every setter below does. */
type Updater<T> = T | ((prev: T) => T);

export interface ChatState {
  // Session State
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  sessions: SessionSummary[];
  sessionLoading: boolean;
  currentSessionId: string | null;
  messages: SessionMessage[];
  busySessionId: string | null;
  isCreatingSession: boolean;

  // Chat State
  question: string;
  isSending: boolean;
  runStatus: string;
  agentClassHint: AgentClassHint;
  pdfTargetFile: string;

  // Document State
  documents: IndexedFileSummary[];
  docsLoading: boolean;
  uploading: boolean;
  uploadInfo: string;
  uploadProgress: number;
  uploadProgressText: string;
  uploadVisibility: "private" | "public";
  docDropActive: boolean;
  composerDropActive: boolean;

  // Prompt State
  prompts: PromptTemplate[];
  promptsLoading: boolean;
  promptTitle: string;
  promptContent: string;
  editingPromptId: string | null;
  promptCheckInfo: string;

  // UI State
  toasts: Toast[];
  error: string;
  settingsOpen: boolean;

  // Actions / Setters
  setSidebarOpen: (open: Updater<boolean>) => void;
  setSidebarCollapsed: (collapsed: Updater<boolean>) => void;
  setSessions: (sessions: Updater<SessionSummary[]>) => void;
  setSessionLoading: (loading: Updater<boolean>) => void;
  setCurrentSessionId: (id: Updater<string | null>) => void;
  setMessages: (messages: Updater<SessionMessage[]>) => void;
  setBusySessionId: (id: Updater<string | null>) => void;
  setIsCreatingSession: (creating: Updater<boolean>) => void;

  setQuestion: (question: Updater<string>) => void;
  setIsSending: (isSending: Updater<boolean>) => void;
  setRunStatus: (status: Updater<string>) => void;
  setAgentClassHint: (hint: Updater<AgentClassHint>) => void;
  setPdfTargetFile: (file: Updater<string>) => void;

  setDocuments: (docs: Updater<IndexedFileSummary[]>) => void;
  setDocsLoading: (loading: Updater<boolean>) => void;
  setUploading: (uploading: Updater<boolean>) => void;
  setUploadInfo: (info: Updater<string>) => void;
  setUploadProgress: (progress: Updater<number>) => void;
  setUploadProgressText: (text: Updater<string>) => void;
  setUploadVisibility: (vis: Updater<"private" | "public">) => void;
  setDocDropActive: (active: Updater<boolean>) => void;
  setComposerDropActive: (active: Updater<boolean>) => void;

  setPrompts: (prompts: Updater<PromptTemplate[]>) => void;
  setPromptsLoading: (loading: Updater<boolean>) => void;
  setPromptTitle: (title: Updater<string>) => void;
  setPromptContent: (content: Updater<string>) => void;
  setEditingPromptId: (id: Updater<string | null>) => void;
  setPromptCheckInfo: (info: Updater<string>) => void;

  setToasts: (toasts: Updater<Toast[]>) => void;
  setError: (error: Updater<string>) => void;
  setSettingsOpen: (open: Updater<boolean>) => void;

  /** Drop every value this user filled in. Called on logout and on user change. */
  reset: () => void;
}

function updateValue<T>(val: Updater<T>, prev: T): T {
  return typeof val === "function" ? (val as (prev: T) => T)(prev) : val;
}

/** The data half of ChatState: every property that is not an action.
 *
 * Discriminated by value type, not by name: `settingsOpen` starts with "set"
 * too, so a `set${string}` key filter would have silently dropped it -- and a
 * field missing from INITIAL_STATE is exactly the drift this type exists to
 * catch.
 *
 * Typed rather than inferred so the compiler enforces that INITIAL_STATE covers
 * exactly these fields: a field added to ChatState but forgotten here is a
 * compile error, not a value that quietly survives a logout.
 */
type ChatData = {
  [K in keyof ChatState as ChatState[K] extends (...args: never[]) => unknown ? never : K]: ChatState[K];
};

const INITIAL_STATE: ChatData = {
  // Session State
  sidebarOpen: false,
  sidebarCollapsed: false,
  sessions: [],
  sessionLoading: true,
  currentSessionId: null,
  messages: [],
  busySessionId: null,
  isCreatingSession: false,

  // Chat State
  question: "",
  isSending: false,
  runStatus: "",
  agentClassHint: "",
  pdfTargetFile: "",

  // Document State
  documents: [],
  docsLoading: false,
  uploading: false,
  uploadInfo: "",
  uploadProgress: 0,
  uploadProgressText: "",
  uploadVisibility: "private",
  docDropActive: false,
  composerDropActive: false,

  // Prompt State
  prompts: [],
  promptsLoading: false,
  promptTitle: "",
  promptContent: "",
  editingPromptId: null,
  promptCheckInfo: "",

  // UI State
  toasts: [],
  error: "",
  settingsOpen: false,
};

export const useChatStore = create<ChatState>((set) => ({
  ...INITIAL_STATE,

  // Setters supporting both raw values and functional updates
  setSidebarOpen: (val) => set((s) => ({ sidebarOpen: updateValue(val, s.sidebarOpen) })),
  setSidebarCollapsed: (val) => set((s) => ({ sidebarCollapsed: updateValue(val, s.sidebarCollapsed) })),
  setSessions: (val) => set((s) => ({ sessions: updateValue(val, s.sessions) })),
  setSessionLoading: (val) => set((s) => ({ sessionLoading: updateValue(val, s.sessionLoading) })),
  setCurrentSessionId: (val) => set((s) => ({ currentSessionId: updateValue(val, s.currentSessionId) })),
  setMessages: (val) => set((s) => ({ messages: updateValue(val, s.messages) })),
  setBusySessionId: (val) => set((s) => ({ busySessionId: updateValue(val, s.busySessionId) })),
  setIsCreatingSession: (val) => set((s) => ({ isCreatingSession: updateValue(val, s.isCreatingSession) })),

  setQuestion: (val) => set((s) => ({ question: updateValue(val, s.question) })),
  setIsSending: (val) => set((s) => ({ isSending: updateValue(val, s.isSending) })),
  setRunStatus: (val) => set((s) => ({ runStatus: updateValue(val, s.runStatus) })),
  setAgentClassHint: (val) => set((s) => ({ agentClassHint: updateValue(val, s.agentClassHint) })),
  setPdfTargetFile: (val) => set((s) => ({ pdfTargetFile: updateValue(val, s.pdfTargetFile) })),

  setDocuments: (val) => set((s) => ({ documents: updateValue(val, s.documents) })),
  setDocsLoading: (val) => set((s) => ({ docsLoading: updateValue(val, s.docsLoading) })),
  setUploading: (val) => set((s) => ({ uploading: updateValue(val, s.uploading) })),
  setUploadInfo: (val) => set((s) => ({ uploadInfo: updateValue(val, s.uploadInfo) })),
  setUploadProgress: (val) => set((s) => ({ uploadProgress: updateValue(val, s.uploadProgress) })),
  setUploadProgressText: (val) => set((s) => ({ uploadProgressText: updateValue(val, s.uploadProgressText) })),
  setUploadVisibility: (val) => set((s) => ({ uploadVisibility: updateValue(val, s.uploadVisibility) })),
  setDocDropActive: (val) => set((s) => ({ docDropActive: updateValue(val, s.docDropActive) })),
  setComposerDropActive: (val) => set((s) => ({ composerDropActive: updateValue(val, s.composerDropActive) })),

  setPrompts: (val) => set((s) => ({ prompts: updateValue(val, s.prompts) })),
  setPromptsLoading: (val) => set((s) => ({ promptsLoading: updateValue(val, s.promptsLoading) })),
  setPromptTitle: (val) => set((s) => ({ promptTitle: updateValue(val, s.promptTitle) })),
  setPromptContent: (val) => set((s) => ({ promptContent: updateValue(val, s.promptContent) })),
  setEditingPromptId: (val) => set((s) => ({ editingPromptId: updateValue(val, s.editingPromptId) })),
  setPromptCheckInfo: (val) => set((s) => ({ promptCheckInfo: updateValue(val, s.promptCheckInfo) })),

  setToasts: (val) => set((s) => ({ toasts: updateValue(val, s.toasts) })),
  setError: (val) => set((s) => ({ error: updateValue(val, s.error) })),
  setSettingsOpen: (val) => set((s) => ({ settingsOpen: updateValue(val, s.settingsOpen) })),

  reset: () => set(INITIAL_STATE),
}));
