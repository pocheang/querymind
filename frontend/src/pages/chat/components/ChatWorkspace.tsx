import type React from "react";
import { ChatMessages } from "@/pages/chat/components/ChatMessages";
import { ChatComposer } from "@/pages/chat/components/ChatComposer";
import { ClarificationPrompt } from "@/pages/chat/components/ClarificationPrompt";
import { ChatRuntimePanels } from "@/pages/chat/components/ChatRuntimePanels";
import type { ClarificationResponse, PendingApproval, SessionMessage } from "@/types/api";

interface ChatWorkspaceProps {
  messages: SessionMessage[];
  chatScrollRef: React.RefObject<HTMLDivElement>;
  documentsCount: number;
  sessionsCount: number;
  onEditMessage: (msg: SessionMessage) => Promise<void>;
  onRemoveMessage: (msg: SessionMessage) => Promise<void>;
  onCreateSession: () => Promise<void>;
  sectionsHidden: boolean;
  toggleSections: () => void;
  executionId: string | null;
  pendingApproval: PendingApproval | null;
  onApproved: (token: string) => Promise<void>;
  onDismissApproval: () => void;
  onDraft: (text: string) => void;
  clarification: ClarificationResponse | null;
  onAnswerClarification: (fieldName: string, answer: string) => Promise<void>;
  onSkipClarification: () => Promise<void>;
  isClarifying: boolean;
  questionRef: React.RefObject<HTMLTextAreaElement>;
  chatUploadInputRef: React.RefObject<HTMLInputElement>;
  isSending: boolean;
  smartQuickPrompts: string[];
  onAsk: () => Promise<void>;
  onStop: () => void;
  onComposerDragEnter: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragOver: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragLeave: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDrop: (evt: React.DragEvent<HTMLElement>) => Promise<void>;
  onChatUploadChange: (evt: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
}

export function ChatWorkspace({
  messages,
  chatScrollRef,
  documentsCount,
  sessionsCount,
  onEditMessage,
  onRemoveMessage,
  onCreateSession,
  sectionsHidden,
  toggleSections,
  executionId,
  pendingApproval,
  onApproved,
  onDismissApproval,
  onDraft,
  clarification,
  onAnswerClarification,
  onSkipClarification,
  isClarifying,
  questionRef,
  chatUploadInputRef,
  isSending,
  smartQuickPrompts,
  onAsk,
  onStop,
  onComposerDragEnter,
  onComposerDragOver,
  onComposerDragLeave,
  onComposerDrop,
  onChatUploadChange,
}: Readonly<ChatWorkspaceProps>) {
  return (
    <main className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
      <ChatMessages
        messages={messages}
        containerRef={chatScrollRef}
        documentsCount={documentsCount}
        sessionsCount={sessionsCount}
        onEditMessage={onEditMessage}
        onRemoveMessage={onRemoveMessage}
        onCreateSession={onCreateSession}
        onNavigateToArchitecture={() => (window.location.href = "/app/architecture")}
      />

      {!sectionsHidden && (
        <ChatRuntimePanels
          executionId={executionId}
          pendingApproval={pendingApproval}
          onApproved={onApproved}
          onDismissApproval={onDismissApproval}
          onDraft={onDraft}
        />
      )}

      {clarification?.action === "NEED_CLARIFICATION" && clarification.clarification && (
        <ClarificationPrompt
          question={clarification.clarification}
          context={clarification.context}
          onAnswer={onAnswerClarification}
          onSkip={onSkipClarification}
          isSubmitting={isClarifying}
        />
      )}

      {!sectionsHidden && (
        <ChatComposer
          questionRef={questionRef}
          chatUploadInputRef={chatUploadInputRef}
          isSending={isSending}
          quickPrompts={smartQuickPrompts}
          onAsk={onAsk}
          onStop={onStop}
          onComposerDragEnter={onComposerDragEnter}
          onComposerDragOver={onComposerDragOver}
          onComposerDragLeave={onComposerDragLeave}
          onComposerDrop={onComposerDrop}
          onChatUploadChange={onChatUploadChange}
          onToggleSections={toggleSections}
        />
      )}
    </main>
  );
}
