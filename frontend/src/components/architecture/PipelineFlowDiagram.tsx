import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileSpreadsheet,
  Images,
  Layers,
  Network,
  Play,
  Radio,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Table,
  User,
  Workflow,
  Wrench,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataFlowVisualization } from "@/components/DataFlowVisualization";

type ViewPerspective = "story" | "tech" | "table" | "blueprint" | "topology";
type ScenarioKey = "rag" | "react" | "graph";

interface StepConfig {
  id: number;
  stepKey: "step1" | "step2" | "step3" | "step4" | "step5" | "step6";
  icon: React.ComponentType<{ className?: string }>;
  colorRing: string;
  badgeClass: string;
  iconBg: string;
  analogyZh: string;
  analogyEn: string;
  simStatusZh: string;
  simStatusEn: string;
  keyPointsZh: string[];
  keyPointsEn: string[];
  inputZh: string;
  inputEn: string;
  outputZh: string;
  outputEn: string;
  securityZh: string;
  securityEn: string;
}

const STEPS: StepConfig[] = [
  {
    id: 1,
    stepKey: "step1",
    icon: ShieldCheck,
    colorRing: "border-blue-500/50 shadow-blue-500/10",
    badgeClass: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
    iconBg: "bg-blue-500/15 text-blue-600 dark:text-blue-400",
    analogyZh: "像大楼门禁保安：核验身份门禁卡，严格拦截危险违禁品",
    analogyEn: "Like a corporate security gate: verifies access cards and stops contraband",
    simStatusZh: "安全门禁：核验用户租户鉴权，防范提示词注入与恶意代码...",
    simStatusEn: "Security Gate: Verifying JWT auth, blocking prompt injection & SQLi...",
    keyPointsZh: ["JWT HttpOnly 严格校验", "角色权限隔离 (RBAC)", "敏感操作频率限流", "输入代码恶意清洗"],
    keyPointsEn: ["JWT HttpOnly Strict Auth", "Tenant RBAC Scope Isolation", "Sensitive Quota Rate Limit", "Malicious Input Sanitization"],
    inputZh: "客户端 HTTPS / SSE 原始请求 + JWT HttpOnly Cookie",
    inputEn: "Raw HTTPS / SSE Request + JWT HttpOnly Cookie",
    outputZh: "纯净合法提问文本 + 锁定租户范围 (owner_user_id)",
    outputEn: "Sanitized Prompt + Locked Tenant Scope (owner_user_id)",
    securityZh: "SQLi 注入过滤、提示词越狱阻断、1-5 req/h 限流",
    securityEn: "SQLi filter, prompt jailbreak blocking, 1-5 req/h rate limits",
  },
  {
    id: 2,
    stepKey: "step2",
    icon: Workflow,
    colorRing: "border-cyan-500/50 shadow-cyan-500/10",
    badgeClass: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/30",
    iconBg: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-400",
    analogyZh: "像总服务台导医：快速判断您的需求类型，安排最合适的专家团队",
    analogyEn: "Like a hospital triage desk: quickly routes your request to the right department",
    simStatusZh: "调度指挥官：进行中文语义分词与意图判定，分流至最适推理档位...",
    simStatusEn: "Router: Segmenting NLP tokens, determining intent, assigning optimal tier...",
    keyPointsZh: ["Jieba 中文语义分词", "相似意图识别去重", "3层仲裁判定 (>99% 准度)", "动态切换 Fast/Balanced/Deep"],
    keyPointsEn: ["Jieba Token Preprocessing", "Semantic Query Dedup", "3-Tier Routing (>99% Accuracy)", "Dynamic Fast/Balanced/Deep Tiers"],
    inputZh: "清洗后的用户自然语言提问",
    inputEn: "Sanitized natural language query",
    outputZh: "执行路由分支 (RAG / ReAct / Graph) + 推理配置档位",
    outputEn: "Routing Decision (RAG / ReAct / Graph) + Tier Profile",
    securityZh: "3层仲裁裁决 (>99% 准确度)、去重防恶意重复消耗",
    securityEn: "3-tier arbitration (>99% accuracy), dedup caching",
  },
  {
    id: 3,
    stepKey: "step3",
    icon: Search,
    colorRing: "border-emerald-500/50 shadow-emerald-500/10",
    badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
    iconBg: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
    analogyZh: "像金牌图书管理员：在万卷馆藏中凭‘字面’与‘意思’精准翻出相关原文",
    analogyEn: "Like a master librarian: pulls the exact passages by keyword and semantic meaning",
    simStatusZh: "图书管理员：向量多维匹配 + BM25 关键词联合检索，深度重排截断...",
    simStatusEn: "Librarian: Dual vector + BM25 recall, RRF fusion, and cross-reranking...",
    keyPointsZh: ["ChromaDB 稠密向量索引", "BM25 倒排关键词快搜", "RRF 互惠排名权重融合", "BGE-Reranker 交叉打分"],
    keyPointsEn: ["ChromaDB BGE-M3 Dense Vectors", "BM25 Inverted Sparse Index", "RRF Reciprocal Rank Fusion", "BGE-Reranker-V2 Cross-Scoring"],
    inputZh: "分词优化查询与语义向量嵌入",
    inputEn: "Segmented query & semantic embedding vectors",
    outputZh: "Top-K 权威制度分块 (含 doc_id、页码、段落文本)",
    outputEn: "Top-K Grounded Chunks (with doc_id, page, text)",
    securityZh: "强制 owner_user_id 租户作用域隔离，防跨租户越权窃取",
    securityEn: "Mandatory tenant scope isolation, cross-tenant leak guard",
  },
  {
    id: 4,
    stepKey: "step4",
    icon: Wrench,
    colorRing: "border-amber-500/50 shadow-amber-500/10",
    badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
    iconBg: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
    analogyZh: "像专业助理：遇到复杂计算或查外部数据，带上审批批件打开工具箱",
    analogyEn: "Like a certified specialist: accesses sandboxed calculators or APIs with approval",
    simStatusZh: "特约助手：按需唤醒受控工具沙箱，携带审批令牌执行并观察反馈...",
    simStatusEn: "Tool Chamber: Invoking sandboxed tools with signed token, observing output...",
    keyPointsZh: ["Think-Act-Observe 思考循环", "单次有效签名审批令牌", "外部联网实时调研兜底", "独立工具超时熔断保护"],
    keyPointsEn: ["Think-Act-Observe ReAct Loops", "Signed Single-Use Approval Tokens", "Dynamic Web Research Fallback", "Per-Tool Timeout Degradation"],
    inputZh: "待求解子任务指令 (计算公式、API 调用参数)",
    inputEn: "Sub-task specifications (calculator expression, API params)",
    outputZh: "工具精确执行数据 (统计报表、实时数据回传)",
    outputEn: "Structured execution observations & numeric results",
    securityZh: "单次有效签名审批令牌机制，独立执行沙箱隔离与熔断",
    securityEn: "Single-use signed approval token, sandboxed execution",
  },
  {
    id: 5,
    stepKey: "step5",
    icon: Sparkles,
    colorRing: "border-purple-500/50 shadow-purple-500/10",
    badgeClass: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30",
    iconBg: "bg-purple-500/15 text-purple-600 dark:text-purple-400",
    analogyZh: "像论文作者：根据检索证据写下严谨回答，每句话打上 [1] 引用角标",
    analogyEn: "Like a research author: writes answers grounded in evidence, citing [1] footnotes",
    simStatusZh: "主笔撰稿人：端到端引用优先合成，SSE 打字机逐字实时推流...",
    simStatusEn: "Lead Writer: Citation-first synthesis, streaming typewriter via SSE...",
    keyPointsZh: ["引用标记 [1][2] 按序植入", "严格绑定原始文档页码分块", "SSE 流式逐字推向客户端", "心跳保活包防止网络断连"],
    keyPointsEn: ["Inline Citations [1][2] Tagged", "Anchored to Document Page Chunks", "SSE Streaming Incremental Output", "Heartbeat Keepalive Packets"],
    inputZh: "原始提问 + 检索到的事实原文 + 工具执行观测数据",
    inputEn: "User query + retrieved factual chunks + tool observations",
    outputZh: "打字机流式输出回答 + 行内引用标记 [1], [2]",
    outputEn: "Streaming typewriter text with inline citations [1], [2]",
    securityZh: "证据强绑定约束，未经验证推论强制降级或提示缺失",
    securityEn: "Strict citation grounding, ungrounded claims hedged",
  },
  {
    id: 6,
    stepKey: "step6",
    icon: CheckCircle2,
    colorRing: "border-rose-500/50 shadow-rose-500/10",
    badgeClass: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30",
    iconBg: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    analogyZh: "像终审质检主编：逐字核对杜绝胡编乱造，对敏感隐私实施实时涂黑",
    analogyEn: "Like an editor-in-chief: verifies zero fabrication and redacts private secrets",
    simStatusZh: "终审质检员：NLI 事实一致性蕴含核对，Output DLP 安全脱敏放行！",
    simStatusEn: "Chief Inspector: NLI factual entailment verified, DLP redacted, committed!",
    keyPointsZh: ["句子级 Grounding 事实校验", "NLI 蕴含推断 (幻觉率 <10%)", "流式 Chunk 输出实时脱敏", "审计历史异步落库与监控"],
    keyPointsEn: ["Sentence-Level Grounding Check", "NLI Entailment (Hallucination <10%)", "Streaming Chunk Output DLP", "Asynchronous Session State Commit"],
    inputZh: "LLM 逐字候选答案流与对应依据段落",
    inputEn: "LLM candidate answer stream & evidence passages",
    outputZh: "最终呈现在屏幕上的可信回答 + 历史审计会话存储",
    outputEn: "Verified clean answer on screen + audit session committed",
    securityZh: "NLI 双向蕴含推断 (事实幻觉率 <10%)、分块 DLP 敏感词脱敏",
    securityEn: "NLI entailment (<10% hallucination), streaming DLP redaction",
  },
];

function getCardStateClass(isCurrentActive: boolean, isFocused: boolean): string {
  if (isCurrentActive) {
    return "border-brand-accent ring-2 ring-brand-accent/50 bg-surface shadow-elev-2 scale-[1.02]";
  }
  if (isFocused) {
    return "border-brand-border ring-1 ring-brand-border bg-surface shadow-elev-1";
  }
  return "border-line bg-surface hover:border-brand-border/80 hover:shadow-elev-1";
}

function StepBadge({
  isCurrentActive,
  isPastCompleted,
  hasCompletedOnce,
  badgeText,
  activeStepText,
  completeStepText,
}: Readonly<{
  isCurrentActive: boolean;
  isPastCompleted: boolean;
  hasCompletedOnce: boolean;
  badgeText: string;
  activeStepText: string;
  completeStepText: string;
}>) {
  if (isCurrentActive) {
    return (
      <Badge variant="brand" size="xs" mono className="text-xs py-0.5 px-2 animate-pulse font-semibold">
        {activeStepText}
      </Badge>
    );
  }
  if (isPastCompleted || hasCompletedOnce) {
    return (
      <Badge
        variant="outline"
        size="xs"
        mono
        className="text-xs py-0.5 px-2 text-emerald-600 dark:text-emerald-400 border-emerald-500/40 bg-emerald-500/10 font-semibold"
      >
        <Check className="mr-1 size-3" />
        {completeStepText}
      </Badge>
    );
  }
  return (
    <Badge variant="neutral" size="xs" mono className="text-xs py-0.5 px-2">
      {badgeText}
    </Badge>
  );
}

interface StepCardProps {
  stg: StepConfig;
  isCurrentActive: boolean;
  isPastCompleted: boolean;
  hasCompletedOnce: boolean;
  isFocused: boolean;
  perspective: ViewPerspective;
  isZh: boolean;
  onSelect: (id: number) => void;
  t: (key: string) => string;
}

function StepCard({
  stg,
  isCurrentActive,
  isPastCompleted,
  hasCompletedOnce,
  isFocused,
  perspective,
  isZh,
  onSelect,
  t,
}: Readonly<StepCardProps>) {
  const Icon = stg.icon;
  const roleTitle = t(`architecture.flow.stages.${stg.stepKey}.role`);
  const techTitle = t(`architecture.flow.stages.${stg.stepKey}.techTitle`);
  const storyDesc = t(`architecture.flow.stages.${stg.stepKey}.storyDesc`);
  const techDesc = t(`architecture.flow.stages.${stg.stepKey}.techDesc`);
  const badgeText = t(`architecture.flow.stages.${stg.stepKey}.badge`);
  const keyPoints = isZh ? stg.keyPointsZh : stg.keyPointsEn;
  const cardBorder = getCardStateClass(isCurrentActive, isFocused);

  return (
    <button
      type="button"
      onClick={() => onSelect(stg.id)}
      className={`group relative flex w-full cursor-pointer flex-col rounded-card border text-left transition-all duration-200 ${cardBorder}`}
    >
      {/* Step Header */}
      <div className="flex items-center justify-between gap-3 border-b border-line/60 bg-surface-muted/30 p-4">
        <div className="flex items-center gap-3">
          <div className={`flex size-9 items-center justify-center rounded-control border ${stg.badgeClass}`}>
            <Icon className="size-4.5" aria-hidden="true" />
          </div>
          <div>
            <div className="text-sm sm:text-base font-bold text-ink leading-snug">
              {perspective === "story" ? roleTitle : techTitle}
            </div>
            <div className="text-xs font-mono text-ink-muted leading-snug">
              {perspective === "story" ? techTitle : roleTitle}
            </div>
          </div>
        </div>

        <StepBadge
          isCurrentActive={isCurrentActive}
          isPastCompleted={isPastCompleted}
          hasCompletedOnce={hasCompletedOnce}
          badgeText={badgeText}
          activeStepText={t("architecture.flow.activeStep")}
          completeStepText={t("architecture.flow.completeStep")}
        />
      </div>

      {/* Step Body */}
      <div className="flex-1 p-4 space-y-3">
        <div className="text-sm text-ink-muted leading-relaxed">
          {perspective === "story" ? (
            <>
              <p className="font-medium text-ink leading-relaxed text-sm sm:text-base">{storyDesc}</p>
              <p className="mt-2 text-xs sm:text-sm text-ink-muted border-l-2 border-brand-border pl-2.5 leading-relaxed">
                💡 {isZh ? stg.analogyZh : stg.analogyEn}
              </p>
            </>
          ) : (
            <p className="font-medium text-ink leading-relaxed text-sm sm:text-base">{techDesc}</p>
          )}
        </div>

        {/* Feature Badges */}
        <div className="flex flex-wrap gap-1.5 pt-1.5">
          {keyPoints.map((point) => (
            <Badge
              key={point}
              variant="outline"
              size="xs"
              mono
              className="text-xs py-0.5 px-2 bg-surface-muted/60 text-ink-muted"
            >
              {point}
            </Badge>
          ))}
        </div>
      </div>

      {/* Card Footer */}
      <div className="border-t border-line/40 px-4 py-2 flex items-center justify-between text-xs">
        <span className="font-mono text-ink-faint">
          {t("architecture.flow.step")} 0{stg.id} / 06
        </span>
        <span className="font-mono text-ink-muted flex items-center gap-1.5">
          <Clock className="size-3" />
          {badgeText}
        </span>
      </div>
    </button>
  );
}

function BlueprintView({ isZh }: Readonly<{ isZh: boolean }>) {
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
          <p className="text-ink-muted">JWT HttpOnly + RBAC 租户隔离，SQLi 与提示词越狱防御，毫秒放行。</p>
        </div>
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-cyan-600 dark:text-cyan-400">2. Intent Router & Multi-Store</span>
          <p className="text-ink-muted">Jieba 分词 + 意图三层仲裁，ChromaDB 向量与 Neo4j 图谱双轨混合检索。</p>
        </div>
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-amber-600 dark:text-amber-400">3. ReAct Governed Sandbox</span>
          <p className="text-ink-muted">思考-行动-观察循环，单次有效签名审批令牌，防范高风险越权调用。</p>
        </div>
        <div className="p-3.5 rounded-control border border-line bg-surface text-xs space-y-1">
          <span className="font-bold text-rose-600 dark:text-rose-400">4. Synthesis & Output DLP</span>
          <p className="text-ink-muted">行内角标 [1][2] 原文锚定，SSE 逐字流式推流，NLI 事实一致性核对与脱敏。</p>
        </div>
      </div>
    </div>
  );
}

function TableView({ isZh, t }: Readonly<{ isZh: boolean; t: (key: string) => string }>) {
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

function TopologyView({ t }: Readonly<{ t: (key: string) => string }>) {
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

function FlowHeader({
  perspective,
  setPerspective,
  t,
}: Readonly<{
  perspective: ViewPerspective;
  setPerspective: (p: ViewPerspective) => void;
  t: (key: string) => string;
}>) {
  return (
    <CardHeader className="flex flex-col gap-4 border-b border-line bg-surface-muted/40 p-5 sm:p-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1.5">
        <div className="flex items-center gap-2.5">
          <Layers className="size-5 text-brand-accent" aria-hidden="true" />
          <CardTitle className="text-lg sm:text-xl font-bold text-ink">
            {t("architecture.flow.title")}
          </CardTitle>
        </div>
        <p className="text-sm sm:text-base text-ink-muted leading-relaxed">
          {t("architecture.flow.subtitle")}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 rounded-control border border-line bg-surface p-1.5">
        <Button
          variant={perspective === "story" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("story")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Sparkles className="size-4 text-amber-500" />
          {t("architecture.flow.modeStory")}
        </Button>
        <Button
          variant={perspective === "tech" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("tech")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Zap className="size-4 text-brand-accent" />
          {t("architecture.flow.modeTech")}
        </Button>
        <Button
          variant={perspective === "table" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("table")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Table className="size-4 text-emerald-500" />
          {t("architecture.flow.modeTable")}
        </Button>
        <Button
          variant={perspective === "blueprint" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("blueprint")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Images className="size-4 text-blue-500" />
          {t("architecture.flow.modeBlueprint")}
        </Button>
        <Button
          variant={perspective === "topology" ? "flat" : "ghost"}
          size="sm"
          onClick={() => setPerspective("topology")}
          className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3"
        >
          <Network className="size-4 text-purple-500" />
          {t("architecture.flow.modeTopology")}
        </Button>
      </div>
    </CardHeader>
  );
}

function SimulationBar({
  selectedScenario,
  setSelectedScenario,
  isSimulating,
  runSimulation,
  resetSimulation,
  isZh,
  t,
}: Readonly<{
  selectedScenario: ScenarioKey;
  setSelectedScenario: (sc: ScenarioKey) => void;
  isSimulating: boolean;
  runSimulation: () => void;
  resetSimulation: () => void;
  isZh: boolean;
  t: (key: string) => string;
}>) {
  return (
    <div className="rounded-card border border-brand-border bg-surface-muted/40 p-5 shadow-elev-1">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-line/60 pb-3.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-sm font-semibold text-ink flex items-center gap-2">
            <Radio className="size-4 text-brand-accent animate-pulse" />
            {t("architecture.flow.sampleQueryLabel")}：
          </span>
          {(["rag", "react", "graph"] as ScenarioKey[]).map((scKey) => (
            <Button
              key={scKey}
              variant={selectedScenario === scKey ? "flat" : "secondary"}
              size="sm"
              onClick={() => setSelectedScenario(scKey)}
              disabled={isSimulating}
              className="gap-1.5 text-xs sm:text-sm font-medium py-1.5 px-3.5"
            >
              {t(`architecture.flow.scenarios.${scKey}.title`)}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-2.5 self-end sm:self-auto">
          <Button
            variant="default"
            size="sm"
            onClick={runSimulation}
            disabled={isSimulating}
            className="gap-2 text-xs sm:text-sm font-semibold py-2 px-4 shadow-sm"
          >
            <Play className="size-3.5" />
            {isSimulating ? t("architecture.flow.simulating") : t("architecture.flow.runSim")}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={resetSimulation}
            disabled={isSimulating}
            title={t("architecture.flow.resetSim")}
          >
            <RotateCcw className="size-4 text-ink-muted" />
          </Button>
        </div>
      </div>

      <div className="mt-4 flex items-start gap-3.5">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-control bg-brand-surface border border-brand-border text-brand-text">
          <User className="size-4.5" />
        </div>
        <div className="flex-1 space-y-1.5">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-ink-muted">
              {isZh ? "用户发送的问题" : "User Chat Input"}
            </span>
            <Badge variant="brand" size="xs" mono className="text-xs py-0.5 px-2 font-medium">
              {t(`architecture.flow.scenarios.${selectedScenario}.tag`)}
            </Badge>
          </div>
          <p className="text-base sm:text-lg font-medium text-ink bg-surface border border-line/60 rounded-control px-4 py-3 shadow-inner leading-relaxed">
            “{t(`architecture.flow.scenarios.${selectedScenario}.query`)}”
          </p>
        </div>
      </div>
    </div>
  );
}

function SimulationProgress({
  activeStepConfig,
  isZh,
  t,
}: Readonly<{
  activeStepConfig: StepConfig;
  isZh: boolean;
  t: (key: string) => string;
}>) {
  return (
    <div className="rounded-control border border-brand-accent/50 bg-brand-surface/80 p-4 shadow-elev-2 animate-in fade-in slide-in-from-top-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex size-3 rounded-full bg-brand-accent animate-ping" />
          <Badge variant="brand" size="sm" mono className="font-bold text-xs py-1 px-2.5">
            {t("architecture.flow.step")} {activeStepConfig.id} / 6
          </Badge>
          <span className="text-sm sm:text-base font-semibold text-ink">
            {isZh ? activeStepConfig.simStatusZh : activeStepConfig.simStatusEn}
          </span>
        </div>
        <Badge variant="neutral" size="sm" mono className="text-xs py-1 px-2.5">
          {t(`architecture.flow.stages.${activeStepConfig.stepKey}.badge`)}
        </Badge>
      </div>

      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface">
        <div
          className="h-full bg-brand-accent transition-all duration-700 ease-out"
          style={{ width: `${(activeStepConfig.id / 6) * 100}%` }}
        />
      </div>
    </div>
  );
}

function StepInspector({
  currentFocusedStep,
  isZh,
  t,
}: Readonly<{
  currentFocusedStep: StepConfig;
  isZh: boolean;
  t: (key: string) => string;
}>) {
  return (
    <div className="rounded-control border border-line bg-surface-muted/30 p-5 space-y-3.5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className={`flex size-7 items-center justify-center rounded-control ${currentFocusedStep.iconBg}`}>
            <currentFocusedStep.icon className="size-4" />
          </div>
          <span className="text-sm sm:text-base font-bold text-ink">
            {t("architecture.flow.step")} 0{currentFocusedStep.id} · {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.role`)}
          </span>
          <span className="text-xs sm:text-sm text-ink-muted font-mono">
            ({t(`architecture.flow.stages.${currentFocusedStep.stepKey}.techTitle`)})
          </span>
        </div>
        <Badge variant="neutral" size="sm" mono className="text-xs py-1 px-2.5">
          {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.badge`)}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
        <div className="space-y-2">
          <div className="font-semibold text-brand-text flex items-center gap-1.5 text-sm sm:text-base">
            <Sparkles className="size-4 text-amber-500" />
            {t("architecture.flow.explanation")}
          </div>
          <p className="text-ink-muted leading-relaxed text-sm sm:text-base">
            {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.storyDesc`)}
          </p>
          <p className="text-xs sm:text-sm text-ink-muted italic border-l-2 border-brand-border pl-2.5">
            💡 {isZh ? currentFocusedStep.analogyZh : currentFocusedStep.analogyEn}
          </p>
        </div>

        <div className="space-y-2">
          <div className="font-semibold text-brand-text flex items-center gap-1.5 text-sm sm:text-base">
            <Zap className="size-4 text-brand-accent" />
            {t("architecture.flow.techSpecification")}
          </div>
          <p className="text-ink-muted leading-relaxed font-mono text-xs sm:text-sm">
            {t(`architecture.flow.stages.${currentFocusedStep.stepKey}.techDesc`)}
          </p>
          <div className="flex flex-wrap gap-1.5 pt-1.5">
            {(isZh ? currentFocusedStep.keyPointsZh : currentFocusedStep.keyPointsEn).map((pt) => (
              <span
                key={pt}
                className="inline-flex items-center gap-1 text-xs text-ink-muted bg-surface border border-line rounded px-2 py-1"
              >
                <Check className="size-3 text-emerald-500" />
                {pt}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// NOSONAR
function AnswerShowcase({
  selectedScenario,
  isZh,
  t,
}: Readonly<{
  selectedScenario: ScenarioKey;
  isZh: boolean;
  t: (key: string) => string;
}>) {
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
          <div className="overflow-x-auto rounded-control border border-line bg-surface">
            <div className="bg-surface-muted/60 px-3.5 py-2 border-b border-line text-xs font-semibold text-ink flex items-center gap-1.5">
              <FileSpreadsheet className="size-3.5 text-brand-accent" />
              <span>{isZh ? "表 1：员工差旅住宿报销限额细则（摘自制度附表一）" : "Table 1: Employee Travel Lodging Cap Specifications (Policy Appendix A)"}</span>
            </div>
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-line bg-surface-muted/30 text-ink font-semibold">
                  <th className="p-2.5">{isZh ? "城市分类" : "City Tier"}</th>
                  <th className="p-2.5">{isZh ? "适用城市范畴" : "Covered Cities"}</th>
                  <th className="p-2.5">{isZh ? "研发报销上限" : "R&D Cap"}</th>
                  <th className="p-2.5">{isZh ? "凭证要求" : "Invoicing"}</th>
                  <th className="p-2.5">{isZh ? "审批权限" : "Approval Chain"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/40 text-ink-muted">
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "一线城市" : "Tier 1"}</td>
                  <td className="p-2.5">{isZh ? "北京、上海、广州、深圳" : "Beijing, Shanghai, Guangzhou, Shenzhen"}</td>
                  <td className="p-2.5 font-mono font-bold text-brand-text">¥500 / 人 / 天</td>
                  <td className="p-2.5">{isZh ? "增值税专用/普通发票" : "VAT Tax Invoice"}</td>
                  <td className="p-2.5">{isZh ? "部门总监审批" : "Director Approval"}</td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "新一线城市" : "New Tier 1"}</td>
                  <td className="p-2.5">{isZh ? "杭州、成都、武汉、南京等" : "Hangzhou, Chengdu, Wuhan, Nanjing"}</td>
                  <td className="p-2.5 font-mono font-bold text-ink">¥400 / 人 / 天</td>
                  <td className="p-2.5">{isZh ? "增值税专用/普通发票" : "VAT Tax Invoice"}</td>
                  <td className="p-2.5">{isZh ? "研发主管审批" : "Manager Approval"}</td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "二线及其他" : "Tier 2 & Other"}</td>
                  <td className="p-2.5">{isZh ? "其他省会及地级市" : "Other Regional Capitals"}</td>
                  <td className="p-2.5 font-mono text-ink">¥300 / 人 / 天</td>
                  <td className="p-2.5">{isZh ? "合规发票实报实销" : "Standard Invoices"}</td>
                  <td className="p-2.5">{isZh ? "项目经理审批" : "Project Lead Approval"}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {selectedScenario === "react" && (
          <div className="overflow-x-auto rounded-control border border-line bg-surface">
            <div className="bg-surface-muted/60 px-3.5 py-2 border-b border-line text-xs font-semibold text-ink flex items-center gap-1.5">
              <FileSpreadsheet className="size-3.5 text-brand-accent" />
              <span>{isZh ? "表 2：华东区月度销售业绩与环比增长分析表（数据沙箱精确计算）" : "Table 2: East Region Monthly Sales & MoM Growth Analysis (Sandbox Calculator)"}</span>
            </div>
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-line bg-surface-muted/30 text-ink font-semibold">
                  <th className="p-2.5">{isZh ? "统计月份" : "Month"}</th>
                  <th className="p-2.5">{isZh ? "销售额 (万元)" : "Revenue (10k RMB)"}</th>
                  <th className="p-2.5">{isZh ? "环比净增额" : "Net Growth"}</th>
                  <th className="p-2.5">{isZh ? "环比增长率 (%)" : "MoM Rate (%)"}</th>
                  <th className="p-2.5">{isZh ? "主要拉动行业" : "Leading Drivers"}</th>
                  <th className="p-2.5">{isZh ? "成交笔数" : "Orders"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/40 text-ink-muted">
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "前一月 (T-1)" : "Month T-1"}</td>
                  <td className="p-2.5 font-mono">210.0 万元</td>
                  <td className="p-2.5 font-mono">{isZh ? "基线月份" : "Baseline"}</td>
                  <td className="p-2.5 font-mono">-</td>
                  <td className="p-2.5">{isZh ? "传统制造 (52%)" : "Manufacturing (52%)"}</td>
                  <td className="p-2.5 font-mono">128 笔</td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "上月 (T)" : "Month T"}</td>
                  <td className="p-2.5 font-mono font-bold text-brand-text">245.8 万元</td>
                  <td className="p-2.5 font-mono text-emerald-600 font-bold">+35.8 万元</td>
                  <td className="p-2.5 font-mono text-emerald-600 font-bold">+17.05%</td>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "新能源 / 储能 (68%)" : "Clean Energy (68%)"}</td>
                  <td className="p-2.5 font-mono font-bold text-ink">164 笔</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {selectedScenario === "graph" && (
          <div className="overflow-x-auto rounded-control border border-line bg-surface">
            <div className="bg-surface-muted/60 px-3.5 py-2 border-b border-line text-xs font-semibold text-ink flex items-center gap-1.5">
              <FileSpreadsheet className="size-3.5 text-brand-accent" />
              <span>{isZh ? "表 3：Neo4j 图谱 2-Hop 关联关系推理表（Cypher 最短路径遍历）" : "Table 3: Neo4j Graph 2-Hop Relation Inference (Cypher Traversal)"}</span>
            </div>
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-line bg-surface-muted/30 text-ink font-semibold">
                  <th className="p-2.5">{isZh ? "起始实体" : "Source Entity"}</th>
                  <th className="p-2.5">{isZh ? "关系谓词 (Cypher)" : "Relationship"}</th>
                  <th className="p-2.5">{isZh ? "目标实体" : "Target Entity"}</th>
                  <th className="p-2.5">{isZh ? "协作职责说明" : "Role / Duty"}</th>
                  <th className="p-2.5">{isZh ? "置信度" : "Confidence"}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/40 text-ink-muted">
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "李工 (架构师)" : "Engineer Li (Architect)"}</td>
                  <td className="p-2.5 font-mono text-brand-text font-bold">[:MEMBER_OF]</td>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "AI平台四期项目" : "AI Platform Phase 4"}</td>
                  <td className="p-2.5">{isZh ? "担任核心架构师与技术负责" : "Core Tech Architect"}</td>
                  <td className="p-2.5 font-mono text-emerald-600 font-bold">1.00</td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "张总 (部门总监)" : "Director Zhang"}</td>
                  <td className="p-2.5 font-mono text-brand-text font-bold">[:DIRECTS]</td>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "AI平台四期项目" : "AI Platform Phase 4"}</td>
                  <td className="p-2.5">{isZh ? "担任项目总负责人兼资源审批人" : "Project Director"}</td>
                  <td className="p-2.5 font-mono text-emerald-600 font-bold">1.00</td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "李工" : "Engineer Li"}</td>
                  <td className="p-2.5 font-mono text-purple-600 font-bold">[:REPORTS_TO]</td>
                  <td className="p-2.5 font-medium text-ink">{isZh ? "张总" : "Director Zhang"}</td>
                  <td className="p-2.5">{isZh ? "项目内直属技术汇报关系" : "Direct Project Reporting Line"}</td>
                  <td className="p-2.5 font-mono text-emerald-600 font-bold">0.99</td>
                </tr>
              </tbody>
            </table>
          </div>
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

function PipelineSummaryStream({ isZh, t }: Readonly<{ isZh: boolean; t: (key: string) => string }>) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2.5 rounded-control border border-line bg-surface-muted/40 p-4 text-sm text-ink-muted">
      <span className="font-bold text-ink">{isZh ? "全链路流转：" : "Full Data Stream:"}</span>
      <span className="flex items-center gap-1.5 font-medium">
        <ShieldCheck className="size-3.5 text-blue-500" />
        {t("architecture.flow.stages.step1.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Workflow className="size-3.5 text-cyan-500" />
        {t("architecture.flow.stages.step2.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Search className="size-3.5 text-emerald-500" />
        {t("architecture.flow.stages.step3.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Wrench className="size-3.5 text-amber-500" />
        {t("architecture.flow.stages.step4.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-medium">
        <Sparkles className="size-3.5 text-purple-500" />
        {t("architecture.flow.stages.step5.role")}
      </span>
      <ArrowRight className="size-3.5 text-brand-accent" />
      <span className="flex items-center gap-1.5 font-bold text-brand-text">
        <CheckCircle2 className="size-3.5 text-rose-500" />
        {t("architecture.flow.stages.step6.role")}
      </span>
    </div>
  );
}

export function PipelineFlowDiagram() {
  const { t, i18n } = useTranslation();
  const isZh = i18n.language.startsWith("zh");

  const [perspective, setPerspective] = useState<ViewPerspective>("story");
  const [selectedScenario, setSelectedScenario] = useState<ScenarioKey>("rag");
  const [activeStepIndex, setActiveStepIndex] = useState<number | null>(null);
  const [focusedStepId, setFocusedStepId] = useState<number>(1);
  const [isSimulating, setIsSimulating] = useState(false);
  const [hasCompletedOnce, setHasCompletedOnce] = useState(false);

  const runSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setHasCompletedOnce(false);
    setActiveStepIndex(0);
    setFocusedStepId(1);

    let step = 0;
    const totalSteps = STEPS.length;

    const timer = setInterval(() => {
      step++;
      if (step < totalSteps) {
        setActiveStepIndex(step);
        setFocusedStepId(STEPS[step].id);
      } else {
        clearInterval(timer);
        setIsSimulating(false);
        setActiveStepIndex(null);
        setHasCompletedOnce(true);
      }
    }, 1100);
  };

  const resetSimulation = () => {
    setIsSimulating(false);
    setActiveStepIndex(null);
    setFocusedStepId(1);
    setHasCompletedOnce(false);
  };

  useEffect(() => {
    resetSimulation();
  }, [selectedScenario]);

  const activeStepConfig = useMemo(() => {
    if (activeStepIndex === null) return null;
    return STEPS[activeStepIndex] || null;
  }, [activeStepIndex]);

  const currentFocusedStep = useMemo(() => {
    return STEPS.find((s) => s.id === focusedStepId) || STEPS[0];
  }, [focusedStepId]);

  return (
    <Card className="overflow-hidden border-line shadow-elev-1 transition-all">
      <FlowHeader perspective={perspective} setPerspective={setPerspective} t={t} />

      <CardContent className="p-5 sm:p-6">
        {perspective === "blueprint" && <BlueprintView isZh={isZh} />}
        {perspective === "table" && <TableView isZh={isZh} t={t} />}
        {perspective === "topology" && <TopologyView t={t} />}

        {(perspective === "story" || perspective === "tech") && (
          <div className="space-y-7">
            <SimulationBar
              selectedScenario={selectedScenario}
              setSelectedScenario={setSelectedScenario}
              isSimulating={isSimulating}
              runSimulation={runSimulation}
              resetSimulation={resetSimulation}
              isZh={isZh}
              t={t}
            />

            {isSimulating && activeStepConfig && (
              <SimulationProgress activeStepConfig={activeStepConfig} isZh={isZh} t={t} />
            )}

            <div>
              <div className="mb-3.5 flex items-center justify-between text-sm text-ink-muted">
                <span className="font-semibold text-ink flex items-center gap-2 text-base">
                  <ArrowRight className="size-4 text-brand-accent" />
                  {isZh ? "AI 内部流转的 6 个执行阶段" : "6 Sequential Execution Phases Inside AI"}
                </span>
                <span className="text-xs text-ink-faint">
                  {t("architecture.flow.clickHint")}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {STEPS.map((stg) => {
                  const isCurrentActive = activeStepConfig?.id === stg.id;
                  const isPastCompleted =
                    isSimulating && activeStepConfig ? activeStepConfig.id > stg.id : false;
                  const isFocused = focusedStepId === stg.id;

                  return (
                    <StepCard
                      key={stg.id}
                      stg={stg}
                      isCurrentActive={isCurrentActive}
                      isPastCompleted={isPastCompleted}
                      hasCompletedOnce={hasCompletedOnce}
                      isFocused={isFocused}
                      perspective={perspective}
                      isZh={isZh}
                      onSelect={setFocusedStepId}
                      t={t}
                    />
                  );
                })}
              </div>
            </div>

            <StepInspector currentFocusedStep={currentFocusedStep} isZh={isZh} t={t} />
            <AnswerShowcase selectedScenario={selectedScenario} isZh={isZh} t={t} />
            <PipelineSummaryStream isZh={isZh} t={t} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
