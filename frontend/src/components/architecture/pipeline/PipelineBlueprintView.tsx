import { ExternalLink, Images } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function PipelineBlueprintView({ isZh }: Readonly<{ isZh: boolean }>) {
  const { t } = useTranslation();

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-surface-muted/50 p-4 sm:p-5 rounded-control border border-line">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Images className="size-5 text-brand-accent" />
            <h3 className="text-base sm:text-lg font-bold text-ink">
              {isZh ? "QueryMind RAG 7阶段端到端系统架构全景蓝图" : "QueryMind RAG 7-Stage End-to-End Architecture Blueprint"}
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-ink-muted leading-relaxed">
            {isZh
              ? "涵盖客户端接入、安全门禁限流、智能体意图路由、向量与知识图谱混合检索、ReAct沙箱工具、引用优先合成与安全出境DLP全流程高清架构图。"
              : "Comprehensive architectural blueprint illustrating Client Ingress, Security Sentinel, Multi-Agent Router, Hybrid Vector/Graph Store, ReAct Sandbox, Synthesis, and Output DLP."}
          </p>
        </div>
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Badge variant="brand" size="sm" mono className="text-xs py-1 px-2.5 font-bold">
            1080p Ultra-HD
          </Badge>
          <Button asChild variant="outline" size="sm" className="text-xs">
            <a href="/architecture_flow_diagram.jpg" target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-3.5 mr-1.5" />
              {isZh ? "在新窗口打开原图" : "Open Full Image"}
            </a>
          </Button>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-card border border-line bg-surface-muted/30 p-2 sm:p-4 shadow-elev-2 flex items-center justify-center">
        <img
          src="/architecture_flow_diagram.jpg"
          alt="QueryMind RAG System Architecture Diagram"
          className="w-full max-h-[760px] object-contain rounded-control transition-all duration-300 hover:scale-[1.01]"
          loading="lazy"
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-blue-600 dark:text-blue-400">1. Client & Security Sentinel</span>
          <p className="text-ink-muted">{t("architecture.flow.blueprintStage1Desc")}</p>
        </div>
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-cyan-600 dark:text-cyan-400">2. Intent Router & Multi-Store</span>
          <p className="text-ink-muted">{t("architecture.flow.blueprintStage2Desc")}</p>
        </div>
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-amber-600 dark:text-amber-400">3. ReAct Governed Sandbox</span>
          <p className="text-ink-muted">{t("architecture.flow.blueprintStage3Desc")}</p>
        </div>
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-rose-600 dark:text-rose-400">4. Synthesis & Output DLP</span>
          <p className="text-ink-muted">{t("architecture.flow.blueprintStage4Desc")}</p>
        </div>
      </div>
    </div>
  );
}
