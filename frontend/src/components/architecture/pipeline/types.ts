import React from "react";
import {
  CheckCircle2,
  Search,
  ShieldCheck,
  Sparkles,
  Workflow,
  Wrench,
} from "lucide-react";

export type ViewPerspective = "story" | "tech" | "table" | "blueprint" | "topology";
export type ScenarioKey = "rag" | "react" | "graph";

export interface StepConfig {
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

export const STEPS: StepConfig[] = [
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

export function getCardStateClass(isCurrentActive: boolean, isFocused: boolean): string {
  if (isCurrentActive) {
    return "border-brand-accent ring-2 ring-brand-accent/50 bg-surface shadow-elev-2 scale-[1.02]";
  }
  if (isFocused) {
    return "border-brand-border ring-1 ring-brand-border bg-surface shadow-elev-1";
  }
  return "border-line bg-surface hover:border-brand-border/80 hover:shadow-elev-1";
}

export type ScenarioTableRow = {
  id: string;
  cells: React.ReactNode[];
};
