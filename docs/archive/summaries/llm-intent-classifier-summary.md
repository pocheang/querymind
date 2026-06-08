# LLM意图分类器实现总结

## 完成时间
2025年（具体日期根据实际情况）

## 实现内容

### 1. 核心文件
- **app/services/llm_intent_classifier.py** - LLM意图分类器
  - 使用Ollama的qwen2.5:7b-instruct模型进行语义理解
  - 支持4种Agent类别：cybersecurity、artificial_intelligence、pdf_text、general
  - 包含后备规则分类器，确保鲁棒性
  - 返回分类结果、置信度和理由

- **app/agents/router_agent.py** - 路由Agent集成
  - 添加`use_llm_intent`参数（默认True）
  - 支持LLM分类和规则分类切换
  - 在reason字段中记录分类方法和置信度

- **scripts/test_intent_classifier.py** - 测试脚本
  - 对比LLM分类和规则分类的准确率
  - 包含11个测试用例，覆盖4种Agent类别

### 2. 测试结果

#### 准确率对比
- **LLM分类准确率**: 11/11 (100.0%)
- **规则分类准确率**: 7/11 (63.6%)
- **LLM改进**: +36.4%

#### 详细测试用例

| 问题 | 期望类别 | LLM分类 | 规则分类 | LLM正确 | 规则正确 |
|------|---------|---------|---------|---------|---------|
| 什么是SQL注入攻击？ | cybersecurity | ✓ cybersecurity | ✓ cybersecurity | ✓ | ✓ |
| 如何防护XSS漏洞？ | cybersecurity | ✓ cybersecurity | ✓ cybersecurity | ✓ | ✓ |
| 介绍一下零信任架构 | cybersecurity | ✓ cybersecurity | ✗ general | ✓ | ✗ |
| 什么是Transformer模型？ | artificial_intelligence | ✓ artificial_intelligence | ✗ general | ✓ | ✗ |
| 如何训练神经网络？ | artificial_intelligence | ✓ artificial_intelligence | ✓ artificial_intelligence | ✓ | ✓ |
| 介绍一下深度学习 | artificial_intelligence | ✓ artificial_intelligence | ✓ artificial_intelligence | ✓ | ✓ |
| 帮我读取这个PDF文档 | pdf_text | ✓ pdf_text | ✗ general | ✓ | ✗ |
| 分析这个PDF的内容 | pdf_text | ✓ pdf_text | ✗ general | ✓ | ✗ |
| 给我介绍一下有哪些知识 | general | ✓ general | ✓ general | ✓ | ✓ |
| 你好 | general | ✓ general | ✓ general | ✓ | ✓ |
| 今天天气怎么样 | general | ✓ general | ✓ general | ✓ | ✓ |

#### LLM分类优势
1. **语义理解能力强** - 能理解"零信任架构"属于网络安全领域
2. **上下文感知** - 能识别"Transformer模型"属于AI领域
3. **PDF识别准确** - 准确识别PDF相关操作
4. **置信度评估** - 提供0.0-1.0的置信度分数

### 3. 技术特点

#### Prompt设计
```
你是一个智能意图分类器。根据用户问题，判断应该使用哪个专业Agent来回答。

可用的Agent类别：
- cybersecurity: 网络安全、漏洞、攻击防护、安全策略、威胁情报
- artificial_intelligence: AI、机器学习、深度学习、神经网络、模型训练
- pdf_text: PDF文档阅读、文档分析、文本提取
- general: 通用知识、其他领域问题

请严格按照JSON格式输出，不要输出其他内容：
{"agent_class": "类别", "confidence": 0.9, "reason": "理由"}
```

#### 鲁棒性设计
1. **JSON解析容错** - 支持中文引号自动转换
2. **后备分类器** - LLM失败时自动降级到规则分类
3. **参数验证** - 验证agent_class有效性和confidence范围
4. **异常处理** - 完整的try-except和日志记录

#### 性能优化
1. **温度设置为0.0** - 确保分类结果稳定
2. **使用缓存的模型** - 通过get_chat_model()复用模型实例
3. **简洁的prompt** - 减少token消耗

### 4. 集成方式

#### 在router_agent中使用
```python
from app.agents.router_agent import decide_route

# 使用LLM意图分类（默认）
decision = decide_route(question="什么是SQL注入？", use_llm_intent=True)
# decision.agent_class = "cybersecurity"
# decision.reason包含 "method=llm(confidence=0.95)"

# 使用规则分类
decision = decide_route(question="什么是SQL注入？", use_llm_intent=False)
# decision.agent_class = "cybersecurity"
# decision.reason包含 "method=rule"
```

#### 直接调用分类器
```python
from app.services.llm_intent_classifier import classify_intent_with_llm

result = classify_intent_with_llm("什么是Transformer模型？")
# {
#     "agent_class": "artificial_intelligence",
#     "confidence": 0.95,
#     "reason": "问题涉及AI模型架构",
#     "method": "llm"
# }
```

### 5. 后续优化建议

#### 短期优化（已在OPTIMIZATION_PLAN.md中）
1. ✅ **LLM意图分类器** - 已完成
2. ⏳ **查询改写** - 使用LLM优化用户问题表述
3. ⏳ **自适应检索** - 根据置信度动态调整检索策略

#### 长期优化
1. **Few-shot学习** - 在prompt中添加示例提升准确率
2. **多模型集成** - 结合多个模型的分类结果
3. **在线学习** - 根据用户反馈持续优化分类器
4. **A/B测试** - 对比不同prompt和模型的效果

### 6. 数据导入状态

知识图谱数据已成功导入：
- ✅ 加载文档: 14个
- ✅ 索引chunks: 692个
- ✅ 写入三元组: 4451个

现在系统支持：
- 向量检索（Chroma）
- 图谱检索（Neo4j）
- LLM意图分类
- 自动文档过滤

## 测试方法

### 运行测试脚本
```bash
conda activate rag-local
python scripts/test_intent_classifier.py
```

### 在前端测试
1. 访问 http://localhost:5173
2. 输入测试问题：
   - "什么是SQL注入攻击？" → 应该路由到cybersecurity
   - "什么是Transformer模型？" → 应该路由到artificial_intelligence
   - "帮我读取这个PDF文档" → 应该路由到pdf_text
3. 查看响应中的reason字段，确认包含 "method=llm(confidence=X.XX)"

## 相关文件
- [app/services/llm_intent_classifier.py](../app/services/llm_intent_classifier.py)
- [app/agents/router_agent.py](../app/agents/router_agent.py)
- [scripts/test_intent_classifier.py](../scripts/test_intent_classifier.py)
- [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)
