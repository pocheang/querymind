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
  return (
    <>
      <div className="pdf-kpi-grid">
        <div className="pdf-kpi-card">
          <span>PDF/IMAGE DOCS</span>
          <strong>{pdfDocuments.length}</strong>
        </div>
        <div className="pdf-kpi-card">
          <span>NEED REINDEX</span>
          <strong>{pdfNeedingReindex.length}</strong>
        </div>
      </div>

      <select
        value={pdfTargetFile}
        onChange={(e) => onPdfTargetFileChange(e.target.value)}
        disabled={!pdfDocuments.length}
      >
        {!pdfDocuments.length && <option value="">暂无PDF文档</option>}
        {pdfDocuments.map((doc) => (
          <option key={doc.source} value={doc.filename}>
            {doc.filename} (块={doc.chunks || 0})
          </option>
        ))}
      </select>

      <div className="row-actions wrap">
        <button type="button" className="secondary tiny-btn" onClick={() => onSwitchAgentMode("pdf_text")}>
          强制 pdf_text
        </button>
        <button type="button" className="secondary tiny-btn" onClick={() => onSwitchAgentMode("")}>
          返回自动
        </button>
      </div>

      {pdfNeedingReindex.length > 0 && (
        <div className="hint">部分PDF文档块数为0，请在提问前重建索引。</div>
      )}
    </>
  );
}
