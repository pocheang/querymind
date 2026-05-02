import type { IndexedFileSummary } from "@/types/api";

type Props = {
  doc: IndexedFileSummary;
  canUploadAndManageDocs: boolean;
  isAdmin: boolean;
  currentUserId?: string;
  onReindexDocument: (doc: IndexedFileSummary) => Promise<void>;
  onDeleteDocument: (doc: IndexedFileSummary, removeFile: boolean) => Promise<void>;
};

export function DocumentItem({
  doc,
  canUploadAndManageDocs,
  isAdmin,
  currentUserId,
  onReindexDocument,
  onDeleteDocument,
}: Props) {
  const canManage = canUploadAndManageDocs && (isAdmin || doc.owner_user_id === currentUserId);

  return (
    <div className="doc-row">
      <div>
        <div>{doc.filename}</div>
        <small className="muted">
          chunks={doc.chunks} | visibility={doc.visibility || "private"} | disk={doc.exists_on_disk ? "yes" : "no"} |
          uploads={doc.in_uploads ? "yes" : "no"} | agent={doc.agent_class || "general"}
        </small>
      </div>
      {canManage && (
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={() => void onReindexDocument(doc)}>
            Reindex
          </button>
          <button type="button" className="danger tiny-btn" onClick={() => void onDeleteDocument(doc, false)}>
            Del Index
          </button>
          <button type="button" className="danger tiny-btn" onClick={() => void onDeleteDocument(doc, true)}>
            Del File
          </button>
        </div>
      )}
    </div>
  );
}
