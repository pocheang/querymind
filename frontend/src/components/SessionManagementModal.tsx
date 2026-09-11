import { useState } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";

import { SessionSearch, SessionMetadataEditor, SessionExportImport } from "@/components/SessionManagement";
import type { SessionMessage } from "@/types/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type Tab = "search" | "metadata" | "exportImport";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  currentSessionId: string | null;
  messages: SessionMessage[];
  onSelectSession: (sessionId: string) => void;
};

/**
 * Advanced session management: tag/category search across sessions, metadata
 * editing for the current session, and export/import.
 *
 * Deliberately the same right-hand drawer shape as `SettingsDrawer` -- the app has
 * one established modal form and this is it, rather than a second one.
 */
export function SessionManagementModal({
  isOpen,
  onClose,
  currentSessionId,
  messages,
  onSelectSession,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("search");

  if (!isOpen) return null;

  const handleSelectSession = (sessionId: string) => {
    onSelectSession(sessionId);
    onClose();
  };

  const tabs: Array<{ key: Tab; label: string; disabled?: boolean; title?: string }> = [
    { key: "search", label: t("sessionManagement.searchSessions") },
    {
      key: "metadata",
      label: t("sessionManagement.editMetadata"),
      disabled: !currentSessionId,
      title: currentSessionId ? undefined : t("sessionManagement.noSessionToExport"),
    },
    {
      key: "exportImport",
      label: `${t("sessionManagement.exportSession")} / ${t("sessionManagement.importSession")}`,
    },
  ];

  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 bg-stone-900/40 backdrop-blur-sm"
        onClick={onClose}
        aria-label={t("common.close")}
      />
      <dialog
        open
        className="glass-panel fixed inset-y-0 right-0 z-50 m-0 flex max-h-none w-full max-w-lg flex-col border-y-0 border-r-0 bg-transparent p-0 shadow-elev-3 animate-in slide-in-from-right duration-300"
        aria-modal="true"
        aria-labelledby="session-management-title"
      >
        <header className="flex shrink-0 items-center justify-between gap-2 border-b border-line-subtle p-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <span
              className="flex size-9 shrink-0 items-center justify-center rounded-card bg-[image:var(--brand-gradient)] font-mono text-xs font-bold text-white shadow-elev-1"
              aria-hidden="true"
            >
              SM
            </span>
            <h2 id="session-management-title" className="truncate text-base font-bold text-ink">
              {t("sessionManagement.searchSessions")}
            </h2>
          </div>
          <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label={t("common.close")}>
            <X aria-hidden="true" />
          </Button>
        </header>

        <div className="shrink-0 px-4 pt-3">
          <div
            role="tablist"
            className="flex items-center gap-0.5 rounded-control border border-line bg-surface-muted p-1"
          >
            {tabs.map(({ key, label, disabled, title }) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={tab === key}
                disabled={disabled}
                title={title}
                onClick={() => setTab(key)}
                className={cn(
                  "flex-1 rounded-control px-2.5 py-1.5 text-xs sm:text-sm font-semibold transition-all",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  tab === key
                    ? "bg-surface font-bold text-brand-text-strong shadow-elev-1"
                    : "text-ink-muted hover:text-brand-text"
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {tab === "search" && <SessionSearch onSelectSession={handleSelectSession} />}
          {tab === "metadata" && currentSessionId && (
            <SessionMetadataEditor sessionId={currentSessionId} messages={messages} />
          )}
          {tab === "exportImport" && (
            <SessionExportImport sessionId={currentSessionId || undefined} onImportSuccess={() => onClose()} />
          )}
        </div>
      </dialog>
    </>
  );
}
