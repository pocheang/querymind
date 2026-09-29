import { useTranslation } from "react-i18next";
import { createApiErrorHandler } from "@/services/http/apiErrorHandler";
import type { Toast } from "@/pages/chat/types";
import { useChatStore } from "@/stores/useChatStore";
import { useSessionActions } from "./useSessionActions";
import { useDocumentActions } from "./useDocumentActions";
import { usePromptActions } from "./usePromptActions";
import { useMessageOperations } from "./useMessageOperations";
import { randomId } from "@/lib/randomId";

interface UseChatActionsParams {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  chatUploadInputRef: React.RefObject<HTMLInputElement | null>;
  onLogout: () => Promise<void>;
  closeSidebar: () => void;
  confirm: (opts: { message: string; title?: string; isDanger?: boolean }) => Promise<boolean>;
  promptInput: (opts: {
    message: string;
    title?: string;
    defaultValue?: string;
    multiline?: boolean;
  }) => Promise<string | null>;
}

export function useChatActions(params: UseChatActionsParams) {
  const { t } = useTranslation();
  // Store-backed state and its setters are read here rather than threaded
  // through ChatPage: the setters never change identity, and passing twenty of
  // them down by hand is what made this hook's signature the widest in the app.
  const currentSessionId = useChatStore((st) => st.currentSessionId);
  const messages = useChatStore((st) => st.messages);
  const uploadVisibility = useChatStore((st) => st.uploadVisibility);
  const {
    setToasts,
    setError,
    setCurrentSessionId,
    setMessages,
    setBusySessionId,
    setIsCreatingSession,
    setUploading,
    setUploadInfo,
    setUploadProgress,
    setUploadProgressText,
    setAgentClassHint,
    setEditingPromptId,
    setPromptTitle,
    setPromptContent,
    setPromptCheckInfo,
  } = useChatStore.getState();
  const { fileInputRef, chatUploadInputRef, onLogout, closeSidebar, confirm, promptInput } = params;

  const notify = (text: string, kind: Toast["kind"] = "info", ttl = 2400) => {
    const id = randomId();
    setToasts((prev) => [...prev, { id, text, kind }]);
    window.setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), ttl);
  };

  const handleApiError = createApiErrorHandler({
    onLogout,
    onError: (msg) => {
      setError(msg);
      notify(msg, "error");
    },
    sessionExpiredMessage: t("common.sessionExpired"),
  });

  // Session management actions
  const sessionActions = useSessionActions({
    setToasts,
    setError,
    setCurrentSessionId,
    setMessages,
    setBusySessionId,
    setIsCreatingSession,
    currentSessionId,
    messages,
    onLogout,
    closeSidebar,
    notify,
    handleApiError,
  });

  // Document management actions
  const documentActions = useDocumentActions({
    setUploading,
    setUploadInfo,
    setUploadProgress,
    setUploadProgressText,
    setAgentClassHint,
    setError,
    uploadVisibility,
    fileInputRef,
    chatUploadInputRef,
    notify,
    handleApiError,
    confirm,
  });

  // Prompt management actions
  const promptActions = usePromptActions({
    setEditingPromptId,
    setPromptTitle,
    setPromptContent,
    setPromptCheckInfo,
    setAgentClassHint,
    setError,
    notify,
    handleApiError,
    confirm,
  });

  // Message operations
  const messageOperations = useMessageOperations({
    currentSessionId,
    setMessages,
    notify,
    handleApiError,
    refreshSessions: sessionActions.refreshSessions,
    promptInput,
  });

  return {
    notify,
    handleApiError,
    ...sessionActions,
    ...documentActions,
    ...promptActions,
    ...messageOperations,
  };
}
