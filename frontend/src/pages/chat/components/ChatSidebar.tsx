import { useState } from "react";
import type { SessionSummary, IndexedFileSummary, PromptTemplate } from "@/types/api";
import { SessionList } from "./SessionList";
import { DocumentsPanel } from "./DocumentsPanel";
import { PromptTemplates } from "./PromptTemplates";
import { AgentWorkbench } from "./AgentWorkbench";
import { PdfWorkbench } from "./PdfWorkbench";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

type AgentMode = {
  key: AgentClassHint;
  title: string;
  desc: string;
};

type Props = {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  sessions: SessionSummary[];
  sessionLoading: boolean;
  currentSessionId: string | null;
  busySessionId: string | null;
  agentClassHint: AgentClassHint;
  agentModes: AgentMode[];
  agentDistribution: Array<{ agent: string; count: number }>;
  pdfDocuments: IndexedFileSummary[];
  pdfNeedingReindex: IndexedFileSummary[];
  pdfTargetFile: string;
  documents: IndexedFileSummary[];
  docsLoading: boolean;
  uploading: boolean;
  uploadInfo: string;
  uploadProgress: number;
  uploadProgressText: string;
  uploadVisibility: "private" | "public";
  docDropActive: boolean;
  canUploadAndManageDocs: boolean;
  isAdmin: boolean;
  user: any;
  prompts: PromptTemplate[];
  promptsLoading: boolean;
  promptTitle: string;
  promptContent: string;
  editingPromptId: string | null;
  promptCheckInfo: string;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onToggleSidebarCollapsed: () => void;
  onCreateSession: () => Promise<void>;
  onLoadSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onSwitchAgentMode: (mode: AgentClassHint) => void;
  onDraftPdfQuestion: () => void;
  onPdfTargetFileChange: (filename: string) => void;
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

export function ChatSidebar({
  sidebarOpen,
  sidebarCollapsed,
  sessions,
  sessionLoading,
  currentSessionId,
  busySessionId,
  agentClassHint,
  agentModes,
  agentDistribution,
  pdfDocuments,
  pdfNeedingReindex,
  pdfTargetFile,
  documents,
  docsLoading,
  uploading,
  uploadInfo,
  uploadProgress,
  uploadProgressText,
  uploadVisibility,
  docDropActive,
  canUploadAndManageDocs,
  isAdmin,
  user,
  prompts,
  promptsLoading,
  promptTitle,
  promptContent,
  editingPromptId,
  promptCheckInfo,
  fileInputRef,
  onToggleSidebarCollapsed,
  onCreateSession,
  onLoadSession,
  onDeleteSession,
  onSwitchAgentMode,
  onDraftPdfQuestion,
  onPdfTargetFileChange,
  onRefreshDocuments,
  onUploadVisibilityChange,
  onMainUploadChange,
  onDocsDrop,
  onDocDropActiveChange,
  onReindexDocument,
  onDeleteDocument,
  onRefreshPrompts,
  onPromptTitleChange,
  onPromptContentChange,
  onCheckPrompt,
  onSavePrompt,
  onUsePrompt,
  onEditPrompt,
  onDeletePrompt,
}: Props) {
  const [toolsCollapsed, setToolsCollapsed] = useState({
    agents: false,
    pdf: false,
    docs: true,
    prompts: true,
  });
  const isDesktop = typeof window !== "undefined" ? window.innerWidth > 1080 : true;
  const showCompactRail = sidebarCollapsed && isDesktop;
  const allToolsCollapsed = Object.values(toolsCollapsed).every(Boolean);

  const toggleToolSection = (key: keyof typeof toolsCollapsed) => {
    setToolsCollapsed((current) => ({ ...current, [key]: !current[key] }));
  };

  const toggleAllTools = () => {
    setToolsCollapsed({
      agents: !allToolsCollapsed,
      pdf: !allToolsCollapsed,
      docs: !allToolsCollapsed,
      prompts: !allToolsCollapsed,
    });
  };

  const moduleStatus = {
    agents: agentClassHint ? "locked" : "auto",
    pdf: `${pdfDocuments.length} files`,
    docs: `${documents.length} docs`,
    prompts: `${prompts.length} saved`,
  };
  const indexedCount = documents.length;
  const pendingCount = pdfNeedingReindex.length;

  if (showCompactRail) {
    return (
      <aside className="sidebar sidebar-rail">
        <div className="sidebar-rail-header">
          <button type="button" className="sidebar-rail-brand" onClick={onToggleSidebarCollapsed} title="展开侧栏">
            R
          </button>
        </div>
        <div className="sidebar-rail-actions">
          <button type="button" className="sidebar-rail-btn" onClick={() => void onCreateSession()} title="新建会话">
            新建
          </button>
          <button type="button" className="sidebar-rail-btn" onClick={onToggleSidebarCollapsed} title="展开工具区">
            打开
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
      <div className="sidebar-shell">
        <div className="sidebar-header">
          <div className="sidebar-brand-block">
            <span className="sidebar-brand-kicker">Operations Deck</span>
            <div className="brand">Local RAG</div>
            <p className="muted">多智能体知识库与检索工作台</p>
          </div>
          <button type="button" className="sidebar-collapse-btn" onClick={onToggleSidebarCollapsed}>
            收起
          </button>
        </div>

        <div className="sidebar-history">
          <div className="sidebar-group-title">
            <span>SESSIONS</span>
          </div>
          <SessionList
            sessions={sessions}
            sessionLoading={sessionLoading}
            currentSessionId={currentSessionId}
            busySessionId={busySessionId}
            onCreateSession={onCreateSession}
            onLoadSession={onLoadSession}
            onDeleteSession={onDeleteSession}
          />
        </div>

        <div className="sidebar-tools">
          <div className="sidebar-group-title sidebar-group-title-with-action">
            <span>WORKBENCH</span>
            <button type="button" className="sidebar-group-action" onClick={toggleAllTools}>
              {allToolsCollapsed ? "全部展开" : "全部收起"}
            </button>
          </div>

          <section className="panel sidebar-module">
            <button type="button" className="sidebar-module-toggle" onClick={() => toggleToolSection("agents")}>
              <div className="sidebar-module-copy">
                <strong>AGENT WORKBENCH</strong>
                <small>自动路由与执行模式切换</small>
              </div>
              <div className="sidebar-module-meta">
                <em>{moduleStatus.agents}</em>
                <span>{toolsCollapsed.agents ? "展开" : "收起"}</span>
              </div>
            </button>
            {!toolsCollapsed.agents && (
              <div className="sidebar-module-body">
                <AgentWorkbench
                  agentClassHint={agentClassHint}
                  agentModes={agentModes}
                  agentDistribution={agentDistribution}
                  onSwitchAgentMode={onSwitchAgentMode}
                />
              </div>
            )}
          </section>

          <section className="panel sidebar-module">
            <button type="button" className="sidebar-module-toggle" onClick={() => toggleToolSection("pdf")}>
              <div className="sidebar-module-copy">
                <strong>PDF WORKBENCH</strong>
                <small>PDF 与图片问答、重建索引</small>
              </div>
              <div className="sidebar-module-meta">
                <em>{moduleStatus.pdf}</em>
                <span>{toolsCollapsed.pdf ? "展开" : "收起"}</span>
              </div>
            </button>
            {!toolsCollapsed.pdf && (
              <div className="sidebar-module-body">
                <PdfWorkbench
                  pdfDocuments={pdfDocuments}
                  pdfNeedingReindex={pdfNeedingReindex}
                  pdfTargetFile={pdfTargetFile}
                  onDraftPdfQuestion={onDraftPdfQuestion}
                  onPdfTargetFileChange={onPdfTargetFileChange}
                  onSwitchAgentMode={onSwitchAgentMode}
                />
              </div>
            )}
          </section>

          <section className="panel sidebar-module">
            <button type="button" className="sidebar-module-toggle" onClick={() => toggleToolSection("docs")}>
              <div className="sidebar-module-copy">
                <strong>KNOWLEDGE BASE</strong>
                <small>上传、刷新、重建与删除</small>
              </div>
              <div className="sidebar-module-meta">
                <em>{moduleStatus.docs}</em>
                <span>{toolsCollapsed.docs ? "展开" : "收起"}</span>
              </div>
            </button>
            {!toolsCollapsed.docs && (
              <div className="sidebar-module-body">
                <div className="sidebar-kb-metrics">
                  <div className="sidebar-kb-card">
                    <span>INDEXED</span>
                    <strong>{indexedCount}</strong>
                  </div>
                  <div className="sidebar-kb-card">
                    <span>PENDING</span>
                    <strong>{pendingCount}</strong>
                  </div>
                </div>
                <DocumentsPanel
                  documents={documents}
                  docsLoading={docsLoading}
                  uploading={uploading}
                  uploadInfo={uploadInfo}
                  uploadProgress={uploadProgress}
                  uploadProgressText={uploadProgressText}
                  uploadVisibility={uploadVisibility}
                  docDropActive={docDropActive}
                  canUploadAndManageDocs={canUploadAndManageDocs}
                  isAdmin={isAdmin}
                  user={user}
                  fileInputRef={fileInputRef}
                  onRefreshDocuments={onRefreshDocuments}
                  onUploadVisibilityChange={onUploadVisibilityChange}
                  onMainUploadChange={onMainUploadChange}
                  onDocsDrop={onDocsDrop}
                  onDocDropActiveChange={onDocDropActiveChange}
                  onReindexDocument={onReindexDocument}
                  onDeleteDocument={onDeleteDocument}
                />
              </div>
            )}
          </section>

          <section className="panel sidebar-module">
            <button type="button" className="sidebar-module-toggle" onClick={() => toggleToolSection("prompts")}>
              <div className="sidebar-module-copy">
                <strong>PROMPT LIBRARY</strong>
                <small>保存与复用常用 Prompt</small>
              </div>
              <div className="sidebar-module-meta">
                <em>{moduleStatus.prompts}</em>
                <span>{toolsCollapsed.prompts ? "展开" : "收起"}</span>
              </div>
            </button>
            {!toolsCollapsed.prompts && (
              <div className="sidebar-module-body">
                <PromptTemplates
                  prompts={prompts}
                  promptsLoading={promptsLoading}
                  promptTitle={promptTitle}
                  promptContent={promptContent}
                  editingPromptId={editingPromptId}
                  promptCheckInfo={promptCheckInfo}
                  onRefreshPrompts={onRefreshPrompts}
                  onPromptTitleChange={onPromptTitleChange}
                  onPromptContentChange={onPromptContentChange}
                  onCheckPrompt={onCheckPrompt}
                  onSavePrompt={onSavePrompt}
                  onUsePrompt={onUsePrompt}
                  onEditPrompt={onEditPrompt}
                  onDeletePrompt={onDeletePrompt}
                />
              </div>
            )}
          </section>
        </div>
      </div>
    </aside>
  );
}
