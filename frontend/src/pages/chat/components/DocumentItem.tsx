import type { IndexedFileSummary } from "@/types/api";
import { useTranslation } from "react-i18next";
import { RefreshCw, Trash2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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
}: Readonly<Props>) {
  const { t } = useTranslation();
  const canManage =
    canUploadAndManageDocs || isAdmin || !doc.owner_user_id || (!!currentUserId && doc.owner_user_id === currentUserId);
  const indexingStatus = doc.indexing_status || "ready";
  // Was four hardcoded English words in a bilingual app.
  const statusLabel = t(`components.workbench.status.${indexingStatus}`, {
    defaultValue: indexingStatus,
  });
  const STATUS_VARIANT: Record<string, "warning" | "info" | "danger" | "success"> = {
    pending: "warning",
    indexing: "info",
    failed: "danger",
    error: "danger",
    ready: "success",
  };
  const statusVariant = STATUS_VARIANT[indexingStatus];

  return (
    <div className="rounded-control border border-line bg-surface p-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-[11px] font-medium text-ink">{doc.filename}</span>
            <Badge variant={statusVariant ?? "neutral"} size="xs">
              {statusLabel}
            </Badge>
          </div>
          <p className="mt-0.5 truncate font-mono text-[10px] text-ink-muted">
            {t("components.workbench.docMeta", {
              chunks: doc.chunks,
              visibility: doc.visibility || "private",
              disk: doc.exists_on_disk ? t("components.workbench.yes") : t("components.workbench.no"),
              uploads: doc.in_uploads ? t("components.workbench.yes") : t("components.workbench.no"),
              agent: doc.agent_class || "general",
            })}
            {doc.parser_profile ? ` | parser=${doc.parser_profile}` : ""}
            {typeof doc.triplets_written === "number" ? ` | graph=${doc.triplets_written}` : ""}
            {doc.indexing_stage ? ` | stage=${doc.indexing_stage}` : ""}
          </p>
          {doc.indexing_error ? <p className="mt-0.5 text-[10px] text-danger">{doc.indexing_error}</p> : null}
        </div>

        {canManage && (
          <div className="flex shrink-0 items-center gap-0.5">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => void onReindexDocument(doc)}
              title={t("components.workbench.reindex")}
            >
              <RefreshCw aria-hidden="true" />
              <span className="sr-only">{t("components.workbench.reindex")}</span>
            </Button>
            <Button
              variant="destructive-ghost"
              size="icon-sm"
              onClick={() => void onDeleteDocument(doc, false)}
              title={t("components.workbench.deleteIndex")}
            >
              <XCircle aria-hidden="true" />
              <span className="sr-only">{t("components.workbench.deleteIndex")}</span>
            </Button>
            <Button
              variant="destructive-ghost"
              size="icon-sm"
              onClick={() => void onDeleteDocument(doc, true)}
              title={t("components.workbench.deleteFile")}
            >
              <Trash2 aria-hidden="true" />
              <span className="sr-only">{t("components.workbench.deleteFile")}</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
