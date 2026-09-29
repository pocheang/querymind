import type { SessionMessage } from "@/types/api";

/**
 * What to ask next, by the specialist that answered. A table rather than a
 * chain of `if` blocks with the same shape, which SonarCloud counted as
 * duplicated code.
 */
const FOLLOW_UPS: Record<string, { zh: string[]; en: string[] }> = {
  cybersecurity: {
    zh: ["这个漏洞在 CISA KEV 里吗？EPSS 概率是多少？", "对应的 ATT&CK 技术怎么检测和缓解？", "按优先级给出处置步骤"],
    en: [
      "Is this vulnerability in CISA KEV, and what is its EPSS probability?",
      "How is the matching ATT&CK technique detected and mitigated?",
      "Turn this into prioritised remediation steps",
    ],
  },
  artificial_intelligence: {
    zh: ["换成 INT4 量化再估算一次显存", "按 6ND 估算训练需要的算力和 GPU 时长", "说明这个估算没有计入哪些开销"],
    en: [
      "Estimate the memory again with INT4 quantization",
      "Estimate the training compute and GPU time with 6ND",
      "What does this estimate leave out?",
    ],
  },
  data_analysis: {
    zh: ["按其他维度再分组看一遍", "列出结果里的空值和异常值", "说明这个结果用了哪张表和哪条 SQL"],
    en: [
      "Break the same figure down by another dimension",
      "List the empty and outlying values in this result",
      "State which table and which SQL produced this result",
    ],
  },
  compliance: {
    zh: ["列出仍无法判断的条款和需要补充的材料", "按整改优先级给出行动计划", "对照另一部法规再审查一遍"],
    en: [
      "List the clauses that still cannot be judged and what material would settle them",
      "Turn the remediation into a prioritised action plan",
      "Review the same policy against another regulation",
    ],
  },
  pdf_text: {
    zh: ["这段内容在第几页、哪个章节？", "下一章讲了什么？", "把这一章的原文要点逐条列出"],
    en: [
      "Which page and section is this passage from?",
      "What does the next chapter say?",
      "List this chapter's points as they are written",
    ],
  },
};

function getAgentPrompts(agentClass: string, isZh: boolean): string[] {
  return FOLLOW_UPS[agentClass]?.[isZh ? "zh" : "en"] ?? [];
}

function getQuestionTypePrompts(userQuestion: string, isZh: boolean): string[] {
  if (
    userQuestion.includes("什么") ||
    userQuestion.includes("介绍") ||
    userQuestion.includes("what") ||
    userQuestion.includes("intro")
  ) {
    return isZh
      ? ["详细展开说明，包含具体案例", "给出实际应用场景和最佳实践"]
      : [
          "Elaborate with concrete examples and real-world scenarios",
          "Provide practical deployment patterns and best practices",
        ];
  }
  if (userQuestion.includes("如何") || userQuestion.includes("怎么") || userQuestion.includes("how")) {
    return isZh
      ? ["给出详细的实施步骤和注意事项", "提供具体的配置示例和代码"]
      : [
          "Provide a step-by-step rollout plan and cautionary notes",
          "Show specific configuration files and executable snippets",
        ];
  }
  if (
    userQuestion.includes("对比") ||
    userQuestion.includes("区别") ||
    userQuestion.includes("compare") ||
    userQuestion.includes("difference")
  ) {
    return isZh
      ? ["制作详细的对比表格", "分析各自的优缺点和适用场景"]
      : [
          "Structure a comprehensive comparison matrix table",
          "Evaluate advantages, pitfalls, and target scenarios for each option",
        ];
  }
  return [];
}

function getAnswerContentPrompts(assistantAnswer: string, isZh: boolean): string[] {
  const prompts: string[] = [];
  if (assistantAnswer.includes("架构") || assistantAnswer.includes("architecture")) {
    prompts.push(
      isZh ? "详细说明各个组件的职责和交互" : "Detail responsibilities and interaction protocols across components",
      isZh ? "分析架构的优缺点和改进方向" : "Critique architectural trade-offs and future evolutionary roadmaps"
    );
  }
  if (
    assistantAnswer.includes("风险") ||
    assistantAnswer.includes("threat") ||
    assistantAnswer.includes("vulnerability") ||
    assistantAnswer.includes("risk")
  ) {
    prompts.push(
      isZh ? "给出具体的风险评估和处置建议" : "Deliver a granular risk assessment and remediation priority list",
      isZh ? "制定应急响应预案" : "Draft an incident response runbook"
    );
  }
  if (assistantAnswer.includes("模型") || assistantAnswer.includes("model") || assistantAnswer.includes("algorithm")) {
    prompts.push(
      isZh ? "解释模型的数学原理和实现细节" : "Explain mathematical foundations and implementation nuances",
      isZh ? "给出模型调优和性能优化建议" : "Recommend hyperparameter tuning and latency optimization tips"
    );
  }
  return prompts;
}

function getMetadataPrompts(metadata: SessionMessage["metadata"], isZh: boolean): string[] {
  const prompts: string[] = [];
  if (metadata?.citations && metadata.citations.length > 0) {
    prompts.push(
      isZh ? "展开引用的文档内容，提供更多细节" : "Expand cited source excerpts with full contextual paragraphs",
      isZh ? "对比不同文档中的相关信息" : "Cross-verify cited findings across multiple ingested documents"
    );
  }
  if ((metadata?.graph_result?.neighbors?.length ?? 0) > 0 || (metadata?.graph_result?.paths?.length ?? 0) > 0) {
    prompts.push(
      isZh ? "深入分析相关实体之间的关系" : "Trace deeper topological graph relations across connected entities",
      isZh ? "探索更多相关的知识点" : "Explore adjacent knowledge nodes in the Neo4j graph"
    );
  }
  return prompts;
}

/**
 * What to ask first. Each specialist's starters are questions it answers with
 * its own tools and shape -- the acceptance questions it was built against --
 * and Auto (or the general analyst) shows one per specialist, so the first
 * screen says what the specialists are for. These replace starters that asked
 * the system to describe itself, which no specialist answers well.
 */
const STARTERS: Record<string, { zh: string[]; en: string[] }> = {
  cybersecurity: {
    zh: [
      "我们用的 log4j 2.14.1 受影响吗？怎么处置？",
      "T1190 怎么检测和缓解？",
      "CVE-2022-22965 的 CVSS 和 KEV 状态是什么？",
    ],
    en: [
      "Are we affected by log4j 2.14.1, and what should we do?",
      "How is T1190 detected and mitigated?",
      "What are the CVSS score and KEV status of CVE-2022-22965?",
    ],
  },
  artificial_intelligence: {
    zh: [
      "70B 模型 FP16 推理需要多少显存？",
      "7B 模型用 1T token 训练需要多少算力？",
      "LoRA 和全参数微调各有什么优缺点？",
    ],
    en: [
      "How much GPU memory does a 70B model need for FP16 inference?",
      "How much compute does training a 7B model on 1T tokens take?",
      "What are the trade-offs between LoRA and full fine-tuning?",
    ],
  },
  data_analysis: {
    zh: ["我上传的销售表里，各区域第三季度的销售额是多少？", "有哪些表格可以查询？", "按月份汇总销售额并排序"],
    en: [
      "In my sales table, what were each region's Q3 sales?",
      "Which tables can I query?",
      "Total the sales by month and sort them",
    ],
  },
  compliance: {
    zh: ["我们的数据保留制度符合个保法吗？", "个人信息保护法对跨境传输有什么要求？", "我们的制度还缺哪些 GDPR 条款？"],
    en: [
      "Does our data retention policy comply with PIPL?",
      "What does PIPL require for cross-border transfers?",
      "Which GDPR requirements does our policy not yet cover?",
    ],
  },
  pdf_text: {
    zh: ["这份合同第 3 章讲了什么？", "我上传的制度第 4 条原文是什么？", "这份报告的结论在哪一页？"],
    en: [
      "What does chapter 3 of this contract say?",
      "What is the exact text of section 4 of the policy I uploaded?",
      "Which page is this report's conclusion on?",
    ],
  },
};

const MIXED_STARTERS: Array<[string, number]> = [
  ["cybersecurity", 0],
  ["artificial_intelligence", 0],
  ["data_analysis", 0],
  ["compliance", 0],
];

export function starterPrompts(agentClassHint: string, isZh: boolean): string[] {
  const lang = isZh ? "zh" : "en";
  const own = STARTERS[agentClassHint];
  if (own) return own[lang];
  return MIXED_STARTERS.map(([agentClass, index]) => STARTERS[agentClass][lang][index]);
}

/**
 * 根据对话历史智能生成快速提示 (支持中英双语)
 */
export function generateSmartPrompts(messages: SessionMessage[], isZh = true, agentClassHint = ""): string[] {
  const defaultPrompts = starterPrompts(agentClassHint, isZh);

  // 如果没有消息或只有一条消息，返回默认提示
  if (messages.length <= 1) {
    return defaultPrompts;
  }

  // 获取最近的对话（最多3轮）
  const recentMessages = messages.slice(-6);
  const lastUserMessage = recentMessages.findLast((m) => m.role === "user");
  const lastAssistantMessage = recentMessages.findLast((m) => m.role === "assistant");

  if (!lastUserMessage || !lastAssistantMessage) {
    return defaultPrompts;
  }

  const userQuestion = lastUserMessage.content.toLowerCase();
  const assistantAnswer = lastAssistantMessage.content.toLowerCase();
  const metadata = lastAssistantMessage.metadata;

  const prompts: string[] = [
    ...getAgentPrompts(metadata?.agent_class || "", isZh),
    ...getQuestionTypePrompts(userQuestion, isZh),
    ...getAnswerContentPrompts(assistantAnswer, isZh),
    ...getMetadataPrompts(metadata, isZh),
    ...(isZh
      ? ["用表格形式总结关键信息", "给出实际案例和应用建议", "切换到其他模式重新分析这个问题"]
      : [
          "Tabulate the essential takeaways into a clean markdown table",
          "Provide practical industry benchmarks and implementation tips",
          "Re-evaluate this question using a different specialist",
        ]),
  ];

  // 去重并返回前4个
  const uniquePrompts = Array.from(new Set(prompts));
  return uniquePrompts.slice(0, 4);
}
