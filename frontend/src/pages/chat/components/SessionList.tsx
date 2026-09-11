import { useEffect, useMemo, useRef, useState } from "react";
import type React from "react";
import { useTranslation } from "react-i18next";
import { Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { SessionSummary } from "@/types/api";
import { usePermissions } from "@/hooks/usePermissions";
import type { UserIdentity } from "@/types/auth";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SessionListItem } from "./SessionListItem";

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
  const { t } = useTranslation();
  const permissions = usePermissions(user);
  const [sessionQuery, setSessionQuery] = useState("");
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<{ id: string; title: string } | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const isSubmittingRenameRef = useRef<string | null>(null);

  const normalizedQuery = sessionQuery.trim().toLowerCase();
  const filteredSessions = useMemo(() => {
    if (!normalizedQuery) return sessions;

    return sessions.filter((session) => {
      const title = session.title || t("components.chat.untitled");
      return title.toLowerCase().includes(normalizedQuery);
    });
  }, [normalizedQuery, sessions, t]);

  const sortedSessions = useMemo(() => {
    return [...filteredSessions].sort((a, b) => {
      const aPinned = a.pinned || false;
      const bPinned = b.pinned || false;
      if (aPinned !== bPinned) return aPinned ? -1 : 1;

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

    const titleValue = value ?? renameValue;
    const trimmedTitle = titleValue.trim();

    if (!trimmedTitle) {
      setRenamingSessionId(null);
      setRenameValue("");
      isSubmittingRenameRef.current = null;
      return;
    }

    if (actionLoading === sessionId || isSubmittingRenameRef.current === sessionId) {
      return;
    }

    isSubmittingRenameRef.current = sessionId;
    setActionLoading(sessionId);

    try {
      await onRenameSession(sessionId, trimmedTitle);
      setRenamingSessionId(null);
      setRenameValue("");
    } catch (error) {
      console.error("Failed to rename session:", error);
    } finally {
      isSubmittingRenameRef.current = null;
      setActionLoading(null);
    }
  };

  const handleRenameKeyDown = (sessionId: string, event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
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
              className="w-full bg-transparent text-xs sm:text-sm text-ink placeholder:text-ink-faint focus-visible:outline-none"
            />
          </label>

          <Button
            variant="soft"
            className="group w-full justify-start text-xs sm:text-sm font-semibold"
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
            <p className="px-2 py-6 text-center text-xs text-ink/75">{t("components.chat.noSessions")}</p>
          )}

          {!sessionLoading && sessions.length > 0 && filteredSessions.length === 0 && (
            <div className="space-y-2 px-2 py-6 text-center">
              <Search className="mx-auto size-5 text-ink-faint" aria-hidden="true" />
              <p className="text-xs font-medium text-ink/75">{t("components.chat.noSessionMatches")}</p>
            </div>
          )}

          {!sessionLoading && sortedSessions.length > 0 && (
            <ul className="space-y-1">
              {sortedSessions.map((session) => (
                <SessionListItem
                  key={session.session_id}
                  session={session}
                  isActive={session.session_id === currentSessionId}
                  isRenaming={renamingSessionId === session.session_id}
                  isLoading={actionLoading === session.session_id}
                  isBusy={busySessionId === session.session_id}
                  renameValue={renameValue}
                  renameInputRef={renameInputRef}
                  canDeleteSession={permissions.canDeleteSession}
                  canRename={Boolean(onRenameSession)}
                  canPin={Boolean(onPinSession)}
                  onLoadSession={onLoadSession}
                  onRenameValueChange={setRenameValue}
                  onRenameBlur={handleRenameBlur}
                  onRenameKeyDown={handleRenameKeyDown}
                  onRenameStart={handleRenameStart}
                  onPinToggle={handlePinToggle}
                  onDeleteStart={handleDeleteStart}
                />
              ))}
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
