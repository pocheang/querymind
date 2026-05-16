import type React from "react";
import type { SessionMessage } from "@/types/api";
import { MessageCard } from "@/pages/chat/components/MessageCard";
import { WelcomeScreen } from "@/pages/chat/components/WelcomeScreen";

type Props = {
  messages: SessionMessage[];
  containerRef: React.MutableRefObject<HTMLDivElement | null>;
  documentsCount?: number;
  sessionsCount?: number;
  onEditMessage: (msg: SessionMessage) => Promise<void>;
  onRemoveMessage: (msg: SessionMessage) => Promise<void>;
  onCreateSession?: () => void;
  onNavigateToArchitecture?: () => void;
};

export function ChatMessages({
  messages,
  containerRef,
  documentsCount,
  sessionsCount,
  onEditMessage,
  onRemoveMessage,
  onCreateSession,
  onNavigateToArchitecture
}: Props) {
  return (
    <section className="chat-window panel" ref={containerRef} role="log" aria-live="polite" aria-label="对话消息">
      {messages.length === 0 && (
        <WelcomeScreen
          documentsCount={documentsCount}
          sessionsCount={sessionsCount}
          onCreateSession={onCreateSession}
          onNavigateToArchitecture={onNavigateToArchitecture}
        />
      )}
      {messages.map((message) => (
        <MessageCard
          key={message.message_id}
          message={message}
          onEditMessage={onEditMessage}
          onRemoveMessage={onRemoveMessage}
        />
      ))}
    </section>
  );
}
