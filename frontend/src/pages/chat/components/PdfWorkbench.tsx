import type { IndexedFileSummary } from "@/types/api";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

type Props = {
  pdfDocuments: IndexedFileSummary[];
  pdfNeedingReindex: IndexedFileSummary[];
  pdfTargetFile: string;
  onDraftPdfQuestion: () => void;
  onPdfTargetFileChange: (filename: string) => void;
  onSwitchAgentMode: (mode: AgentClassHint) => void;
};

export function PdfWorkbench({
  pdfDocuments,
  pdfNeedingReindex,
  pdfTargetFile,
  onDraftPdfQuestion,
  onPdfTargetFileChange,
  onSwitchAgentMode,
}: Props) {
  return (
    <section className="panel">
      <div className="section-head">
        <strong>PDF Workbench</strong>
        <button type="button" className="secondary tiny-btn" onClick={onDraftPdfQuestion}>
          Draft Question
        </button>
      </div>
      <div className="pdf-kpi-grid">
        <div className="pdf-kpi-card">
          <span>PDF/Image Docs</span>
          <strong>{pdfDocuments.length}</strong>
        </div>
        <div className="pdf-kpi-card">
          <span>Need Reindex</span>
          <strong>{pdfNeedingReindex.length}</strong>
        </div>
      </div>
      <select
        value={pdfTargetFile}
        onChange={(e) => onPdfTargetFileChange(e.target.value)}
        disabled={!pdfDocuments.length}
      >
        {!pdfDocuments.length && <option value="">No PDF docs</option>}
        {pdfDocuments.map((doc) => (
          <option key={doc.source} value={doc.filename}>
            {doc.filename} (chunks={doc.chunks || 0})
          </option>
        ))}
      </select>
      <div className="row-actions wrap">
        <button type="button" className="secondary tiny-btn" onClick={() => onSwitchAgentMode("pdf_text")}>
          Force pdf_text
        </button>
        <button type="button" className="secondary tiny-btn" onClick={() => onSwitchAgentMode("")}>
          Back to auto
        </button>
      </div>
      {pdfNeedingReindex.length > 0 && (
        <div className="hint">Some PDF docs have 0 chunks. Reindex before asking detailed questions.</div>
      )}
    </section>
  );
}
