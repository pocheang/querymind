import { useEffect, useMemo, useRef, useState } from "react";
import type { SessionSummary } from "@/types/api";

type Props = {
  sessions: SessionSummary[];
  sessionLoading: boolean;
  currentSessionId: string | null;
  busySessionId: string | null;
  searchRequestKey?: number;
  onCreateSession: () => Promise<void>;
  onLoadSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
};

function formatSessionTime(value?: string) {
  if (!value) return "最近";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "最近";

  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SessionList({
  sessions,
  sessionLoading,
  currentSessionId,
  busySessionId,
  searchRequestKey = 0,
  onCreateSession,
  onLoadSession,
  onDeleteSession,
}: Props) {
  const [sessionQuery, setSessionQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  const normalizedQuery = sessionQuery.trim().toLowerCase();
  const filteredSessions = useMemo(() => {
    if (!normalizedQuery) return sessions;

    return sessions.filter((session) => {
      const title = session.title || "Untitled";
      return title.toLowerCase().includes(normalizedQuery);
    });
  }, [normalizedQuery, sessions]);

  useEffect(() => {
    if (searchRequestKey <= 0) return;
    setSessionQuery("");
    window.setTimeout(() => searchInputRef.current?.focus(), 0);
  }, [searchRequestKey]);

  return (
    <section className="sidebar-history-panel">
      <label className="session-search" aria-label="搜索会话">
        <span className="session-search-icon" aria-hidden="true" />
        <input
          ref={searchInputRef}
          type="search"
          value={sessionQuery}
          onChange={(event) => setSessionQuery(event.target.value)}
          placeholder="搜索会话"
        />
      </label>
      <button
        type="button"
        className="session-create-btn"
        onClick={() => void onCreateSession()}
        disabled={sessionLoading}
      >
        <span className="session-create-icon" aria-hidden="true">+</span>
        <span>新建会话</span>
        <small>{sessions.length || 0}</small>
      </button>
      {sessionLoading && <div className="skeleton-list" />}
      {!sessionLoading && sessions.length === 0 && <div className="muted">还没有会话</div>}
      {!sessionLoading && sessions.length > 0 && filteredSessions.length === 0 && (
        <div className="session-empty">没有匹配的会话</div>
      )}
      {!sessionLoading && filteredSessions.length > 0 && (
        <ul className="list session-list">
          {filteredSessions.map((s) => (
            <li key={s.session_id} className={`session-item ${s.session_id === currentSessionId ? "active" : ""}`}>
              <button
                type="button"
                className="list-main-btn session-main-btn"
                onClick={() => void onLoadSession(s.session_id)}
                disabled={busySessionId === s.session_id}
              >
                <span className="session-icon" aria-hidden="true">R</span>
                <span className="session-copy">
                  <span className="session-title">{s.title || "Untitled"}</span>
                  <small className="session-meta">{formatSessionTime(s.updated_at)}</small>
                </span>
                <small className="session-count">{s.message_count || 0}</small>
              </button>
              <button
                type="button"
                className="danger tiny-btn session-delete-btn"
                onClick={() => void onDeleteSession(s.session_id)}
                aria-label={`删除会话 ${s.title || "未命名会话"}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
