import { BookOpen, CheckCircle2, FileSpreadsheet } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ScenarioKey, ScenarioTableRow } from "./types";

interface ScenarioTableProps {
  title: string;
  headers: string[];
  rows: ScenarioTableRow[];
}

function ScenarioTable({
  title,
  headers,
  rows,
}: Readonly<ScenarioTableProps>) {
  return (
    <div className="overflow-x-auto rounded-control border border-line bg-surface">
      <div className="bg-surface-muted/60 px-3.5 py-2 border-b border-line text-xs font-semibold text-ink flex items-center gap-1.5">
        <FileSpreadsheet className="size-3.5 text-brand-accent" />
        <span>{title}</span>
      </div>
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-line bg-surface-muted/30 text-ink font-semibold">
            {headers.map((h) => (
              <th key={h} className="p-2.5">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line/40 text-ink-muted">
          {rows.map((row) => (
            <tr key={row.id}>
              {headers.map((h, col) => (
                <td key={`${row.id}-${h}`} className="p-2.5">{row.cells[col]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface PipelineAnswerShowcaseProps {
  selectedScenario: ScenarioKey;
  isZh: boolean;
  t: (key: string) => string;
}

export function PipelineAnswerShowcase({
  selectedScenario,
  isZh,
  t,
}: Readonly<PipelineAnswerShowcaseProps>) {
  return (
    <div className="rounded-card border border-emerald-500/30 bg-surface p-5 shadow-elev-1">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex size-7 items-center justify-center rounded-control bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="size-4" />
          </div>
          <span className="text-base sm:text-lg font-bold text-ink">
            {t("architecture.flow.finalAnswerLabel")}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" size="sm" mono className="text-xs py-1 px-2.5 text-emerald-600 dark:text-emerald-400 border-emerald-500/40 bg-emerald-500/10 font-semibold">
            {isZh ? "事实一致性: 99.2%" : "Grounding: 99.2%"}
          </Badge>
          <Badge variant="outline" size="sm" mono className="text-xs py-1 px-2.5 text-blue-600 dark:text-blue-400 border-blue-500/40 bg-blue-500/10 font-semibold">
            {isZh ? "幻觉率: <10%" : "Hallucination: <10%"}
          </Badge>
          <Badge variant="outline" size="sm" mono className="text-xs py-1 px-2.5 text-purple-600 dark:text-purple-400 border-purple-500/40 bg-purple-500/10 font-semibold">
            {isZh ? "首字耗时: 420ms" : "TTFT: 420ms"}
          </Badge>
        </div>
      </div>

      <div className="mt-4 space-y-3.5">
        <div className="rounded-control bg-surface-muted/30 p-4 border border-line/70 text-sm sm:text-base font-medium text-ink leading-relaxed shadow-sm">
          {t(`architecture.flow.scenarios.${selectedScenario}.answer`)}
        </div>

        {selectedScenario === "rag" && (
          <ScenarioTable
            title={isZh ? "表 1：员工差旅住宿报销限额细则（摘自制度附表一）" : "Table 1: Employee Travel Lodging Cap Specifications (Policy Appendix A)"}
            headers={isZh ? ["城市分类", "适用城市范畴", "研发报销上限", "凭证要求", "审批权限"] : ["City Tier", "Covered Cities", "R&D Cap", "Invoicing", "Approval Chain"]}
            rows={[
              {
                id: "tier-1",
                cells: [
                  <span key="tier-1-type" className="font-medium text-ink">{isZh ? "一线城市" : "Tier 1"}</span>,
                  isZh ? "北京、上海、广州、深圳" : "Beijing, Shanghai, Guangzhou, Shenzhen",
                  <span key="tier-1-cap" className="font-mono font-bold text-brand-text">¥500 / 人 / 天</span>,
                  isZh ? "增值税专用/普通发票" : "VAT Tax Invoice",
                  isZh ? "部门总监审批" : "Director Approval",
                ],
              },
              {
                id: "new-tier-1",
                cells: [
                  <span key="new-tier-1-type" className="font-medium text-ink">{isZh ? "新一线城市" : "New Tier 1"}</span>,
                  isZh ? "杭州、成都、武汉、南京等" : "Hangzhou, Chengdu, Wuhan, Nanjing",
                  <span key="new-tier-1-cap" className="font-mono font-bold text-ink">¥400 / 人 / 天</span>,
                  isZh ? "增值税专用/普通发票" : "VAT Tax Invoice",
                  isZh ? "研发主管审批" : "Manager Approval",
                ],
              },
              {
                id: "tier-2",
                cells: [
                  <span key="tier-2-type" className="font-medium text-ink">{isZh ? "二线及其他" : "Tier 2 & Other"}</span>,
                  isZh ? "其他省会及地级市" : "Other Regional Capitals",
                  <span key="tier-2-cap" className="font-mono text-ink">¥300 / 人 / 天</span>,
                  isZh ? "合规发票实报实销" : "Standard Invoices",
                  isZh ? "项目经理审批" : "Project Lead Approval",
                ],
              },
            ]}
          />
        )}

        {selectedScenario === "react" && (
          <ScenarioTable
            title={isZh ? "表 2：华东区月度销售业绩与环比增长分析表（数据沙箱精确计算）" : "Table 2: East Region Monthly Sales & MoM Growth Analysis (Sandbox Calculator)"}
            headers={isZh ? ["统计月份", "销售额 (万元)", "环比净增额", "环比增长率 (%)", "主要拉动行业", "成交笔数"] : ["Month", "Revenue (10k RMB)", "Net Growth", "MoM Rate (%)", "Leading Drivers", "Orders"]}
            rows={[
              {
                id: "month-t-minus-1",
                cells: [
                  <span key="t-minus-1-month" className="font-medium text-ink">{isZh ? "前一月 (T-1)" : "Month T-1"}</span>,
                  <span key="t-minus-1-rev" className="font-mono">210.0 万元</span>,
                  <span key="t-minus-1-growth" className="font-mono">{isZh ? "基线月份" : "Baseline"}</span>,
                  <span key="t-minus-1-rate" className="font-mono">-</span>,
                  isZh ? "传统制造 (52%)" : "Manufacturing (52%)",
                  <span key="t-minus-1-orders" className="font-mono">128 笔</span>,
                ],
              },
              {
                id: "month-t",
                cells: [
                  <span key="t-month" className="font-medium text-ink">{isZh ? "上月 (T)" : "Month T"}</span>,
                  <span key="t-rev" className="font-mono font-bold text-brand-text">245.8 万元</span>,
                  <span key="t-growth" className="font-mono text-emerald-600 font-bold">+35.8 万元</span>,
                  <span key="t-rate" className="font-mono text-emerald-600 font-bold">+17.05%</span>,
                  <span key="t-driver" className="font-medium text-ink">{isZh ? "新能源 / 储能 (68%)" : "Clean Energy (68%)"}</span>,
                  <span key="t-orders" className="font-mono font-bold text-ink">164 笔</span>,
                ],
              },
            ]}
          />
        )}

        {selectedScenario === "graph" && (
          <ScenarioTable
            title={isZh ? "表 3：Neo4j 图谱 2-Hop 关联关系推理表（Cypher 最短路径遍历）" : "Table 3: Neo4j Graph 2-Hop Relation Inference (Cypher Traversal)"}
            headers={isZh ? ["起始实体", "关系谓词 (Cypher)", "目标实体", "协作职责说明", "置信度"] : ["Source Entity", "Relationship", "Target Entity", "Role / Duty", "Confidence"]}
            rows={[
              {
                id: "graph-rel-1",
                cells: [
                  <span key="g1-src" className="font-medium text-ink">{isZh ? "李工 (架构师)" : "Engineer Li (Architect)"}</span>,
                  <span key="g1-rel" className="font-mono text-brand-text font-bold">[:MEMBER_OF]</span>,
                  <span key="g1-tgt" className="font-medium text-ink">{isZh ? "AI平台四期项目" : "AI Platform Phase 4"}</span>,
                  isZh ? "担任核心架构师与技术负责" : "Core Tech Architect",
                  <span key="g1-conf" className="font-mono text-emerald-600 font-bold">1.00</span>,
                ],
              },
              {
                id: "graph-rel-2",
                cells: [
                  <span key="g2-src" className="font-medium text-ink">{isZh ? "张总 (部门总监)" : "Director Zhang"}</span>,
                  <span key="g2-rel" className="font-mono text-brand-text font-bold">[:DIRECTS]</span>,
                  <span key="g2-tgt" className="font-medium text-ink">{isZh ? "AI平台四期项目" : "AI Platform Phase 4"}</span>,
                  isZh ? "担任项目总负责人兼资源审批人" : "Project Director",
                  <span key="g2-conf" className="font-mono text-emerald-600 font-bold">1.00</span>,
                ],
              },
              {
                id: "graph-rel-3",
                cells: [
                  <span key="g3-src" className="font-medium text-ink">{isZh ? "李工" : "Engineer Li"}</span>,
                  <span key="g3-rel" className="font-mono text-purple-600 font-bold">[:REPORTS_TO]</span>,
                  <span key="g3-tgt" className="font-medium text-ink">{isZh ? "张总" : "Director Zhang"}</span>,
                  isZh ? "项目内直属技术汇报关系" : "Direct Project Reporting Line",
                  <span key="g3-conf" className="font-mono text-emerald-600 font-bold">0.99</span>,
                ],
              },
            ]}
          />
        )}

        <div className="flex items-center gap-2.5 rounded-control bg-surface-muted/60 px-4 py-2.5 text-xs sm:text-sm text-ink-muted border border-line/40">
          <BookOpen className="size-4 text-brand-accent shrink-0" />
          <span className="font-mono text-ink font-medium">
            {t(`architecture.flow.scenarios.${selectedScenario}.citation`)}
          </span>
        </div>
      </div>
    </div>
  );
}
