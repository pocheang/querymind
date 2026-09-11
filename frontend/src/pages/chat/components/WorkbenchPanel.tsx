import { useState } from "react";

import { Button } from "@/components/ui/button";
import { WorkbenchModule } from "@/pages/chat/components/WorkbenchModule";
import { useTranslation } from "react-i18next";
import type React from "react";
import type { IndexedFileSummary, PromptTemplate } from "@/types/api";
import type { UserIdentity } from "@/types/auth";
import { AgentWorkbench } from "@/pages/chat/components/AgentWorkbench";
import { DocumentsPanel } from "@/pages/chat/components/DocumentsPanel";
import { PdfWorkbench } from "@/pages/chat/components/PdfWorkbench";
import { PromptTemplates } from "@/pages/chat/components/PromptTemplates";

import type { AgentClassHint, AgentMode, WorkbenchActionProps } from "@/pages/chat/types";

type Props = WorkbenchActionProps & {
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
  user: unknown;
  prompts: PromptTemplate[];
  promptsLoading: boolean;
  promptTitle: string;
  promptContent: string;
  editingPromptId: string | null;
  promptCheckInfo: string;
  fileInputRef: React.RefObject<HTMLInputElement>;
};

export function WorkbenchPanel({
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
  onSwitchAgentMode,
  onPdfTargetFileChange,
  onDraftQuestion,
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
}: Readonly<Props>) {
  const { t } = useTranslation();
  const [toolsCollapsed, setToolsCollapsed] = useState({
    agents: false,
    pdf: false,
    docs: true,
    prompts: true,
  });

  const allToolsCollapsed = Object.values(toolsCollapsed).every(Boolean);
  const indexedCount = documents.length;
  const indexingCount = documents.filter((doc) =>
    ["pending", "indexing"].includes(String(doc.indexing_status || ""))
  ).length;
  const readyCount = documents.filter((doc) => String(doc.indexing_status || "ready") === "ready").length;
  const failedCount = documents.filter((doc) => String(doc.indexing_status || "") === "failed").length;
  const moduleStatus = {
    agents: agentClassHint ? t("components.workbench.locked") : t("components.workbench.auto"),
    pdf: t("components.workbench.files", { count: pdfDocuments.length }),
    docs: t("components.workbench.docs", { count: documents.length }),
    prompts: t("components.workbench.saved", { count: prompts.length }),
  };

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

  return (
    /* max-h keeps this from starving the session list above it: as a
       shrink-0 flex child with no bound, an expanded workbench took the whole
       column and collapsed the sessions to 5px. */
    <div className="flex max-h-[45%] shrink-0 flex-col gap-2 overflow-y-auto border-t border-line-subtle px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          {t("components.workbench.workbench")}
        </span>
        <Button variant="ghost" size="xs" onClick={toggleAllTools}>
          {allToolsCollapsed ? t("components.workbench.expandAll") : t("components.workbench.collapseAll")}
        </Button>
      </div>

      <WorkbenchModule
        title={t("components.workbench.agentWorkbench")}
        description={t("components.workbench.agentWorkbenchDesc")}
        status={moduleStatus.agents}
        statusVariant={agentClassHint ? "warning" : "success"}
        accent="brand"
        open={!toolsCollapsed.agents}
        onToggle={() => toggleToolSection("agents")}
      >
        <AgentWorkbench
          agentClassHint={agentClassHint}
          agentModes={agentModes}
          agentDistribution={agentDistribution}
          onSwitchAgentMode={onSwitchAgentMode}
        />
      </WorkbenchModule>

      <WorkbenchModule
        title={t("components.workbench.pdfWorkbench")}
        description={t("components.workbench.pdfWorkbenchDesc")}
        status={moduleStatus.pdf}
        statusVariant="info"
        accent="info"
        open={!toolsCollapsed.pdf}
        onToggle={() => toggleToolSection("pdf")}
      >
        <PdfWorkbench
          pdfDocuments={pdfDocuments}
          pdfNeedingReindex={pdfNeedingReindex}
          pdfTargetFile={pdfTargetFile}
          onPdfTargetFileChange={onPdfTargetFileChange}
          onSwitchAgentMode={onSwitchAgentMode}
          onDraftQuestion={onDraftQuestion}
        />
      </WorkbenchModule>

      <WorkbenchModule
        title={t("components.workbench.knowledgeBase")}
        description={t("components.workbench.knowledgeBaseDesc")}
        status={moduleStatus.docs}
        statusVariant="success"
        accent="success"
        open={!toolsCollapsed.docs}
        onToggle={() => toggleToolSection("docs")}
      >
        <div className="grid grid-cols-4 gap-1.5">
          <div className="rounded-control border border-line bg-surface p-2 text-center">
            <span className="block truncate text-xs font-semibold uppercase tracking-wider text-ink/75">
              {t("components.workbench.indexed")}
            </span>
            <strong className="block font-mono text-sm font-bold text-brand-text">{indexedCount}</strong>
          </div>
          <div className="rounded-control border border-line bg-surface p-2 text-center">
            <span className="block truncate text-xs font-semibold uppercase tracking-wider text-ink/75">
              {t("components.workbench.pending")}
            </span>
            <strong className="block font-mono text-sm font-bold text-brand-text">{indexingCount}</strong>
          </div>
          <div className="rounded-control border border-line bg-surface p-2 text-center">
            <span className="block truncate text-xs font-semibold uppercase tracking-wider text-ink/75">
              {t("components.workbench.ready", "Ready")}
            </span>
            <strong className="block font-mono text-sm font-bold text-brand-text">{readyCount}</strong>
          </div>
          <div className="rounded-control border border-line bg-surface p-2 text-center">
            <span className="block truncate text-xs font-semibold uppercase tracking-wider text-ink/75">
              {t("components.workbench.failed", "Failed")}
            </span>
            <strong className="block font-mono text-sm font-bold text-brand-text">{failedCount}</strong>
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
          user={user as UserIdentity | null}
          fileInputRef={fileInputRef}
          onRefreshDocuments={onRefreshDocuments}
          onUploadVisibilityChange={onUploadVisibilityChange}
          onMainUploadChange={onMainUploadChange}
          onDocsDrop={onDocsDrop}
          onDocDropActiveChange={onDocDropActiveChange}
          onReindexDocument={onReindexDocument}
          onDeleteDocument={onDeleteDocument}
        />
      </WorkbenchModule>

      <WorkbenchModule
        title={t("components.workbench.promptLibrary")}
        description={t("components.workbench.promptLibraryDesc")}
        status={moduleStatus.prompts}
        statusVariant="brand"
        accent="warning"
        open={!toolsCollapsed.prompts}
        onToggle={() => toggleToolSection("prompts")}
      >
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
      </WorkbenchModule>
    </div>
  );
}
