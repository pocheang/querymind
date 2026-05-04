import type React from "react";
import type { SessionMessage } from "@/types/api";
import { MessageCard } from "@/pages/chat/components/MessageCard";

type Props = {
  messages: SessionMessage[];
  containerRef: React.MutableRefObject<HTMLDivElement | null>;
  onEditMessage: (msg: SessionMessage) => Promise<void>;
  onRemoveMessage: (msg: SessionMessage) => Promise<void>;
};

export function ChatMessages({ messages, containerRef, onEditMessage, onRemoveMessage }: Props) {
  return (
    <section className="chat-window panel" ref={containerRef} role="log" aria-live="polite" aria-label="对话消息">
      {messages.length === 0 && (
        <div className="empty-chat-state">
          <span className="empty-chat-label">Console Ready</span>
          <h3>开始一次有证据链的分析</h3>
          <p>
            你可以上传 PDF 或图片、指定 Agent 模式、选择检索策略，或直接询问知识库。回答会展示路由、检索来源、
            执行过程和引用片段。
          </p>
        </div>
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
