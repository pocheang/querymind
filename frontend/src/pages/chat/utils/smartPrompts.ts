import type { SessionMessage } from "@/types/api";

/**
 * 根据对话历史智能生成快速提示
 */
export function generateSmartPrompts(messages: SessionMessage[]): string[] {
  // 默认提示（当没有对话历史时）
  const defaultPrompts = [
    "介绍一下系统中有哪些网络安全知识",
    "解释一下人工智能的基本概念",
    "总结最新上传的 PDF 文档内容",
    "用 5 条要点汇报当前知识库状态",
  ];

  // 如果没有消息或只有一条消息，返回默认提示
  if (messages.length <= 1) {
    return defaultPrompts;
  }

  // 获取最近的对话（最多3轮）
  const recentMessages = messages.slice(-6); // 最近3轮对话（用户+助手）
  const lastUserMessage = recentMessages.filter(m => m.role === "user").pop();
  const lastAssistantMessage = recentMessages.filter(m => m.role === "assistant").pop();

  if (!lastUserMessage || !lastAssistantMessage) {
    return defaultPrompts;
  }

  const userQuestion = lastUserMessage.content.toLowerCase();
  const assistantAnswer = lastAssistantMessage.content.toLowerCase();
  const metadata = lastAssistantMessage.metadata;

  const prompts: string[] = [];

  // 1. 根据使用的agent类型推荐相关提示
  const agentClass = metadata?.agent_class || "";

  if (agentClass === "cybersecurity") {
    prompts.push("深入分析这个安全问题的攻击面和防护措施");
    prompts.push("给出具体的安全加固建议和实施步骤");
    prompts.push("分析相关的安全合规要求");
  } else if (agentClass === "artificial_intelligence") {
    prompts.push("详细解释这个AI概念的技术原理");
    prompts.push("给出实际应用场景和代码示例");
    prompts.push("对比不同的AI方法和优缺点");
  } else if (agentClass === "pdf_text") {
    prompts.push("提取文档中的关键数据和证据");
    prompts.push("总结文档的核心要点和结论");
    prompts.push("分析文档中的风险点和建议");
  }

  // 2. 根据问题类型推荐深入提示
  if (userQuestion.includes("什么") || userQuestion.includes("介绍") || userQuestion.includes("是什么")) {
    prompts.push("详细展开说明，包含具体案例");
    prompts.push("给出实际应用场景和最佳实践");
  } else if (userQuestion.includes("如何") || userQuestion.includes("怎么")) {
    prompts.push("给出详细的实施步骤和注意事项");
    prompts.push("提供具体的配置示例和代码");
  } else if (userQuestion.includes("对比") || userQuestion.includes("区别")) {
    prompts.push("制作详细的对比表格");
    prompts.push("分析各自的优缺点和适用场景");
  }

  // 3. 根据回答内容推荐后续提示
  if (assistantAnswer.includes("架构") || assistantAnswer.includes("architecture")) {
    prompts.push("详细说明各个组件的职责和交互");
    prompts.push("分析架构的优缺点和改进方向");
  }

  if (assistantAnswer.includes("风险") || assistantAnswer.includes("威胁") || assistantAnswer.includes("漏洞")) {
    prompts.push("给出具体的风险评估和处置建议");
    prompts.push("制定应急响应预案");
  }

  if (assistantAnswer.includes("模型") || assistantAnswer.includes("算法") || assistantAnswer.includes("训练")) {
    prompts.push("解释模型的数学原理和实现细节");
    prompts.push("给出模型调优和性能优化建议");
  }

  // 4. 根据引用证据推荐
  if (metadata?.citations && metadata.citations.length > 0) {
    prompts.push("展开引用的文档内容，提供更多细节");
    prompts.push("对比不同文档中的相关信息");
  }

  // 5. 根据图谱关系推荐
  if (metadata?.graph_result?.neighbors?.length > 0 || metadata?.graph_result?.paths?.length > 0) {
    prompts.push("深入分析相关实体之间的关系");
    prompts.push("探索更多相关的知识点");
  }

  // 6. 通用后续提示
  prompts.push("用表格形式总结关键信息");
  prompts.push("给出实际案例和应用建议");
  prompts.push("切换到其他模式重新分析这个问题");

  // 去重并返回前4个
  const uniquePrompts = Array.from(new Set(prompts));
  return uniquePrompts.slice(0, 4);
}

/**
 * 生成基于主题的快速提示
 */
export function generateTopicPrompts(topic: string): string[] {
  const topicLower = topic.toLowerCase();

  if (topicLower.includes("安全") || topicLower.includes("security")) {
    return [
      "分析这个安全问题的攻击链和影响范围",
      "给出分层防护方案和加固建议",
      "评估安全风险等级并制定处置计划",
      "总结相关的安全合规要求",
    ];
  }

  if (topicLower.includes("ai") || topicLower.includes("人工智能") || topicLower.includes("机器学习")) {
    return [
      "详细解释技术原理和数学基础",
      "给出代码实现和实际应用案例",
      "对比不同方法的优缺点",
      "分析性能优化和调优策略",
    ];
  }

  if (topicLower.includes("架构") || topicLower.includes("architecture")) {
    return [
      "详细说明各组件的职责和交互流程",
      "分析架构的优缺点和适用场景",
      "给出架构演进和优化建议",
      "对比其他架构方案",
    ];
  }

  return [
    "详细展开说明，包含具体案例",
    "给出实际应用场景和最佳实践",
    "用表格形式总结关键信息",
    "提供相关的参考资料和延伸阅读",
  ];
}
