import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type React from "react";
import type { IndexedFileSummary } from "@/types/api";
import type { UserIdentity } from "@/types/auth";
import { DocumentItem } from "./DocumentItem";
import { UPLOAD_ACCEPT_ATTRIBUTE } from "@/lib/uploadFormats";

const PDF_FILE_RE = /\.(pdf|png|jpe?g|bmp|tiff?|webp)$/i;

type Props = {
  documents: IndexedFileSummary[];
  docsLoading: boolean;
  uploading: boolean;
  uploadInfo: string;
  uploadProgress: number;
  uploadProgressText: string;
  uploadVisibility: "private" | "public";
  docDropActive: boolean;
  canUploadAndManageDocs: boolean;
  isAdmin: boolean;
  user: UserIdentity | null;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onRefreshDocuments: () => Promise<void>;
  onUploadVisibilityChange: (visibility: "private" | "public") => void;
  onMainUploadChange: (evt: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  onDocsDrop: (evt: React.DragEvent<HTMLDivElement>) => Promise<void>;
  onDocDropActiveChange: (active: boolean) => void;
  onReindexDocument: (doc: IndexedFileSummary) => Promise<void>;
  onDeleteDocument: (doc: IndexedFileSummary, removeFile: boolean) => Promise<void>;
};

export function DocumentsPanel({
  documents,
  docsLoading,
  uploading,
  uploadInfo,
  uploadProgress,
  uploadProgressText,
  uploadVisibility,
  docDropActive,
  canUploadAndManageDocs,
  isAdmin,
  user,
  fileInputRef,
  onRefreshDocuments,
  onUploadVisibilityChange,
  onMainUploadChange,
  onDocsDrop,
  onDocDropActiveChange,
  onReindexDocument,
  onDeleteDocument,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const pdfDocuments = documents.filter((doc) => PDF_FILE_RE.test(doc.filename || ""));
  const nonPdfDocuments = documents.filter((doc) => !PDF_FILE_RE.test(doc.filename || ""));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          {t("components.workbench.documents")}
        </span>
        <Button variant="ghost" size="xs" onClick={() => void onRefreshDocuments()}>
          <RefreshCw className="size-3.5" aria-hidden="true" />
          {t("components.workbench.refresh")}
        </Button>
      </div>

      {canUploadAndManageDocs && (
        <div className="space-y-2 rounded-control border border-line bg-surface p-2.5">
          {isAdmin && (
            <select
              value={uploadVisibility}
              onChange={(event) => onUploadVisibilityChange((event.target.value as "private" | "public") || "private")}
              className="w-full rounded-control border border-brand-border bg-surface px-2.5 py-1.5 text-xs sm:text-sm text-ink focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
            >
              <option value="private">{t("components.workbench.private")}</option>
              <option value="public">{t("components.workbench.public")}</option>
            </select>
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={(event) => void onMainUploadChange(event)}
            accept={UPLOAD_ACCEPT_ATTRIBUTE}
            className="w-full text-xs text-ink/75 file:mr-2 file:rounded-control file:border-0 file:bg-brand-surface file:px-2.5 file:py-1 file:text-xs file:font-semibold file:text-brand-text"
          />
          <p className="text-xs text-ink/75">
            {uploading ? t("components.workbench.uploading") : t("components.workbench.uploadSupport")}
          </p>
          {uploadInfo && <p className="text-xs font-semibold text-brand-text">{uploadInfo}</p>}
          {(uploading || uploadProgress > 0) && (
            <div className="space-y-1">
              <div className="h-1.5 w-full overflow-hidden rounded-pill bg-brand-surface-hover">
                <div
                  className="h-full rounded-pill bg-[image:var(--brand-gradient)] transition-[width]"
                  style={{ width: `${Math.round(uploadProgress)}%` }}
                />
              </div>
              <div className="font-mono text-xs text-ink/75">
                {uploadProgressText ||
                  t("components.workbench.uploadProgress", { progress: Math.round(uploadProgress) })}
              </div>
            </div>
          )}
        </div>
      )}

      {canUploadAndManageDocs && (
        <div
          className={cn(
            "cursor-pointer rounded-control border-2 border-dashed p-3 text-center text-xs font-medium transition-colors",
            docDropActive
              ? "border-brand-accent bg-brand-surface-hover text-brand-text"
              : "border-brand-border bg-brand-surface/30 text-ink/75 hover:bg-brand-surface/60"
          )}
          onDragEnter={(event) => {
            event.preventDefault();
            event.stopPropagation();
            onDocDropActiveChange(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            event.stopPropagation();
            onDocDropActiveChange(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            event.stopPropagation();
            onDocDropActiveChange(false);
          }}
          onDrop={(event) => void onDocsDrop(event)}
        >
          {t("components.workbench.dropDocs")}
        </div>
      )}

      {docsLoading && (
        <div className="space-y-1.5">
          {[0, 1].map((row) => (
            <div key={row} className="h-12 animate-pulse rounded-control bg-brand-surface-hover" />
          ))}
        </div>
      )}
      {!docsLoading && documents.length === 0 && (
        <p className="py-3 text-center text-xs text-ink/75">{t("components.workbench.noIndexedDocuments")}</p>
      )}
      {!docsLoading && pdfDocuments.length > 0 && (
        <p className="pt-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">
          {t("components.workbench.pdfImageDocs", { count: pdfDocuments.length })}
        </p>
      )}
      {!docsLoading &&
        pdfDocuments.map((doc) => (
          <DocumentItem
            key={`${doc.filename}-${doc.source}`}
            doc={doc}
            canUploadAndManageDocs={canUploadAndManageDocs}
            isAdmin={isAdmin}
            currentUserId={user?.user_id}
            onReindexDocument={onReindexDocument}
            onDeleteDocument={onDeleteDocument}
          />
        ))}
      {!docsLoading && nonPdfDocuments.length > 0 && (
        <p className="pt-1 text-xs font-semibold uppercase tracking-wider text-ink-muted">
          {t("components.workbench.otherDocs", { count: nonPdfDocuments.length })}
        </p>
      )}
      {!docsLoading &&
        nonPdfDocuments.map((doc) => (
          <DocumentItem
            key={`${doc.filename}-${doc.source}`}
            doc={doc}
            canUploadAndManageDocs={canUploadAndManageDocs}
            isAdmin={isAdmin}
            currentUserId={user?.user_id}
            onReindexDocument={onReindexDocument}
            onDeleteDocument={onDeleteDocument}
          />
        ))}
    </div>
  );
}
