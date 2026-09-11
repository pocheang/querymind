import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronsLeft, KeyRound, LogOut, Settings2, User as UserIcon } from "lucide-react";
import type React from "react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { IndexedFileSummary } from "@/types/api";
import type { UserIdentity } from "@/types/auth";
import { SessionList } from "@/pages/chat/components/SessionList";
import { WorkbenchPanel } from "@/pages/chat/components/WorkbenchPanel";
import { useChatStore } from "@/stores/useChatStore";
import { useShallow } from "zustand/react/shallow";

import type { AgentMode, WorkbenchActionProps } from "@/pages/chat/types";

type Props = WorkbenchActionProps & {
  agentModes: AgentMode[];
  agentDistribution: Array<{ agent: string; count: number }>;
  pdfDocuments: IndexedFileSummary[];
  pdfNeedingReindex: IndexedFileSummary[];
  canUploadAndManageDocs: boolean;
  isAdmin: boolean;
  user: UserIdentity | null;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onToggleSidebarCollapsed: () => void;
  onCreateSession: () => Promise<void>;
  onLoadSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onRenameSession?: (sessionId: string, newTitle: string) => Promise<void>;
  onPinSession?: (sessionId: string, pinned: boolean) => Promise<void>;
  onLogout: () => Promise<void>;
};

export function ChatSidebar({
  agentModes,
  agentDistribution,
  pdfDocuments,
  pdfNeedingReindex,
  canUploadAndManageDocs,
  isAdmin,
  user,
  fileInputRef,
  onToggleSidebarCollapsed,
  onCreateSession,
  onLoadSession,
  onDeleteSession,
  onRenameSession,
  onPinSession,
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
  onLogout,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const {
    sidebarOpen,
    sidebarCollapsed,
    sessions,
    sessionLoading,
    currentSessionId,
    busySessionId,
    isCreatingSession,
    agentClassHint,
    pdfTargetFile,
    documents,
    docsLoading,
    uploading,
    uploadInfo,
    uploadProgress,
    uploadProgressText,
    uploadVisibility,
    docDropActive,
    prompts,
    promptsLoading,
    promptTitle,
    promptContent,
    editingPromptId,
    promptCheckInfo,
  } = useChatStore(
    useShallow((s) => ({
      sidebarOpen: s.sidebarOpen,
      sidebarCollapsed: s.sidebarCollapsed,
      sessions: s.sessions,
      sessionLoading: s.sessionLoading,
      currentSessionId: s.currentSessionId,
      busySessionId: s.busySessionId,
      isCreatingSession: s.isCreatingSession,
      agentClassHint: s.agentClassHint,
      pdfTargetFile: s.pdfTargetFile,
      documents: s.documents,
      docsLoading: s.docsLoading,
      uploading: s.uploading,
      uploadInfo: s.uploadInfo,
      uploadProgress: s.uploadProgress,
      uploadProgressText: s.uploadProgressText,
      uploadVisibility: s.uploadVisibility,
      docDropActive: s.docDropActive,
      prompts: s.prompts,
      promptsLoading: s.promptsLoading,
      promptTitle: s.promptTitle,
      promptContent: s.promptContent,
      editingPromptId: s.editingPromptId,
      promptCheckInfo: s.promptCheckInfo,
    }))
  );
  return (
    /* `sidebar` and `open` are behavioural hooks kept for scripts/screenshots.mjs,
       which reads `classList.contains("open")` rather than a visibility check --
       a panel translated off-canvas still reports as visible. Everything
       visual is Tailwind.

       Two mechanisms, one panel: below 1080px it is an off-canvas drawer
       driven by `sidebarOpen`; at or above it, an in-flow column that
       `sidebarCollapsed` slides out and un-gaps with a negative margin. */
    <aside
      className={cn(
        "sidebar glass-panel absolute inset-y-0 left-0 z-30 flex w-80 shrink-0 flex-col border-y-0 border-l-0 shadow-elev-3",
        "transition-[transform,margin-left,opacity] duration-300 ease-[var(--ease-standard)]",
        "sidebar:relative sidebar:shadow-none",
        sidebarOpen && "open",
        sidebarOpen ? "translate-x-0" : "-translate-x-full",
        sidebarCollapsed
          ? "sidebar:pointer-events-none sidebar:-ml-80 sidebar:-translate-x-full sidebar:opacity-0"
          : "sidebar:translate-x-0 sidebar:opacity-100"
      )}
      aria-label={t("components.chat.sessions")}
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-line-subtle px-3 py-2.5">
          <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-ink">
            {t("components.chat.sessions")}
            <Badge variant="brand" size="xs" mono className="text-xs">
              {sessions.length}
            </Badge>
          </span>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onToggleSidebarCollapsed}
            title={t("components.chat.collapse")}
          >
            <ChevronsLeft aria-hidden="true" />
            <span className="sr-only">{t("components.chat.collapse")}</span>
          </Button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <SessionList
            sessions={sessions}
            sessionLoading={sessionLoading}
            currentSessionId={currentSessionId}
            busySessionId={busySessionId}
            isCreatingSession={isCreatingSession}
            user={user}
            onCreateSession={onCreateSession}
            onLoadSession={onLoadSession}
            onDeleteSession={onDeleteSession}
            onRenameSession={onRenameSession}
            onPinSession={onPinSession}
          />
        </div>

        <WorkbenchPanel
          agentClassHint={agentClassHint}
          agentModes={agentModes}
          agentDistribution={agentDistribution}
          pdfDocuments={pdfDocuments}
          pdfNeedingReindex={pdfNeedingReindex}
          pdfTargetFile={pdfTargetFile}
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
          prompts={prompts}
          promptsLoading={promptsLoading}
          promptTitle={promptTitle}
          promptContent={promptContent}
          editingPromptId={editingPromptId}
          promptCheckInfo={promptCheckInfo}
          fileInputRef={fileInputRef}
          onSwitchAgentMode={onSwitchAgentMode}
          onPdfTargetFileChange={onPdfTargetFileChange}
          onDraftQuestion={onDraftQuestion}
          onRefreshDocuments={onRefreshDocuments}
          onUploadVisibilityChange={onUploadVisibilityChange}
          onMainUploadChange={onMainUploadChange}
          onDocsDrop={onDocsDrop}
          onDocDropActiveChange={onDocDropActiveChange}
          onReindexDocument={onReindexDocument}
          onDeleteDocument={onDeleteDocument}
          onRefreshPrompts={onRefreshPrompts}
          onPromptTitleChange={onPromptTitleChange}
          onPromptContentChange={onPromptContentChange}
          onCheckPrompt={onCheckPrompt}
          onSavePrompt={onSavePrompt}
          onUsePrompt={onUsePrompt}
          onEditPrompt={onEditPrompt}
          onDeletePrompt={onDeletePrompt}
        />

        <div className="flex shrink-0 items-center justify-between gap-2 border-t border-line-subtle px-3 py-2.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="relative shrink-0">
              <span className="flex size-8 items-center justify-center rounded-control border border-brand-border bg-brand-surface text-xs font-bold text-brand-text">
                {user?.username?.charAt(0).toUpperCase() || "U"}
              </span>
              <span
                className="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-pill border-2 border-white bg-success"
                aria-hidden="true"
              />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-xs sm:text-sm font-semibold leading-tight text-ink">
                {user?.username || t("components.chat.userFallback")}
              </span>
              <Badge variant="brand" size="xs" mono className="mt-0.5 text-xs uppercase tracking-wider">
                {user?.role || "user"}
              </Badge>
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-0.5">
            <Button asChild variant="ghost" size="icon-sm" title={t("components.chat.profile")}>
              <Link to="/app/profile">
                <UserIcon aria-hidden="true" />
                <span className="sr-only">{t("components.chat.profile")}</span>
              </Link>
            </Button>
            <Button asChild variant="ghost" size="icon-sm" title={t("components.chat.password")}>
              <Link to="/app/change-password">
                <KeyRound aria-hidden="true" />
                <span className="sr-only">{t("components.chat.password")}</span>
              </Link>
            </Button>
            {isAdmin && (
              <Button asChild variant="ghost" size="icon-sm" title={t("components.chat.admin")}>
                <Link to="/app/admin">
                  <Settings2 aria-hidden="true" />
                  <span className="sr-only">{t("components.chat.admin")}</span>
                </Link>
              </Button>
            )}
            <Button
              variant="destructive-ghost"
              size="icon-sm"
              onClick={() => void onLogout()}
              title={t("components.chat.logout")}
            >
              <LogOut aria-hidden="true" />
              <span className="sr-only">{t("components.chat.logout")}</span>
            </Button>
          </div>
        </div>
      </div>
    </aside>
  );
}
