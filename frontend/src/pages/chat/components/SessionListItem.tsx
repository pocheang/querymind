import type React from "react";
import { useTranslation } from "react-i18next";
import { Pencil, Pin, PinOff, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { SessionSummary } from "@/types/api";

function formatSessionTime(value: string | undefined, fallback: string, locale: string) {
  if (!value) return fallback;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;

  return date.toLocaleTimeString(locale === "zh" ? "zh-CN" : "en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface SessionListItemProps {
  session: SessionSummary;
  isActive: boolean;
  isRenaming: boolean;
  isLoading: boolean;
  isBusy: boolean;
  renameValue: string;
  renameInputRef: React.RefObject<HTMLInputElement>;
  canDeleteSession: boolean;
  canRename: boolean;
  canPin: boolean;
  onLoadSession: (sessionId: string) => Promise<void>;
  onRenameValueChange: (value: string) => void;
  onRenameBlur: (sessionId: string) => void;
  onRenameKeyDown: (sessionId: string, event: React.KeyboardEvent<HTMLInputElement>) => void;
  onRenameStart: (session: SessionSummary, event: React.MouseEvent) => void;
  onPinToggle: (session: SessionSummary, event: React.MouseEvent) => void;
  onDeleteStart: (session: SessionSummary, event: React.MouseEvent) => void;
}

export function SessionListItem({
  session,
  isActive,
  isRenaming,
  isLoading,
  isBusy,
  renameValue,
  renameInputRef,
  canDeleteSession,
  canRename,
  canPin,
  onLoadSession,
  onRenameValueChange,
  onRenameBlur,
  onRenameKeyDown,
  onRenameStart,
  onPinToggle,
  onDeleteStart,
}: Readonly<SessionListItemProps>) {
  const { t, i18n } = useTranslation();
  const title = session.title || t("components.chat.untitled");

  return (
    <li
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
          className="w-full rounded-control border border-brand-accent bg-surface px-2 py-1 text-xs sm:text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
          value={renameValue}
          onChange={(e) => onRenameValueChange(e.target.value)}
          onBlur={() => onRenameBlur(session.session_id)}
          onKeyDown={(e) => onRenameKeyDown(session.session_id, e)}
          onClick={(e) => e.stopPropagation()}
          disabled={isLoading}
        />
      ) : (
        <>
          <button
            type="button"
            className="flex min-w-0 flex-1 items-center gap-1.5 rounded-control text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
            onClick={() => void onLoadSession(session.session_id)}
            disabled={isBusy || isLoading}
          >
            {session.pinned && (
              <Pin
                className="size-3.5 shrink-0 text-brand-accent"
                aria-label={t("components.chat.pinSession")}
              />
            )}
            <span className="min-w-0 flex-1">
              <span
                className={cn(
                  "block truncate text-xs sm:text-sm",
                  isActive ? "font-bold text-brand-text-strong" : "font-medium text-ink"
                )}
              >
                {title}
              </span>
              <span className="mt-0.5 flex items-center gap-1.5 font-mono text-xs text-ink-muted">
                <span>
                  {formatSessionTime(session.updated_at, t("components.chat.recent"), i18n.language)}
                </span>
                <span>{session.message_count || 0}</span>
              </span>
            </span>
          </button>

          <div
            className={cn(
              "flex shrink-0 items-center gap-0.5 transition-opacity focus-within:opacity-100",
              isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
            )}
          >
            {canRename && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={(event) => onRenameStart(session, event)}
                disabled={isLoading}
                title={t("components.chat.renameSession")}
              >
                <Pencil aria-hidden="true" />
                <span className="sr-only">{t("components.chat.renameSession")}</span>
              </Button>
            )}
            {canPin && (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={(event) => void onPinToggle(session, event)}
                disabled={isLoading}
                title={session.pinned ? t("components.chat.unpinSession") : t("components.chat.pinSession")}
              >
                {session.pinned ? <PinOff aria-hidden="true" /> : <Pin aria-hidden="true" />}
                <span className="sr-only">
                  {session.pinned ? t("components.chat.unpinSession") : t("components.chat.pinSession")}
                </span>
              </Button>
            )}
            {canDeleteSession && (
              <Button
                variant="destructive-ghost"
                size="icon-sm"
                onClick={(event) => onDeleteStart(session, event)}
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
}
