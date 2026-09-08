import { useEffect, useMemo, useRef, useState } from "react";
import type React from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Pin, PinOff, Plus, Search, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { SessionSummary } from "@/types/api";
import { usePermissions } from "@/hooks/usePermissions";
import type { UserIdentity } from "@/types/auth";
import { ConfirmDialog } from "@/components/ConfirmDialog";

type Props = {
  sessions: SessionSummary[];
  sessionLoading: boolean;
  currentSessionId: string | null;
  busySessionId: string | null;
  isCreatingSession: boolean;
  searchRequestKey?: number;
  user: UserIdentity | null;
  onCreateSession: () => Promise<void>;
  onLoadSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
  onRenameSession?: (sessionId: string, newTitle: string) => Promise<void>;
  onPinSession?: (sessionId: string, pinned: boolean) => Promise<void>;
};

function formatSessionTime(value: string | undefined, fallback: string, locale: string) {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;

  return date.toLocaleTimeString(locale === "zh" ? "zh-CN" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SessionList({
  sessions,
  sessionLoading,
  currentSessionId,
  busySessionId,
  isCreatingSession,
  searchRequestKey = 0,
  user,
  onCreateSession,
  onLoadSession,
  onDeleteSession,
  onRenameSession,
  onPinSession,
}: Readonly<Props>) {
  const { t, i18n } = useTranslation();
  const permissions = usePermissions(user);
  const [sessionQuery, setSessionQuery] = useState("");
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<{ id: string; title: string } | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const isSubmittingRenameRef = useRef<string | null>(null); // Track which session is submitting

  const normalizedQuery = sessionQuery.trim().toLowerCase();
  const filteredSessions = useMemo(() => {
    if (!normalizedQuery) return sessions;

    return sessions.filter((session) => {
      const title = session.title || t("components.chat.untitled");
      return title.toLowerCase().includes(normalizedQuery);
    });
  }, [normalizedQuery, sessions, t]);

  // Sort sessions: pinned first, then by updated_at
  const sortedSessions = useMemo(() => {
    return [...filteredSessions].sort((a, b) => {
      // Pinned sessions first
      const aPinned = a.pinned || false;
      const bPinned = b.pinned || false;
      if (aPinned !== bPinned) return aPinned ? -1 : 1;

      // Then by updated_at (most recent first)
      const aTime = new Date(a.updated_at || 0).getTime();
      const bTime = new Date(b.updated_at || 0).getTime();
      return bTime - aTime;
    });
  }, [filteredSessions]);

  useEffect(() => {
    if (searchRequestKey <= 0) return;
    setSessionQuery("");
    window.setTimeout(() => searchInputRef.current?.focus(), 0);
  }, [searchRequestKey]);

  useEffect(() => {
    if (renamingSessionId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingSessionId]);

  const handleRenameStart = (session: SessionSummary, event: React.MouseEvent) => {
    event.stopPropagation();
    setRenamingSessionId(session.session_id);
    setRenameValue(session.title || "");
    isSubmittingRenameRef.current = null;
  };

  const handleRenameSubmit = async (sessionId: string, value?: string) => {
    if (!onRenameSession) return;

    // Use provided value (from Enter key with direct DOM read) or fallback to state
    const titleValue = value !== undefined ? value : renameValue;
    const trimmedTitle = titleValue.trim();

    // Exit early if empty
    if (!trimmedTitle) {
      setRenamingSessionId(null);
      setRenameValue("");
      isSubmittingRenameRef.current = null;
      return;
    }

    // Prevent double submission - check both state and ref
    if (actionLoading === sessionId || isSubmittingRenameRef.current === sessionId) {
      return;
    }

    // Mark as submitting
    isSubmittingRenameRef.current = sessionId;
    setActionLoading(sessionId);

    try {
      await onRenameSession(sessionId, trimmedTitle);

      // Success - exit edit mode
      setRenamingSessionId(null);
      setRenameValue("");
    } catch (error) {
      // Error handled by parent - keep edit mode open for retry
      console.error("Failed to rename session:", error);
    } finally {
      // Always cleanup
      isSubmittingRenameRef.current = null;
      setActionLoading(null);
    }
  };

  const handleRenameKeyDown = (sessionId: string, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      // Read value directly from DOM to get the absolute latest value
      // bypassing React's asynchronous state updates
      const currentValue = event.currentTarget.value;
      void handleRenameSubmit(sessionId, currentValue);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setRenamingSessionId(null);
      setRenameValue("");
      isSubmittingRenameRef.current = null;
    }
  };

  const handleRenameBlur = (sessionId: string) => {
    // Only submit if not already submitting (prevents duplicate submissions)
    if (actionLoading !== sessionId && isSubmittingRenameRef.current !== sessionId) {
      void handleRenameSubmit(sessionId);
    }
  };

  const handlePinToggle = async (session: SessionSummary, event: React.MouseEvent) => {
    event.stopPropagation();

    if (!onPinSession) return;

    const newPinned = !session.pinned;
    setActionLoading(session.session_id);
    try {
      await onPinSession(session.session_id, newPinned);
    } catch {
      // `pinSession` notifies through `handleApiError` and re-throws; this
      // catch exists only to put the row's spinner back. Optional binding, so
      // the syntax says the value is deliberately unused.
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteStart = (session: SessionSummary, event: React.MouseEvent) => {
    event.stopPropagation();
    setSessionToDelete({
      id: session.session_id,
      title: session.title || t("components.chat.untitled"),
    });
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!sessionToDelete) return;

    setDeleteConfirmOpen(false);
    setActionLoading(sessionToDelete.id);
    try {
      await onDeleteSession(sessionToDelete.id);
    } catch {
      // Same as the pin handler: `deleteSession` has already reported it.
    } finally {
      setActionLoading(null);
      setSessionToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
    setSessionToDelete(null);
  };

  return (
    <>
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="shrink-0 space-y-2 px-3 py-2">
          {/* Search capsule: the wrapper carries the focus ring so the input
              itself stays chrome-free. */}
          <label
            className="field-shell flex items-center gap-1.5 rounded-control border border-line bg-surface px-2.5 py-1.5 shadow-elev-1 transition-all focus-within:border-brand-accent focus-within:ring-2 focus-within:ring-[var(--brand-ring)]"
            aria-label={t("components.chat.searchSessions")}
          >
            <Search className="size-3.5 shrink-0 text-ink-faint" aria-hidden="true" />
            <input
              ref={searchInputRef}
              type="search"
              value={sessionQuery}
              onChange={(event) => setSessionQuery(event.target.value)}
              placeholder={t("components.chat.searchSessions")}
              className="w-full bg-transparent text-xs text-ink placeholder:text-ink-faint focus-visible:outline-none"
            />
          </label>

          <Button
            variant="soft"
            className="group w-full justify-start"
            onClick={() => void onCreateSession()}
            disabled={sessionLoading || isCreatingSession}
          >
            <Plus
              className="size-3.5 text-brand-accent transition-transform group-hover:rotate-90"
              strokeWidth={2.5}
              aria-hidden="true"
            />
            <span>{t("components.chat.newSession")}</span>
          </Button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
          {sessionLoading && (
            <div className="space-y-1.5 px-1">
              {[0, 1, 2].map((row) => (
                <div key={row} className="h-11 animate-pulse rounded-card bg-brand-surface-hover" />
              ))}
            </div>
          )}

          {!sessionLoading && sessions.length === 0 && (
            <p className="px-2 py-6 text-center text-[11px] text-ink-muted">{t("components.chat.noSessions")}</p>
          )}

          {!sessionLoading && sessions.length > 0 && filteredSessions.length === 0 && (
            <div className="space-y-2 px-2 py-6 text-center">
              <Search className="mx-auto size-5 text-ink-faint" aria-hidden="true" />
              <p className="text-[11px] font-medium text-ink-muted">{t("components.chat.noSessionMatches")}</p>
            </div>
          )}

          {!sessionLoading && sortedSessions.length > 0 && (
            <ul className="space-y-1">
              {sortedSessions.map((session) => {
                const title = session.title || t("components.chat.untitled");
                const isRenaming = renamingSessionId === session.session_id;
                const isLoading = actionLoading === session.session_id;
                const isActive = session.session_id === currentSessionId;

                return (
                  <li
                    key={session.session_id}
                    className={cn(
                      "group flex items-center gap-1 rounded-card border p-2 transition-all",
                      isActive
                        ? "border-brand-border-strong bg-brand-surface shadow-elev-1"
                        : "border-transparent bg-surface/60 hover:border-brand-border hover:bg-brand-surface/60"
                    )}
                  >
                    {isRenaming ? (
                      <input
                        ref={renameInputRef}
                        type="text"
                        className="w-full rounded-control border border-brand-accent bg-surface px-1.5 py-0.5 text-xs text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => handleRenameBlur(session.session_id)}
                        onKeyDown={(e) => handleRenameKeyDown(session.session_id, e)}
                        onClick={(e) => e.stopPropagation()}
                        disabled={isLoading}
                      />
                    ) : (
                      <>
                        <button
                          type="button"
                          className="flex min-w-0 flex-1 items-center gap-1.5 rounded-control text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
                          onClick={() => void onLoadSession(session.session_id)}
                          disabled={busySessionId === session.session_id || isLoading}
                        >
                          {session.pinned && (
                            <Pin
                              className="size-3 shrink-0 text-brand-accent"
                              aria-label={t("components.chat.pinSession")}
                            />
                          )}
                          <span className="min-w-0 flex-1">
                            <span
                              className={cn(
                                "block truncate text-xs",
                                isActive ? "font-bold text-brand-text-strong" : "font-medium text-ink"
                              )}
                            >
                              {title}
                            </span>
                            <span className="mt-0.5 flex items-center gap-1.5 font-mono text-[10px] text-ink-muted">
                              <span>
                                {formatSessionTime(session.updated_at, t("components.chat.recent"), i18n.language)}
                              </span>
                              <span>{session.message_count || 0}</span>
                            </span>
                          </span>
                        </button>

                        {/* Revealed on hover, permanently visible on the active
                            row -- the pattern the design uses for every list. */}
                        <div
                          className={cn(
                            "flex shrink-0 items-center gap-0.5 transition-opacity focus-within:opacity-100",
                            isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                          )}
                        >
                          {onRenameSession && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={(event) => handleRenameStart(session, event)}
                              disabled={isLoading}
                              title={t("components.chat.renameSession")}
                            >
                              <Pencil aria-hidden="true" />
                              <span className="sr-only">{t("components.chat.renameSession")}</span>
                            </Button>
                          )}
                          {onPinSession && (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={(event) => void handlePinToggle(session, event)}
                              disabled={isLoading}
                              title={
                                session.pinned ? t("components.chat.unpinSession") : t("components.chat.pinSession")
                              }
                            >
                              {session.pinned ? <PinOff aria-hidden="true" /> : <Pin aria-hidden="true" />}
                              <span className="sr-only">
                                {session.pinned ? t("components.chat.unpinSession") : t("components.chat.pinSession")}
                              </span>
                            </Button>
                          )}
                          {permissions.canDeleteSession && (
                            <Button
                              variant="destructive-ghost"
                              size="icon-sm"
                              onClick={(event) => handleDeleteStart(session, event)}
                              disabled={isLoading}
                              title={t("components.chat.deleteSession")}
                            >
                              <Trash2 aria-hidden="true" />
                              <span className="sr-only">{t("components.chat.deleteSession")}</span>
                            </Button>
                          )}
                        </div>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={deleteConfirmOpen}
        title={t("components.chat.deleteSessionTitle")}
        message={t("components.chat.deleteSessionMessage", { title: sessionToDelete?.title || "" })}
        confirmText={t("common.delete")}
        cancelText={t("common.cancel")}
        isDanger={true}
        onConfirm={() => void handleDeleteConfirm()}
        onCancel={handleDeleteCancel}
      />
    </>
  );
}
