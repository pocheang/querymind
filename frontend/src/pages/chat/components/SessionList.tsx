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
  onRenameSession?: (sessionId: string, newTitle: string) => Promise<void>;
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
  onRenameSession,
}: Props) {
  const [sessionQuery, setSessionQuery] = useState("");
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
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

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpenMenuId(null);
      }
    }

    if (openMenuId) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [openMenuId]);

  const handleMenuToggle = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setOpenMenuId(openMenuId === sessionId ? null : sessionId);
  };

  const handleDelete = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setOpenMenuId(null);
    void onDeleteSession(sessionId);
  };

  const handleRename = (sessionId: string, currentTitle: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setOpenMenuId(null);

    const newTitle = window.prompt("重命名会话", currentTitle || "Untitled");
    if (newTitle !== null && newTitle.trim() !== "" && newTitle !== currentTitle) {
      void onRenameSession?.(sessionId, newTitle.trim());
    }
  };

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
                <span className="session-copy">
                  <span className="session-title">{s.title || "Untitled"}</span>
                  <small className="session-meta">{formatSessionTime(s.updated_at)}</small>
                </span>
                <small className="session-count">{s.message_count || 0}</small>
              </button>
              <div className="session-menu-wrapper">
                <button
                  type="button"
                  className="session-menu-btn"
                  onClick={(e) => handleMenuToggle(s.session_id, e)}
                  aria-label={`会话选项 ${s.title || "未命名会话"}`}
                >
                  ⋯
                </button>
                {openMenuId === s.session_id && (
                  <div ref={menuRef} className="session-dropdown-menu">
                    <button
                      type="button"
                      className="session-menu-item"
                      onClick={(e) => handleRename(s.session_id, s.title || "", e)}
                    >
                      <span className="menu-icon">✏️</span>
                      重命名
                    </button>
                    <button
                      type="button"
                      className="session-menu-item danger"
                      onClick={(e) => handleDelete(s.session_id, e)}
                    >
                      <span className="menu-icon">🗑️</span>
                      删除
                    </button>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
