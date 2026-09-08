import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import type { IndexedFileSummary } from "@/types/api";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

type Props = {
  pdfDocuments: IndexedFileSummary[];
  pdfNeedingReindex: IndexedFileSummary[];
  pdfTargetFile: string;
  onPdfTargetFileChange: (filename: string) => void;
  onSwitchAgentMode: (mode: AgentClassHint) => void;
  onDraftQuestion: () => void;
};

export function PdfWorkbench({
  pdfDocuments,
  pdfNeedingReindex,
  pdfTargetFile,
  onPdfTargetFileChange,
  onSwitchAgentMode,
  onDraftQuestion,
}: Readonly<Props>) {
  const { t } = useTranslation();

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-1.5">
        <div className="rounded-control border border-line bg-surface p-1.5 text-center">
          <span className="block truncate text-[9px] uppercase tracking-wider text-ink-muted">
            {t("components.workbench.pdfImageDocsShort")}
          </span>
          <strong className="block font-mono text-xs font-bold text-brand-text">{pdfDocuments.length}</strong>
        </div>
        <div className="rounded-control border border-line bg-surface p-1.5 text-center">
          <span className="block truncate text-[9px] uppercase tracking-wider text-ink-muted">
            {t("components.workbench.needReindex")}
          </span>
          <strong className="block font-mono text-xs font-bold text-brand-text">{pdfNeedingReindex.length}</strong>
        </div>
      </div>

      <select
        value={pdfTargetFile}
        onChange={(event) => onPdfTargetFileChange(event.target.value)}
        disabled={!pdfDocuments.length}
        className="w-full rounded-control border border-brand-border bg-surface px-2 py-1.5 text-[11px] text-ink focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] disabled:opacity-60"
      >
        {!pdfDocuments.length && <option value="">{t("components.workbench.noPdfDocs")}</option>}
        {pdfDocuments.map((doc) => (
          <option key={doc.source} value={doc.filename}>
            {doc.filename} ({t("components.workbench.chunks", { count: doc.chunks || 0 })})
          </option>
        ))}
      </select>

      <div className="flex flex-wrap gap-1">
        <Button variant="secondary" size="xs" onClick={() => onSwitchAgentMode("pdf_text")}>
          {t("components.workbench.forcePdfText")}
        </Button>
        <Button variant="secondary" size="xs" onClick={onDraftQuestion}>
          {t("components.workbench.draftQuestion")}
        </Button>
        <Button variant="ghost" size="xs" onClick={() => onSwitchAgentMode("")}>
          {t("components.workbench.returnAuto")}
        </Button>
      </div>

      {pdfNeedingReindex.length > 0 && (
        <p className="text-[10px] text-warning">{t("components.workbench.reindexHint")}</p>
      )}
    </div>
  );
}
