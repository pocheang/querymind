import { useTranslation } from "react-i18next";
import type { IndexedFileSummary } from "@/types/api";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

type Props = {
  pdfDocuments: IndexedFileSummary[];
  pdfNeedingReindex: IndexedFileSummary[];
  pdfTargetFile: string;
  onPdfTargetFileChange: (filename: string) => void;
  onSwitchAgentMode: (mode: AgentClassHint) => void;
};

export function PdfWorkbench({
  pdfDocuments,
  pdfNeedingReindex,
  pdfTargetFile,
  onPdfTargetFileChange,
  onSwitchAgentMode,
}: Props) {
  const { t } = useTranslation();

  return (
    <>
      <div className="pdf-kpi-grid">
        <div className="pdf-kpi-card">
          <span>{t("components.workbench.pdfImageDocsShort")}</span>
          <strong>{pdfDocuments.length}</strong>
        </div>
        <div className="pdf-kpi-card">
          <span>{t("components.workbench.needReindex")}</span>
          <strong>{pdfNeedingReindex.length}</strong>
        </div>
      </div>

      <select
        value={pdfTargetFile}
        onChange={(event) => onPdfTargetFileChange(event.target.value)}
        disabled={!pdfDocuments.length}
      >
        {!pdfDocuments.length && <option value="">{t("components.workbench.noPdfDocs")}</option>}
        {pdfDocuments.map((doc) => (
          <option key={doc.source} value={doc.filename}>
            {doc.filename} ({t("components.workbench.chunks", { count: doc.chunks || 0 })})
          </option>
        ))}
      </select>

      <div className="row-actions wrap">
        <button type="button" className="secondary tiny-btn" onClick={() => onSwitchAgentMode("pdf_text")}>
          {t("components.workbench.forcePdfText")}
        </button>
        <button type="button" className="secondary tiny-btn" onClick={() => onSwitchAgentMode("")}>
          {t("components.workbench.returnAuto")}
        </button>
      </div>

      {pdfNeedingReindex.length > 0 && <div className="hint">{t("components.workbench.reindexHint")}</div>}
    </>
  );
}
