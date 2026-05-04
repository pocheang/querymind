import type { IndexedFileSummary } from "@/types/api";
import { DocumentItem } from "./DocumentItem";

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
  user: any;
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
}: Props) {
  const pdfDocuments = documents.filter((doc) => PDF_FILE_RE.test(doc.filename || ""));
  const nonPdfDocuments = documents.filter((doc) => !PDF_FILE_RE.test(doc.filename || ""));

  return (
    <section className="panel">
      <div className="section-head">
        <strong>Documents</strong>
        <button type="button" className="secondary tiny-btn" onClick={() => void onRefreshDocuments()}>
          Refresh
        </button>
      </div>

      {canUploadAndManageDocs && (
        <div className="upload-box">
          {isAdmin && (
            <select
              value={uploadVisibility}
              onChange={(e) => onUploadVisibilityChange((e.target.value as "private" | "public") || "private")}
            >
              <option value="private">private</option>
              <option value="public">public</option>
            </select>
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={(evt) => void onMainUploadChange(evt)}
            accept=".md,.txt,.pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp"
          />
          <div className="muted">{uploading ? "Uploading..." : "Supports .md/.txt/.pdf/images"}</div>
          {uploadInfo && <div className="hint">{uploadInfo}</div>}
          {(uploading || uploadProgress > 0) && (
            <div className="progress-wrap">
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${Math.round(uploadProgress)}%` }} />
              </div>
              <div className="progress-text">{uploadProgressText || `Uploading ${Math.round(uploadProgress)}%`}</div>
            </div>
          )}
        </div>
      )}

      {canUploadAndManageDocs && (
        <div
          className={`dropzone ${docDropActive ? "dragover" : ""}`}
          onDragEnter={(evt) => {
            evt.preventDefault();
            evt.stopPropagation();
            onDocDropActiveChange(true);
          }}
          onDragOver={(evt) => {
            evt.preventDefault();
            evt.stopPropagation();
            onDocDropActiveChange(true);
          }}
          onDragLeave={(evt) => {
            evt.preventDefault();
            evt.stopPropagation();
            onDocDropActiveChange(false);
          }}
          onDrop={(evt) => void onDocsDrop(evt)}
        >
          Drop docs here (.md / .txt / .pdf / images)
        </div>
      )}

      {docsLoading && <div className="skeleton-list" />}
      {!docsLoading && documents.length === 0 && <div className="muted">No indexed documents</div>}
      {!docsLoading && pdfDocuments.length > 0 && <div className="doc-subtitle">PDF/Image ({pdfDocuments.length})</div>}
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
      {!docsLoading && nonPdfDocuments.length > 0 && <div className="doc-subtitle">Other Docs ({nonPdfDocuments.length})</div>}
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
    </section>
  );
}
