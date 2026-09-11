import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PromptDialog } from "@/components/PromptDialog";
import { SettingsDrawer } from "@/components/SettingsDrawer";
import { ToastStack } from "@/pages/chat/components/ToastStack";
import { SessionManagementModal } from "@/components/SessionManagementModal";
import { SectionToggleButton } from "@/pages/chat/components/SectionToggleButton";
import type { Toast } from "@/pages/chat/types";
import type { SessionMessage } from "@/types/api";

interface ConfirmDialogState {
  isOpen: boolean;
  options?: {
    title?: string;
    message?: string;
    confirmText?: string;
    cancelText?: string;
    isDanger?: boolean;
  } | null;
  handleConfirm: () => void;
  handleCancel: () => void;
}

interface PromptDialogState {
  isOpen: boolean;
  options?: {
    title?: string;
    message?: string;
    defaultValue?: string;
    placeholder?: string;
    confirmText?: string;
    cancelText?: string;
    multiline?: boolean;
    inputType?: "text" | "password";
  } | null;
  handleConfirm: (value: string) => void;
  handleCancel: () => void;
}

interface ChatDialogsAndDrawersProps {
  toasts: Toast[];
  onRemoveToast: (id: string) => void;
  sectionsHidden: boolean;
  toggleSections: () => void;
  settingsOpen: boolean;
  onCloseSettings: () => void;
  confirmDialog: ConfirmDialogState;
  promptDialog: PromptDialogState;
  sessionManagementOpen: boolean;
  onCloseSessionManagement: () => void;
  currentSessionId: string | null;
  messages: SessionMessage[];
  onSelectSession: (sessionId: string) => void;
}

export function ChatDialogsAndDrawers({
  toasts,
  onRemoveToast,
  sectionsHidden,
  toggleSections,
  settingsOpen,
  onCloseSettings,
  confirmDialog,
  promptDialog,
  sessionManagementOpen,
  onCloseSessionManagement,
  currentSessionId,
  messages,
  onSelectSession,
}: Readonly<ChatDialogsAndDrawersProps>) {
  return (
    <>
      <ToastStack toasts={toasts} onRemove={onRemoveToast} />
      <SectionToggleButton sectionsHidden={sectionsHidden} onToggle={toggleSections} />
      <SettingsDrawer isOpen={settingsOpen} onClose={onCloseSettings} />

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.options?.title || ""}
        message={confirmDialog.options?.message || ""}
        confirmText={confirmDialog.options?.confirmText}
        cancelText={confirmDialog.options?.cancelText}
        isDanger={confirmDialog.options?.isDanger}
        onConfirm={confirmDialog.handleConfirm}
        onCancel={confirmDialog.handleCancel}
      />

      <PromptDialog
        isOpen={promptDialog.isOpen}
        title={promptDialog.options?.title || ""}
        message={promptDialog.options?.message || ""}
        defaultValue={promptDialog.options?.defaultValue}
        placeholder={promptDialog.options?.placeholder}
        confirmText={promptDialog.options?.confirmText}
        cancelText={promptDialog.options?.cancelText}
        multiline={promptDialog.options?.multiline}
        inputType={promptDialog.options?.inputType}
        onConfirm={promptDialog.handleConfirm}
        onCancel={promptDialog.handleCancel}
      />

      {sessionManagementOpen && (
        <SessionManagementModal
          isOpen={sessionManagementOpen}
          onClose={onCloseSessionManagement}
          currentSessionId={currentSessionId}
          messages={messages}
          onSelectSession={onSelectSession}
        />
      )}
    </>
  );
}
