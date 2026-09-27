import type { IndexedFileSummary } from "@/types/api";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { RefreshCw, Trash2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { appApi } from "@/lib/api";
import { AGENT_MODES } from "@/pages/chat/constants";
import { useAgentModeLabels } from "@/pages/chat/agentModeLabels";

/**
 * Which specialist a document belongs to, changeable in place.
 *
 * The label only orders what a specialist retrieves (the server boosts a
 * labelled passage after reranking); it never decides who may read the
 * document, and changing it needs no reindex. The options are the mode cards'
 * own classes, so there is no second list of agent classes to drift.
 */
function DocumentDomainSelect({ documentId, initial }: Readonly<{ documentId: string; initial: string }>) {
  const { t } = useTranslation();
  const labelFor = useAgentModeLabels();
  const [value, setValue] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const modes = AGENT_MODES.filter((mode) => mode.key);
  const known = modes.some((mode) => mode.key === value);

  const change = async (next: string) => {
    const previous = value;
    setValue(next);
    setSaving(true);
    setFailed(false);
    try {
      const res = await appApi.documentRelabel(documentId, next);
      setValue(res.agent_class);
    } catch {
      setValue(previous);
      setFailed(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <span className="inline-flex items-center gap-1">
      <select
        value={value}
        disabled={saving}
        onChange={(e) => void change(e.target.value)}
        aria-label={t("components.workbench.domainLabel")}
        className="h-6 rounded-control border border-brand-border bg-surface px-1 text-xs text-ink focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] disabled:opacity-60"
      >
        {!known && <option value={value}>{value}</option>}
        {modes.map((mode) => (
          <option key={mode.key} value={mode.key}>
            {labelFor(mode).title}
          </option>
        ))}
      </select>
      {failed && (
        <span role="alert" className="text-xs font-medium text-danger">
          {t("components.workbench.relabelFailed")}
        </span>
      )}
    </span>
  );
}

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
  // The server answers this per row (`can_manage`), from the same predicate the
  // reindex and delete endpoints enforce, so an offered button is a request that
  // will be accepted. The client used to guess with four clauses, and one of
  // them -- `!doc.owner_user_id`, "nobody owns it, so anyone may manage it" --
  // was exactly backwards for the shared corpus: a `data/docs/` file has no
  // owner and is manageable by NOBODY, since manageability means "under
  // uploads_path". Every shared-corpus document therefore showed Reindex,
  // Del Index and Del File, and all three answered 404.
  //
  // The role check still applies: a role that may not manage documents at all
  // does not get buttons for the ones it happens to own.
  const canManage = doc.can_manage && (canUploadAndManageDocs || isAdmin || !!currentUserId);
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
            <span className="truncate text-xs sm:text-sm font-semibold text-ink">{doc.filename}</span>
            <Badge variant={statusVariant ?? "neutral"} size="xs">
              {statusLabel}
            </Badge>
          </div>
          <p className="mt-0.5 truncate font-mono text-xs text-ink/75">
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
          {doc.indexing_error ? <p className="mt-0.5 text-xs font-medium text-danger">{doc.indexing_error}</p> : null}
          {canManage && doc.document_id ? (
            <div className="mt-1">
              <DocumentDomainSelect documentId={doc.document_id} initial={doc.agent_class || "general"} />
            </div>
          ) : null}
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
