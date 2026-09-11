import { DataFlowVisualization } from "@/components/DataFlowVisualization";

interface PipelineTopologyViewProps {
  t: (key: string) => string;
}

export function PipelineTopologyView({ t }: Readonly<PipelineTopologyViewProps>) {
  return (
    <div className="space-y-4">
      <DataFlowVisualization />
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-surface-muted/30 px-5 py-3 text-xs text-ink-muted">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-[#4a5568]" /> UI & Entry
          </span>
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-[#5a67d8]" /> Security & Auth
          </span>
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-[#3b82f6]" /> LangGraph Router
          </span>
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-[#10b981]" /> Quality Assurance
          </span>
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-[#8b5cf6]" /> Hybrid Retrieval
          </span>
          <span className="flex items-center gap-2">
            <span className="size-2.5 rounded-full bg-[#f59e0b]" /> Multi-Store
          </span>
        </div>
        <span className="font-mono text-xs text-ink-faint">
          {t("architecture.flow.topologyLegend")}
        </span>
      </div>
    </div>
  );
}
