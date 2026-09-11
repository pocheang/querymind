import type { AuthUser, Citation, IndexedFileSummary, PromptTemplate, SessionMessage, ToolRun } from "@/types/api";

export type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

export type AgentMode = {
  key: AgentClassHint;
  title: string;
  desc: string;
};

export type WorkbenchActionProps = {
  onSwitchAgentMode: (mode: AgentClassHint) => void;
  onPdfTargetFileChange: (filename: string) => void;
  onDraftQuestion: () => void;
  onRefreshDocuments: () => Promise<void>;
  onUploadVisibilityChange: (visibility: "private" | "public") => void;
  onMainUploadChange: (evt: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  onDocsDrop: (evt: React.DragEvent<HTMLDivElement>) => Promise<void>;
  onDocDropActiveChange: (active: boolean) => void;
  onReindexDocument: (doc: IndexedFileSummary) => Promise<void>;
  onDeleteDocument: (doc: IndexedFileSummary, removeFile: boolean) => Promise<void>;
  onRefreshPrompts: () => Promise<void>;
  onPromptTitleChange: (title: string) => void;
  onPromptContentChange: (content: string) => void;
  onCheckPrompt: () => Promise<void>;
  onSavePrompt: () => Promise<void>;
  onUsePrompt: (prompt: PromptTemplate) => void;
  onEditPrompt: (prompt: PromptTemplate) => void;
  onDeletePrompt: (prompt: PromptTemplate) => Promise<void>;
};

export type Props = {
  user: AuthUser | null;
  onLogout: () => Promise<void>;
  onUserRefresh: () => Promise<void>;
};

export type Toast = {
  id: string;
  text: string;
  kind: "info" | "success" | "warn" | "error";
};

export type GraphEntity = {
  name: string;
  type: string;
  description?: string;
};

export type GraphNeighbor = {
  entity: string;
  relation: string;
  direction: "in" | "out";
};

export type GraphPath = {
  entities: string[];
  relations: string[];
};

export type GraphResult = {
  entities: GraphEntity[];
  neighbors: GraphNeighbor[];
  paths: GraphPath[];
  context?: string;
};

export type ChatMetadata = {
  route: string;
  execution_route?: string;
  agent_class: string;
  web_used: boolean;
  latency_ms?: number;
  thoughts: string[];
  graph_entities: string[];
  graph_result?: GraphResult;
  citations: Citation[];
  /** What the governed tool loop actually did. */
  tool_runs: ToolRun[];
  quality_report?: Record<string, unknown>;
  current_status?: string;
  execution_steps?: Array<{
    kind: string;
    label: string;
    detail?: string;
    at?: string;
  }>;
};

export type SetString = React.Dispatch<React.SetStateAction<string>>;
export type SetBoolean = React.Dispatch<React.SetStateAction<boolean>>;
export type SetMessageList = React.Dispatch<React.SetStateAction<SessionMessage[]>>;
