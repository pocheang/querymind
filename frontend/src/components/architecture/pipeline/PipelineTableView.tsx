import { ShieldCheck, Table } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { STEPS } from "./types";

interface PipelineTableViewProps {
  isZh: boolean;
  t: (key: string) => string;
}

export function PipelineTableView({ isZh, t }: Readonly<PipelineTableViewProps>) {
  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-surface-muted/50 p-4 sm:p-5 rounded-control border border-line">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Table className="size-5 text-emerald-500" />
            <h3 className="text-base sm:text-lg font-bold text-ink">
              {isZh ? "QueryMind 全链路执行阶段规格对照表" : "QueryMind Pipeline Stage Specification Matrix"}
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-ink-muted leading-relaxed">
            {isZh
              ? "逐项对比系统 6 个核心执行阶段的职责角色、底层核心技术算法、SLA 耗时标准、输入产出与安全保障屏障。"
              : "Complete stage-by-stage technical comparison matrix covering roles, algorithms, latency SLA, inputs/outputs, and security guardrails."}
          </p>
        </div>
        <Badge variant="outline" size="sm" mono className="text-xs self-start sm:self-auto">
          6 Execution Stages
        </Badge>
      </div>

      <div className="overflow-x-auto rounded-card border border-line bg-surface shadow-elev-1">
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="border-b border-line bg-surface-muted/60 text-xs font-semibold text-ink">
              <th className="p-3.5 sm:p-4 whitespace-nowrap">{t("architecture.flow.tablePhase")}</th>
              <th className="p-3.5 sm:p-4 whitespace-nowrap">{t("architecture.flow.tableRole")}</th>
              <th className="p-3.5 sm:p-4 min-w-[220px]">{t("architecture.flow.tableTech")}</th>
              <th className="p-3.5 sm:p-4 whitespace-nowrap">{t("architecture.flow.tableLatency")}</th>
              <th className="p-3.5 sm:p-4 min-w-[240px]">{t("architecture.flow.tableIO")}</th>
              <th className="p-3.5 sm:p-4 min-w-[220px]">{t("architecture.flow.tableSecurity")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {STEPS.map((stg) => {
              const Icon = stg.icon;
              return (
                <tr key={stg.id} className="hover:bg-surface-muted/30 transition-colors">
                  <td className="p-3.5 sm:p-4 whitespace-nowrap">
                    <div className="flex items-center gap-2.5">
                      <div className={`flex size-8 items-center justify-center rounded-control border ${stg.badgeClass}`}>
                        <Icon className="size-4" />
                      </div>
                      <span className="font-mono text-sm font-bold text-ink">
                        Stage 0{stg.id}
                      </span>
                    </div>
                  </td>
                  <td className="p-3.5 sm:p-4 whitespace-nowrap">
                    <div className="text-sm font-bold text-ink">
                      {t(`architecture.flow.stages.${stg.stepKey}.role`)}
                    </div>
                    <div className="text-xs font-mono text-ink-muted">
                      {t(`architecture.flow.stages.${stg.stepKey}.techTitle`)}
                    </div>
                  </td>
                  <td className="p-3.5 sm:p-4 text-xs text-ink-muted leading-relaxed">
                    <p className="font-medium text-ink">{t(`architecture.flow.stages.${stg.stepKey}.techDesc`)}</p>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {(isZh ? stg.keyPointsZh : stg.keyPointsEn).map((pt) => (
                        <Badge key={pt} variant="outline" size="xs" mono className="text-xs bg-surface-muted/60">
                          {pt}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="p-3.5 sm:p-4 whitespace-nowrap">
                    <Badge variant="neutral" size="sm" mono className="text-xs py-1 px-2.5 font-bold">
                      {t(`architecture.flow.stages.${stg.stepKey}.badge`)}
                    </Badge>
                  </td>
                  <td className="p-3.5 sm:p-4 text-xs space-y-1">
                    <div className="text-ink-muted">
                      <span className="font-semibold text-ink">In:</span> {isZh ? stg.inputZh : stg.inputEn}
                    </div>
                    <div className="text-brand-text font-medium">
                      <span className="font-semibold text-ink">Out:</span> {isZh ? stg.outputZh : stg.outputEn}
                    </div>
                  </td>
                  <td className="p-3.5 sm:p-4 text-xs text-ink-muted leading-relaxed">
                    <div className="flex items-start gap-1.5">
                      <ShieldCheck className="size-3.5 text-emerald-500 shrink-0 mt-0.5" />
                      <span>{isZh ? stg.securityZh : stg.securityEn}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
