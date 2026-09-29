import React from "react";
import { CheckCircle2, Search, ShieldCheck, Sparkles, Workflow, Wrench } from "lucide-react";

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
    analogyZh: "像档案室的核对员：先确认您能调阅哪些卷宗，再把敏感信息遮住",
    analogyEn: "Like a records clerk: checks which files you may read, then covers the sensitive details",
    simStatusZh: "权限与隐私：解析访问范围，把问题中的敏感信息换成占位符...",
    simStatusEn: "Permission & Privacy: resolving your access scope, tokenising sensitive values...",
    keyPointsZh: ["检索前先解析访问范围", "问题中的 PII 替换为占位符", "按意图筛查提示注入", "范围为空不等于全库"],
    keyPointsEn: [
      "Access Scope Resolved Before Retrieval",
      "PII in the Question Becomes Tokens",
      "Injection Screening by Intent",
      "An Empty Scope Is Not the Whole Corpus",
    ],
    inputZh: "已登录用户的提问与身份",
    inputEn: "A signed-in user's question and identity",
    outputZh: "脱敏后的问题 + 锁定的访问范围",
    outputEn: "Redacted question + locked access scope",
    securityZh: "权限与输出过滤是必经阶段，超时也不会被跳过",
    securityEn: "Permission and output filtering are mandatory stages; a timeout never skips them",
  },
  {
    id: 2,
    stepKey: "step2",
    icon: Workflow,
    colorRing: "border-cyan-500/50 shadow-cyan-500/10",
    badgeClass: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/30",
    iconBg: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-400",
    analogyZh: "像总服务台导医：看懂您的需求，安排对口的专家",
    analogyEn: "Like a triage desk: understands your request and sends it to the right specialist",
    simStatusZh: "路由：一次调用选定检索路由、领域专家和回答形态...",
    simStatusEn: "Router: one call chooses the retrieval route, the specialist and the answer shape...",
    keyPointsZh: [
      "一次调用：路由 + 专家 + 形态",
      "超时由关键词规则兜底",
      "按问题缓存路由决策",
      "5 位领域专家 + 通用分析",
    ],
    keyPointsEn: [
      "One Call: Route + Specialist + Shape",
      "Keyword Rules on Timeout",
      "Route Decisions Cached per Question",
      "5 Domain Specialists + General Analyst",
    ],
    inputZh: "脱敏后的提问（可附侧栏选定的专家）",
    inputEn: "Redacted question (and a specialist pinned in the sidebar, if any)",
    outputZh: "检索路由 + 领域专家 + 回答形态 + 理由",
    outputEn: "Retrieval route + specialist + answer shape + reason",
    securityZh: "侧栏指定的专家直接生效；超时时专家与工具仍保留",
    securityEn: "A pinned specialist applies directly; a timeout keeps the specialist and its tools",
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
    keyPointsZh: ["向量 + BM25 + 图谱 + Web", "按（来源, 查询）RRF 融合", "交叉编码器重排", "本领域文档重排后加分"],
    keyPointsEn: [
      "Vector + BM25 + Graph + Web",
      "RRF per (Source, Query)",
      "Cross-Encoder Reranking",
      "Own-Domain Boost After Reranking",
    ],
    inputZh: "分词优化查询与语义向量嵌入",
    inputEn: "Segmented query & semantic embedding vectors",
    outputZh: "Top-K 权威制度分块 (含 doc_id、页码、段落文本)",
    outputEn: "Top-K Grounded Chunks (with doc_id, page, text)",
    securityZh: "只在已授权范围内检索；领域加分只重排、不扩大范围",
    securityEn: "Searches only the authorised scope; the domain boost reorders and never widens",
  },
  {
    id: 4,
    stepKey: "step4",
    icon: Wrench,
    colorRing: "border-amber-500/50 shadow-amber-500/10",
    badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
    iconBg: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
    analogyZh: "像专科医生的检查仪器：只用本科室的设备，动刀之前先签字",
    analogyEn:
      "Like a specialist's own instruments: only the department's tools, and a signature before anything invasive",
    simStatusZh: "专家工具：在本领域只读工具中选择并执行，最多 3 步...",
    simStatusEn: "Specialist tools: choosing among the domain's read-only tools, up to 3 steps...",
    keyPointsZh: [
      "只提供本领域只读工具",
      "最多 3 步（TOOL_MAX_STEPS）",
      "选择工具时看不到检索内容",
      "写操作需单次审批令牌",
    ],
    keyPointsEn: [
      "Only the Domain's Read-only Tools",
      "Up to 3 Steps (TOOL_MAX_STEPS)",
      "Tool Choice Never Sees Retrieved Text",
      "Writes Need a Single-use Approval Token",
    ],
    inputZh: "提问 + 对话 + 本领域工具目录",
    inputEn: "Question + conversation + the domain's tool catalog",
    outputZh: "工具结果（可引用的编为 [T1]、[T2]）",
    outputEn: "Tool results (the citable ones become [T1], [T2])",
    securityZh: "证据盲选择；开放世界结果只回传 (id, 状态)；写操作需审批",
    securityEn: "Evidence-blind selection; open-world results return only (id, status); writes need approval",
  },
  {
    id: 5,
    stepKey: "step5",
    icon: Sparkles,
    colorRing: "border-purple-500/50 shadow-purple-500/10",
    badgeClass: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30",
    iconBg: "bg-purple-500/15 text-purple-600 dark:text-purple-400",
    analogyZh: "像论文作者：按专家的体例写，文献标 [1]，仪器读数标 [T1]",
    analogyEn:
      "Like a research author: writes in the specialist's format, sources marked [1], instrument readings [T1]",
    simStatusZh: "生成：按专家的回答形态撰写，证据与工具分别引用，SSE 流式推送草稿...",
    simStatusEn:
      "Synthesis: writing in the specialist's shape, evidence and tools cited apart, draft streamed over SSE...",
    keyPointsZh: ["证据标记 [E] → [1][2]", "工具标记 [T1]", "按专家的回答形态作答", "篇幅随证据"],
    keyPointsEn: [
      "Evidence Markers [E] → [1][2]",
      "Tool Markers [T1]",
      "Answer in the Specialist's Shape",
      "Length Follows the Evidence",
    ],
    inputZh: "提问 + 检索证据 + 工具结果 + 回答形态",
    inputEn: "Question + retrieved evidence + tool results + answer shape",
    outputZh: "带 [E{k}] 与 [T{k}] 标记的草稿",
    outputEn: "A draft carrying [E{k}] and [T{k}] markers",
    securityZh: "工具结果放在证据沙箱之外单独成段，不冒充文档引用",
    securityEn:
      "Tool results sit in their own section outside the evidence sandbox, never posing as document citations",
  },
  {
    id: 6,
    stepKey: "step6",
    icon: CheckCircle2,
    colorRing: "border-rose-500/50 shadow-rose-500/10",
    badgeClass: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30",
    iconBg: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
    analogyZh: "像终审编辑：逐句核对出处，不够就退回重查，最后遮住隐私",
    analogyEn:
      "Like a final editor: checks every sentence's source, sends it back once if thin, then covers private details",
    simStatusZh: "核验与输出：引用、蕴含与句子依据核对，必要时重试一次，输出脱敏...",
    simStatusEn:
      "Verify & output: citations, entailment and grounding checked, one retry if needed, output redacted...",
    keyPointsZh: ["引用与句子依据核对", "NLI 蕴含（跨文字时弃权）", "不达标时有界重试", "输出 DLP、工具来源列表"],
    keyPointsEn: [
      "Citation and Grounding Checks",
      "NLI Entailment (Abstains Across Scripts)",
      "Bounded Retry When It Falls Short",
      "Output DLP and the Tool Sources List",
    ],
    inputZh: "草稿答案 + 证据 + 工具结果",
    inputEn: "Draft answer + evidence + tool results",
    outputZh: "核验后的答案：[1][2] 引用、工具来源列表",
    outputEn: "Verified answer: [1][2] citations and a tool sources list",
    securityZh: "工具结论按工具输出核对；输出过滤是必经阶段",
    securityEn: "Tool facts are checked against the tool's output; output filtering is mandatory",
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
