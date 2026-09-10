/**
 * SessionExportImport Component
 *
 * Allows users to export sessions to JSON/ZIP and import sessions from files.
 * Supports conflict resolution strategies and progress tracking.
 */

import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { sessionManagementApi, ExportFormat, ConflictStrategy, ImportResponse } from "../../services/sessionManagement";
import { activateOnKey } from "@/lib/a11y";
import { CheckCircle2, FileText, Loader2, UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

interface SessionExportImportProps {
  sessionId?: string; // For export
  onImportSuccess?: (result: ImportResponse) => void;
}

export const SessionExportImport: React.FC<SessionExportImportProps> = ({ sessionId, onImportSuccess }) => {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Export state
  const [exportFormat, setExportFormat] = useState<ExportFormat>("json");
  const [includeContext, setIncludeContext] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Import state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [conflictStrategy, setConflictStrategy] = useState<ConflictStrategy>("skip");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);

  // Error/success state
  const [error, setError] = useState<string | null>(null);

  // Export handler
  const handleExport = async () => {
    if (!sessionId) {
      setError(t("sessionManagement.noSessionToExport"));
      return;
    }

    setExporting(true);
    setError(null);

    try {
      const blob = await sessionManagementApi.exportSession(sessionId, {
        format: exportFormat,
        include_context: includeContext,
      });

      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `session_${sessionId}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      setError(t("sessionManagement.exportFailed"));
    } finally {
      setExporting(false);
    }
  };

  // File selection handler
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.name.endsWith(".json") && !file.name.endsWith(".zip")) {
        setError(t("sessionManagement.invalidFileType"));
        return;
      }
      setSelectedFile(file);
      setError(null);
      setImportResult(null);
    }
  };

  // Drag and drop handlers
  const openFilePicker = () => fileInputRef.current?.click();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.add("drag-over");
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove("drag-over");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");

    const file = e.dataTransfer.files[0];
    if (file) {
      if (!file.name.endsWith(".json") && !file.name.endsWith(".zip")) {
        setError(t("sessionManagement.invalidFileType"));
        return;
      }
      setSelectedFile(file);
      setError(null);
      setImportResult(null);
    }
  };

  // Import handler
  const handleImport = async () => {
    if (!selectedFile) {
      setError(t("sessionManagement.noFileSelected"));
      return;
    }

    setImporting(true);
    setError(null);
    setImportResult(null);

    try {
      const result = await sessionManagementApi.importSession(selectedFile, conflictStrategy);
      setImportResult(result);

      if (onImportSuccess) {
        onImportSuccess(result);
      }
    } catch (err: unknown) {
      console.error("Import failed:", err);
      const errorDetail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(errorDetail || t("sessionManagement.importFailed"));
    } finally {
      setImporting(false);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setImportResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const RADIO = "size-3.5 shrink-0 accent-[var(--brand)]";
  const ROW = "flex items-center gap-1.5 text-[11px] text-ink";

  return (
    <div className="space-y-4">
      {sessionId && (
        <section className="space-y-2">
          <h3 className="text-xs font-bold text-ink">{t("sessionManagement.exportSession")}</h3>

          <div className="space-y-1.5">
            <Label>{t("sessionManagement.exportFormat")}</Label>
            <div className="flex items-center gap-4">
              {(["json", "zip"] as const).map((format) => (
                <label key={format} className={ROW}>
                  <input
                    className={RADIO}
                    type="radio"
                    name="format"
                    value={format}
                    checked={exportFormat === format}
                    onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                    disabled={exporting}
                  />
                  <span className="uppercase">{format}</span>
                </label>
              ))}
            </div>
          </div>

          <label className={ROW}>
            <input
              className={RADIO}
              type="checkbox"
              checked={includeContext}
              onChange={(e) => setIncludeContext(e.target.checked)}
              disabled={exporting}
            />
            <span>{t("sessionManagement.includeContext")}</span>
          </label>

          <Button size="sm" onClick={handleExport} disabled={exporting}>
            {exporting && <Loader2 className="size-3 animate-spin" aria-hidden="true" />}
            {t("sessionManagement.export")}
          </Button>
        </section>
      )}

      <section className="space-y-2 border-t border-line-subtle pt-4">
        <h3 className="text-xs font-bold text-ink">{t("sessionManagement.importSession")}</h3>

        <div
          className="cursor-pointer rounded-card border-2 border-dashed border-brand-border bg-brand-surface/30 p-4 text-center transition-colors hover:bg-brand-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
          role="button"
          tabIndex={0}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={openFilePicker}
          onKeyDown={activateOnKey(openFilePicker)}
        >
          <input ref={fileInputRef} type="file" accept=".json,.zip" onChange={handleFileSelect} className="sr-only" />

          {selectedFile ? (
            <div className="flex items-center gap-2 text-left">
              <FileText className="size-5 shrink-0 text-brand-accent" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[11px] font-medium text-ink">{selectedFile.name}</p>
                <p className="font-mono text-[10px] text-ink-muted">{(selectedFile.size / 1024).toFixed(1)} KB</p>
              </div>
              <Button
                variant="destructive-ghost"
                size="icon-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearFile();
                }}
                aria-label={t("common.clear", "Clear")}
              >
                <X aria-hidden="true" />
              </Button>
            </div>
          ) : (
            <div className="space-y-1">
              <UploadCloud className="mx-auto size-6 text-brand-accent" strokeWidth={1.5} aria-hidden="true" />
              <p className="text-[11px] font-medium text-ink">{t("sessionManagement.dragDropFile")}</p>
              <p className="text-[10px] text-ink-muted">{t("sessionManagement.orClickToSelect")}</p>
              <p className="font-mono text-[10px] text-ink-faint">JSON or ZIP</p>
            </div>
          )}
        </div>

        {selectedFile && (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="conflict-strategy">{t("sessionManagement.conflictStrategy")}</Label>
              <select
                id="conflict-strategy"
                value={conflictStrategy}
                onChange={(e) => setConflictStrategy(e.target.value as ConflictStrategy)}
                disabled={importing}
                className="h-8 w-full rounded-control border border-brand-border bg-surface px-2 text-xs text-ink focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] disabled:opacity-60"
              >
                <option value="skip">{t("sessionManagement.strategies.skip")}</option>
                <option value="overwrite">{t("sessionManagement.strategies.overwrite")}</option>
                <option value="rename">{t("sessionManagement.strategies.rename")}</option>
              </select>
              <p className="text-[10px] text-ink-muted">{t(`sessionManagement.strategiesHelp.${conflictStrategy}`)}</p>
            </div>

            <Button size="sm" onClick={handleImport} disabled={importing}>
              {importing && <Loader2 className="size-3 animate-spin" aria-hidden="true" />}
              {t("sessionManagement.import")}
            </Button>
          </>
        )}

        {importResult && (
          <div className="space-y-1.5 rounded-card border border-success-border bg-success-surface p-2.5">
            <p className="flex items-center gap-1.5 text-[11px] font-semibold text-success">
              <CheckCircle2 className="size-3.5" aria-hidden="true" />
              {t("sessionManagement.importSuccessful")}
            </p>
            <dl className="space-y-0.5 text-[10px]">
              {[
                [t("sessionManagement.sessionId"), importResult.session_id],
                ...(importResult.conflict_occurred
                  ? [[t("sessionManagement.conflictResolution"), importResult.conflict_resolution] as const]
                  : []),
                [t("sessionManagement.messagesImported"), String(importResult.messages_imported)],
                [t("sessionManagement.metadataImported"), importResult.metadata_imported ? "yes" : "no"],
                [t("sessionManagement.contextImported"), importResult.context_imported ? "yes" : "no"],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-2">
                  <dt className="text-ink-muted">{label}:</dt>
                  <dd className="truncate font-mono text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </section>

      {error && (
        <p
          role="alert"
          className="rounded-control border border-danger-border bg-danger-surface px-2.5 py-1.5 text-[11px] text-danger"
        >
          {error}
        </p>
      )}
    </div>
  );
};
