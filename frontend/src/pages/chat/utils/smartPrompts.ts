import type { SessionMessage } from "@/types/api";

/**
 * 根据对话历史智能生成快速提示 (支持中英双语)
 */
export function generateSmartPrompts(messages: SessionMessage[], isZh = true): string[] {
  // 默认提示（当没有对话历史时）
  const defaultPrompts = isZh
    ? [
        "介绍一下系统中有哪些网络安全知识",
        "解释一下人工智能的基本概念",
        "总结最新上传的 PDF 文档内容",
        "用 5 条要点汇报当前知识库状态",
      ]
    : [
        "What cybersecurity capabilities are available in this system?",
        "Explain the fundamental concepts of artificial intelligence",
        "Summarize the key takeaways from the latest uploaded PDF",
        "Provide an executive summary of current knowledge base status in 5 points",
      ];

  // 如果没有消息或只有一条消息，返回默认提示
  if (messages.length <= 1) {
    return defaultPrompts;
  }

  // 获取最近的对话（最多3轮）
  const recentMessages = messages.slice(-6); // 最近3轮对话（用户+助手）
  const lastUserMessage = recentMessages.findLast((m) => m.role === "user");
  const lastAssistantMessage = recentMessages.findLast((m) => m.role === "assistant");

  if (!lastUserMessage || !lastAssistantMessage) {
    return defaultPrompts;
  }

  const userQuestion = lastUserMessage.content.toLowerCase();
  const assistantAnswer = lastAssistantMessage.content.toLowerCase();
  const metadata = lastAssistantMessage.metadata;

  const prompts: string[] = [];

  // 1. 根据使用的 agent 类型推荐相关提示
  const agentClass = metadata?.agent_class || "";

  if (agentClass === "cybersecurity") {
    prompts.push(
      isZh ? "深入分析这个安全问题的攻击面和防护措施" : "Analyze attack surfaces and mitigation strategies for this security issue",
      isZh ? "给出具体的安全加固建议和实施步骤" : "Provide concrete security hardening recommendations and action steps",
      isZh ? "分析相关的安全合规要求" : "Assess relevant regulatory and compliance requirements"
    );
  } else if (agentClass === "artificial_intelligence") {
    prompts.push(
      isZh ? "详细解释这个AI概念的技术原理" : "Explain the underlying technical principles of this AI concept",
      isZh ? "给出实际应用场景和代码示例" : "Provide production use cases and implementation code examples",
      isZh ? "对比不同的AI方法和优缺点" : "Compare alternative AI methodologies, pros, and trade-offs"
    );
  } else if (agentClass === "pdf_text") {
    prompts.push(
      isZh ? "提取文档中的关键数据和证据" : "Extract key empirical figures and evidence citations from the document",
      isZh ? "总结文档的核心要点和结论" : "Summarize core findings and conclusions from this document",
      isZh ? "分析文档中的风险点和建议" : "Analyze potential vulnerabilities, risk points, and recommendations"
    );
  }

  // 2. 根据问题类型推荐深入提示
  if (userQuestion.includes("什么") || userQuestion.includes("介绍") || userQuestion.includes("what") || userQuestion.includes("intro")) {
    prompts.push(
      isZh ? "详细展开说明，包含具体案例" : "Elaborate with concrete examples and real-world scenarios",
      isZh ? "给出实际应用场景和最佳实践" : "Provide practical deployment patterns and best practices"
    );
  } else if (userQuestion.includes("如何") || userQuestion.includes("怎么") || userQuestion.includes("how")) {
    prompts.push(
      isZh ? "给出详细的实施步骤和注意事项" : "Provide a step-by-step rollout plan and cautionary notes",
      isZh ? "提供具体的配置示例和代码" : "Show specific configuration files and executable snippets"
    );
  } else if (userQuestion.includes("对比") || userQuestion.includes("区别") || userQuestion.includes("compare") || userQuestion.includes("difference")) {
    prompts.push(
      isZh ? "制作详细的对比表格" : "Structure a comprehensive comparison matrix table",
      isZh ? "分析各自的优缺点和适用场景" : "Evaluate advantages, pitfalls, and target scenarios for each option"
    );
  }

  // 3. 根据回答内容推荐后续提示
  if (assistantAnswer.includes("架构") || assistantAnswer.includes("architecture")) {
    prompts.push(
      isZh ? "详细说明各个组件的职责和交互" : "Detail responsibilities and interaction protocols across components",
      isZh ? "分析架构的优缺点和改进方向" : "Critique architectural trade-offs and future evolutionary roadmaps"
    );
  }

  if (assistantAnswer.includes("风险") || assistantAnswer.includes("threat") || assistantAnswer.includes("vulnerability") || assistantAnswer.includes("risk")) {
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

  // 4. 根据引用证据推荐
  if (metadata?.citations && metadata.citations.length > 0) {
    prompts.push(
      isZh ? "展开引用的文档内容，提供更多细节" : "Expand cited source excerpts with full contextual paragraphs",
      isZh ? "对比不同文档中的相关信息" : "Cross-verify cited findings across multiple ingested documents"
    );
  }

  // 5. 根据图谱关系推荐
  if ((metadata?.graph_result?.neighbors?.length ?? 0) > 0 || (metadata?.graph_result?.paths?.length ?? 0) > 0) {
    prompts.push(
      isZh ? "深入分析相关实体之间的关系" : "Trace deeper topological graph relations across connected entities",
      isZh ? "探索更多相关的知识点" : "Explore adjacent knowledge nodes in the Neo4j graph"
    );
  }

  // 6. 通用后续提示
  prompts.push(
    isZh ? "用表格形式总结关键信息" : "Tabulate the essential takeaways into a clean markdown table",
    isZh ? "给出实际案例和应用建议" : "Provide practical industry benchmarks and implementation tips",
    isZh ? "切换到其他模式重新分析这个问题" : "Re-evaluate this question using a different specialized agent mode"
  );

  // 去重并返回前4个
  const uniquePrompts = Array.from(new Set(prompts));
  return uniquePrompts.slice(0, 4);
}

/**
 * 生成基于主题的快速提示 (支持中英双语)
 */
export function generateTopicPrompts(topic: string, isZh = true): string[] {
  const topicLower = topic.toLowerCase();

  if (topicLower.includes("安全") || topicLower.includes("security")) {
    return isZh
      ? [
          "分析这个安全问题的攻击链和影响范围",
          "给出分层防护方案和加固建议",
          "评估安全风险等级并制定处置计划",
          "总结相关的安全合规要求",
        ]
      : [
          "Analyze the kill chain and blast radius for this security alert",
          "Propose a defense-in-depth security hardening plan",
          "Score risk severity and construct a triage roadmap",
          "Summarize applicable compliance standards and mandates",
        ];
  }

  if (topicLower.includes("ai") || topicLower.includes("人工智能") || topicLower.includes("machine learning")) {
    return isZh
      ? [
          "详细解释技术原理和数学基础",
          "给出代码实现和实际应用案例",
          "对比不同方法的优缺点",
          "分析性能优化和调优策略",
        ]
      : [
          "Explain technical foundations and mathematical formulations",
          "Provide reference code implementation and enterprise use cases",
          "Compare architectural paradigms, pros, and trade-offs",
          "Outline throughput optimization and latency reduction methods",
        ];
  }

  if (topicLower.includes("架构") || topicLower.includes("architecture")) {
    return isZh
      ? [
          "详细说明各组件的职责和交互流程",
          "分析架构的优缺点和适用场景",
          "给出架构演进和优化建议",
          "对比其他架构方案",
        ]
      : [
          "Detail component responsibilities and end-to-end data flows",
          "Analyze architectural trade-offs and recommended scale",
          "Provide architecture evolution guidelines and roadmap",
          "Benchmark against alternative distributed RAG topologies",
        ];
  }

  return isZh
    ? [
        "详细展开说明，包含具体案例",
        "给出实际应用场景和最佳实践",
        "用表格形式总结关键信息",
        "提供相关的参考资料和延伸阅读",
      ]
    : [
        "Elaborate in detail with practical real-world examples",
        "Provide recommended deployment patterns and best practices",
        "Synthesize key insights into a structured markdown table",
        "Suggest relevant reference papers and further reading",
      ];
}
