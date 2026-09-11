import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AGENT_MODES, type AgentClassHint } from "@/pages/chat/constants";
import type { Props } from "@/pages/chat/types";
import type { PendingApproval } from "@/types/api";
import { useChatStore } from "@/stores/useChatStore";
import { AppShell } from "@/components/layout/AppShell";
import { cn } from "@/lib/utils";
import { useConfirmDialog } from "@/hooks/useConfirmDialog";
import { usePromptDialog } from "@/hooks/usePromptDialog";
import { ChatSidebar } from "@/pages/chat/components/ChatSidebar";
import { ChatWorkspace } from "@/pages/chat/components/ChatWorkspace";
import { ChatDialogsAndDrawers } from "@/pages/chat/components/ChatDialogsAndDrawers";
import { useChatActions } from "@/pages/chat/hooks/useChatActions";
import { useFileUpload } from "@/pages/chat/hooks/useFileUpload";
import { useMessageActions } from "@/pages/chat/hooks/useMessageActions";
import { useChatPageState } from "@/pages/chat/hooks/useChatPageState";
import { useDragHandlers } from "@/pages/chat/hooks/useDragHandlers";
import { useChatComputed } from "@/pages/chat/hooks/useChatComputed";
import { useChatHelpers } from "@/pages/chat/hooks/useChatHelpers";
import { useClarification } from "@/pages/chat/hooks/useClarification";
import { useSettingsPolling } from "@/pages/chat/hooks/useSettingsPolling";
import { useAutoRefresh } from "@/pages/chat/hooks/useAutoRefresh";
import { useAutoScroll } from "@/pages/chat/hooks/useAutoScroll";
import { generateSmartPrompts } from "@/pages/chat/utils/smartPrompts";
import type { UserIdentity } from "@/types/auth";
import { useSectionToggle } from "@/hooks/useSectionToggle";

export function ChatPage({ user, onLogout, onUserRefresh }: Readonly<Props>) {
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<{
    approval: PendingApproval;
    question: string;
  } | null>(null);
  const [sessionManagementOpen, setSessionManagementOpen] = useState(false);
  const permissionUser: UserIdentity | null = user;
  const { sectionsHidden, toggleSections } = useSectionToggle();

  const {
    sidebarOpen,
    setSidebarOpen,
    sidebarCollapsed,
    setSidebarCollapsed,
    sessions,
    setSessions,
    setSessionLoading,
    currentSessionId,
    setCurrentSessionId,
    messages,
    setMessages,
    setBusySessionId,
    setIsCreatingSession,
    setQuestion,
    isSending,
    setIsSending,
    setRunStatus,
    setAgentClassHint,
    pdfTargetFile,
    setPdfTargetFile,
    documents,
    setDocuments,
    setDocsLoading,
    setUploading,
    setUploadInfo,
    setUploadProgress,
    setUploadProgressText,
    uploadVisibility,
    setUploadVisibility,
    setDocDropActive,
    setComposerDropActive,
    setPrompts,
    setPromptsLoading,
    setPromptTitle,
    setPromptContent,
    setEditingPromptId,
    setPromptCheckInfo,
    toasts,
    setToasts,
    setError,
    settingsOpen,
    setSettingsOpen,
    fileInputRef,
    chatUploadInputRef,
    questionRef,
    chatScrollRef,
  } = useChatPageState();

  const [searchParams] = useSearchParams();
  useEffect(() => {
    const modeParam = searchParams.get("mode");
    if (modeParam && ["cybersecurity", "artificial_intelligence", "pdf_text", "general"].includes(modeParam)) {
      setAgentClassHint(modeParam as AgentClassHint);
    }
  }, [searchParams, setAgentClassHint]);

  const confirmDialog = useConfirmDialog();
  const promptDialog = usePromptDialog();

  const dragHandlers = useDragHandlers(setComposerDropActive);

  const computed = useChatComputed({ documents, user });
  const { isAdmin, canUploadAndManageDocs, pdfDocuments, pdfNeedingReindex, agentDistribution } = computed;

  const closeSidebar = () => {
    if (pdfDocuments.length > 0) setSidebarOpen(false);
  };

  const actions = useChatActions({
    setToasts,
    setError,
    setSessions,
    setSessionLoading,
    setCurrentSessionId,
    setMessages,
    setBusySessionId,
    setIsCreatingSession,
    setDocuments,
    setDocsLoading,
    setUploading,
    setUploadInfo,
    setUploadProgress,
    setUploadProgressText,
    setAgentClassHint,
    setPrompts,
    setPromptsLoading,
    setEditingPromptId,
    setPromptTitle,
    setPromptContent,
    setPromptCheckInfo,
    currentSessionId,
    sessions,
    messages,
    uploadVisibility,
    fileInputRef,
    chatUploadInputRef,
    onLogout,
    closeSidebar,
    confirm: confirmDialog.confirm,
    promptInput: promptDialog.promptInput,
  });

  const helpers = useChatHelpers({
    canUploadAndManageDocs,
    pdfDocuments,
    pdfTargetFile,
    setSidebarOpen,
    setAgentClassHint,
    setQuestion,
    questionRef,
    actions,
  });

  const fileUploadHandlers = useFileUpload({
    canUploadAndManageDocs,
    setDocDropActive,
    setComposerDropActive,
    notify: actions.notify,
    uploadFiles: actions.uploadFiles,
  });

  const messageActions = useMessageActions({
    currentSessionId,
    actions,
    setRunStatus,
    setMessages,
    setIsSending,
    setQuestion,
    onExecutionId: setExecutionId,
    onCreditsChanged: onUserRefresh,
    onPendingApproval: (approval, question) => setPendingApproval(approval ? { approval, question } : null),
  });

  const {
    clarification,
    isClarifying,
    handleClarificationAnswer,
    handleClarificationSkip,
    checkAndInitiateClarification,
  } = useClarification({
    currentSessionId,
    onClarificationComplete: async (originalQuestion) => {
      await messageActions.ask({
        question: originalQuestion,
        isSending: false,
      });
    },
    onNotify: actions.notify,
  });

  const handleSendWithClarification = async (questionText: string) => {
    if (!questionText.trim()) return;

    setIsSending(true);
    setRunStatus("preparing");
    let sessionId = currentSessionId;

    try {
      sessionId = sessionId || (await messageActions.ensureSessionForAsk());
      if (!sessionId) {
        setIsSending(false);
        setRunStatus("");
        return;
      }

      const needsClarification = await checkAndInitiateClarification(questionText, sessionId);
      if (needsClarification) {
        setIsSending(false);
        setRunStatus("");
        return;
      }

      await messageActions.ask({
        question: questionText,
        isSending: false,
        sessionId,
      });
    } catch (error: unknown) {
      const apiError = error as { response?: { status?: number }; status?: number };
      const status = apiError?.response?.status ?? apiError?.status;
      if (status === 403 || status === 401) {
        setIsSending(false);
        setRunStatus("");
        return;
      }

      await messageActions.ask({
        question: questionText,
        isSending: false,
        sessionId: sessionId || undefined,
      });
    }
  };

  useEffect(() => {
    if (!pdfDocuments.length) {
      setPdfTargetFile("");
      return;
    }
    if (!pdfTargetFile || !pdfDocuments.some((doc) => doc.filename === pdfTargetFile)) {
      setPdfTargetFile(pdfDocuments[0]?.filename || "");
    }
  }, [pdfDocuments, pdfTargetFile, setPdfTargetFile]);

  useEffect(() => {
    void (async () => {
      const rows = await actions.refreshSessions();
      await actions.refreshDocuments();
      await actions.refreshPrompts();
      if (rows.length > 0) await actions.loadSession(rows[0].session_id);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useAutoScroll({ ref: chatScrollRef, messages });
  useAutoRefresh({
    refreshSessions: actions.refreshSessions,
    refreshDocuments: actions.refreshDocuments,
    refreshPrompts: actions.refreshPrompts,
  });
  useSettingsPolling({ onNotify: actions.notify });

  const handleSidebarToggle = () => {
    if (window.innerWidth <= 1080) {
      setSidebarOpen((value) => !value);
      return;
    }
    setSidebarCollapsed((value) => !value);
  };

  const { i18n } = useTranslation();
  const isZh = Boolean(i18n.language?.startsWith("zh"));

  const smartQuickPrompts = useMemo(() => {
    return generateSmartPrompts(messages, isZh);
  }, [messages, isZh]);

  return (
    <AppShell
      user={permissionUser}
      onLogout={onLogout}
      onOpenSettings={() => setSettingsOpen(true)}
      onOpenSessionManagement={() => setSessionManagementOpen(true)}
      onNewSession={() => void actions.createSession()}
    >
      <div
        className={cn(
          "page-shell relative flex min-h-0 flex-1 overflow-hidden",
          sidebarCollapsed && "sidebar-collapsed"
        )}
      >
        <ChatSidebar
          agentModes={AGENT_MODES}
          agentDistribution={agentDistribution}
          pdfDocuments={pdfDocuments}
          pdfNeedingReindex={pdfNeedingReindex}
          canUploadAndManageDocs={canUploadAndManageDocs}
          isAdmin={isAdmin}
          user={permissionUser}
          fileInputRef={fileInputRef}
          onToggleSidebarCollapsed={handleSidebarToggle}
          onCreateSession={async () => {
            await actions.createSession();
          }}
          onLoadSession={actions.loadSession}
          onDeleteSession={actions.deleteSession}
          onRenameSession={actions.renameSession}
          onPinSession={actions.pinSession}
          onSwitchAgentMode={helpers.switchAgentMode}
          onPdfTargetFileChange={setPdfTargetFile}
          onDraftQuestion={helpers.draftPdfQuestion}
          onRefreshDocuments={actions.refreshDocuments}
          onUploadVisibilityChange={setUploadVisibility}
          onMainUploadChange={fileUploadHandlers.onMainUploadChange}
          onDocsDrop={fileUploadHandlers.onDocsDrop}
          onDocDropActiveChange={setDocDropActive}
          onReindexDocument={helpers.reindexDocument}
          onDeleteDocument={helpers.deleteDocument}
          onRefreshPrompts={actions.refreshPrompts}
          onPromptTitleChange={setPromptTitle}
          onPromptContentChange={setPromptContent}
          onCheckPrompt={helpers.checkPrompt}
          onSavePrompt={helpers.savePrompt}
          onUsePrompt={(p) => {
            setQuestion(p.content || "");
            if (p.agent_class) setAgentClassHint((p.agent_class as AgentClassHint) || "");
          }}
          onEditPrompt={(p) => {
            setEditingPromptId(p.prompt_id);
            setPromptTitle(p.title || "");
            setPromptContent(p.content || "");
          }}
          onDeletePrompt={helpers.deletePrompt}
          onLogout={onLogout}
        />

        <div
          className={cn(
            "absolute inset-0 z-20 bg-stone-900/40 backdrop-blur-sm transition-opacity sidebar:hidden",
            sidebarOpen ? "opacity-100" : "pointer-events-none opacity-0"
          )}
          aria-hidden="true"
          onClick={() => setSidebarOpen(false)}
        />

        <ChatWorkspace
          messages={messages}
          chatScrollRef={chatScrollRef}
          documentsCount={documents.length}
          sessionsCount={sessions.length}
          onEditMessage={(msg) => messageActions.editMessage(msg)}
          onRemoveMessage={(msg) => messageActions.removeMessage(msg)}
          onCreateSession={async () => {
            await actions.createSession();
          }}
          sectionsHidden={sectionsHidden}
          toggleSections={toggleSections}
          executionId={executionId}
          pendingApproval={pendingApproval?.approval ?? null}
          onApproved={async (token) => {
            const question = pendingApproval?.question;
            setPendingApproval(null);
            if (!question) return;
            await messageActions.ask({
              question,
              isSending: false,
              sessionId: currentSessionId || undefined,
              approvalToken: token,
            });
          }}
          onDismissApproval={() => setPendingApproval(null)}
          onDraft={(text) => {
            if (!text) return;
            setMessages((prev) => {
              const index = prev.findIndex(
                (message) => message.message_id === "local-assistant-stream" && !message.content
              );
              if (index === -1) return prev;
              const next = [...prev];
              next[index] = { ...next[index], content: text };
              return next;
            });
          }}
          clarification={clarification}
          onAnswerClarification={handleClarificationAnswer}
          onSkipClarification={handleClarificationSkip}
          isClarifying={isClarifying}
          questionRef={questionRef}
          chatUploadInputRef={chatUploadInputRef}
          isSending={isSending || Boolean(clarification)}
          smartQuickPrompts={smartQuickPrompts}
          onAsk={async () => {
            if (clarification) return;
            await handleSendWithClarification(useChatStore.getState().question);
          }}
          onStop={() => messageActions.stopCurrentRun(isSending)}
          onComposerDragEnter={dragHandlers.onComposerDragEnter}
          onComposerDragOver={dragHandlers.onComposerDragOver}
          onComposerDragLeave={dragHandlers.onComposerDragLeave}
          onComposerDrop={fileUploadHandlers.onComposerDrop}
          onChatUploadChange={fileUploadHandlers.onChatUploadChange}
        />
      </div>

      <ChatDialogsAndDrawers
        toasts={toasts}
        onRemoveToast={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
        sectionsHidden={sectionsHidden}
        toggleSections={toggleSections}
        settingsOpen={settingsOpen}
        onCloseSettings={() => setSettingsOpen(false)}
        confirmDialog={confirmDialog}
        promptDialog={promptDialog}
        sessionManagementOpen={sessionManagementOpen}
        onCloseSessionManagement={() => setSessionManagementOpen(false)}
        currentSessionId={currentSessionId}
        messages={messages}
        onSelectSession={(sessionId) => void actions.loadSession(sessionId)}
      />
    </AppShell>
  );
}
