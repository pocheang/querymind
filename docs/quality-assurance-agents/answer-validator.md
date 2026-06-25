# Answer Validator Agent

## 概述

Answer Validator Agent 是质量保障系统中最关键的组件，负责验证生成答案的事实性和质量。采用四层渐进验证策略，结合 NLI 模型进行幻觉检测，确保答案的可信度。

## 四层验证流程

### Level 0: 快速检查 (<20ms)

**验证内容**:
1. **长度检查**: 答案是否过短 (<50 字符)
2. **引用检查**: 是否包含引用信息
3. **安全检查**: 是否包含敏感信息 (SSN、信用卡、密码等)

**决策**:
- 不通过 → 直接拒绝，返回 `action="regenerate"`
- 通过 → 进入 Level 1

```python
# 示例：检测到安全问题
answer = "用户密码是: password123"
result = await validate_answer(query, answer, source_docs, citations)
# result.action = "regenerate"
# result.issues = [AnswerIssue(type="safety", severity="critical")]
```

### Level 1: 引用一致性验证 (<100ms)

**验证逻辑**:
- 检查每个引用的 `doc_id` 是否在 `source_docs` 中
- 计算引用完整性分数 = 有效引用数 / 总引用数

**示例**:
```python
citations = [
    {"doc_id": "doc1"},
    {"doc_id": "doc2"},
    {"doc_id": "doc3"}  # 不存在于 source_docs
]

source_docs = [
    {"id": "doc1", "content": "..."},
    {"id": "doc2", "content": "..."}
]

# citation_completeness = 2/3 = 0.67
```

### Level 2: 幻觉检测 (<200ms) - NLI 模型

**使用场景**: 
- preliminary_score < 0.8 (不满足快速路径)
- preliminary_score >= 0.6 (不触发 Level 3)

**工作原理**:
1. 提取高风险事实性内容 (数字、日期、专有名词)
2. 使用 NLI (Natural Language Inference) 模型验证每个事实
3. 计算幻觉风险分数

**NLI 模型**: `cross-encoder/nli-MiniLM2-L6-H768`

**提取的高风险内容**:
- 数字和百分比: `\d+\.?\d*%?`
- 日期: `2024年3月15日`, `03/15/2024`
- 中文专有名词: 2+ 汉字组合
- 英文专有名词: 首字母大写的词组

**验证逻辑**:
```python
# 对每个事实性内容
for span in factual_spans:
    # 使用 NLI 模型检查是否被源文档支持
    entailment_score = nli_model.predict([
        (source_text, f"The document mentions: {span}")
    ])
    
    # entailment_score > 0.5 → 支持
    # entailment_score < 0.5 → 不支持 (可能是幻觉)
    if entailment_score < 0.5:
        unsupported_count += 1

hallucination_risk = unsupported_count / total_spans
```

**示例**:
```python
query = "公司的市场份额是多少？"
answer = "公司在 2025 年达到了 95% 的市场份额。"  # 具体数字
source_docs = [{"content": "公司市场份额持续增长"}]  # 模糊描述

result = await validate_answer(query, answer, source_docs, citations)
# result.validation_details.hallucination_risk > 0.5  # 高风险
# result.action = "flag" 或 "regenerate"
```

### Level 3: LLM 深度验证 (~500ms)

**触发条件**: preliminary_score < 0.6 (非常低的初步评分)

**验证方式**:
- 使用 LLM 深度分析答案与源文档的一致性
- 超时保护: 1 秒

**Prompt 模板**:
```
Verify if this answer is factually consistent with the source documents.

Query: {query}

Answer: {answer}

Source Documents:
{source_text}

Is the answer factually supported by the sources? Respond with:
FACTUAL: yes/no
CONFIDENCE: 0.0-1.0
ISSUES: brief list of any unsupported claims (if FACTUAL=no)
```

**使用场景**:
- 答案质量很差 (长度不足、无引用)
- 引用完整性很低 (<0.5)
- 前面的层级无法给出明确判断

## 五个验证维度

### 1. Factual Consistency (事实一致性)

**权重**: 40% (最重要)

**评分来源**:
- Level 2 NLI 检测: `1.0 - hallucination_risk`
- Level 3 LLM 验证: 直接返回置信度

### 2. Hallucination Risk (幻觉风险)

**定义**: 答案中包含源文档未支持的事实性内容的比例

**阈值**:
- < 0.15: 低风险 (绿色)
- 0.15-0.30: 中等风险 (黄色)
- > 0.30: 高风险 (红色) → 应用 0.7 惩罚系数

### 3. Citation Completeness (引用完整性)

**权重**: 25%

**计算**: 有效引用数 / 总引用数

**影响**:
- >= 0.8 → 可以走快速路径
- < 0.5 → 触发 "missing_citation" 问题

### 4. Answer Quality (答案质量)

**权重**: 15%

**评估维度**:
- 长度适中 (100-2000 字符)
- 结构完整 (多句话)
- 信息性强 (不是"不知道"之类的回答)

### 5. Safety Score (安全分数)

**权重**: 10%

**检查内容**:
- PII (个人身份信息): SSN, 信用卡号
- 密码泄露
- 其他敏感信息

## 决策逻辑

```python
# 计算综合分数
overall_score = (
    factual_consistency * 0.40 +
    citation_completeness * 0.25 +
    answer_quality * 0.15 +
    safety_score * 0.10
)

# 应用惩罚
if hallucination_risk > 0.30:
    overall_score *= 0.7  # 高幻觉风险惩罚

# 决策
if overall_score >= 0.80:
    action = "approve"  # 批准
elif overall_score >= 0.60:
    action = "flag"     # 标记但通过
else:
    action = "regenerate"  # 重新生成
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANSWER_FAST_PATH_THRESHOLD` | 0.80 | 快速路径阈值 |
| `ANSWER_STANDARD_PATH_THRESHOLD` | 0.60 | 标准路径阈值 |
| `ANSWER_APPROVE_THRESHOLD` | 0.80 | 批准阈值 |
| `ANSWER_FLAG_THRESHOLD` | 0.60 | 标记阈值 |
| `HALLUCINATION_HIGH_RISK_THRESHOLD` | 0.30 | 高幻觉风险阈值 |
| `NLI_MODEL_NAME` | `cross-encoder/nli-MiniLM2-L6-H768` | NLI 模型 |
| `NLI_MAX_CHECKS` | 5 | 最大 NLI 检查次数 |
| `ANSWER_VALIDATOR_TIMEOUT_MS` | 1000 | 超时时间 |

## 使用示例

### 基础用法

```python
from app.agents.answer_validator_agent import validate_answer

query = "张三的职位是什么？"
answer = "张三是高级软件工程师，负责后端开发。"
source_docs = [
    {"id": "doc1", "content": "张三是软件工程师"},
    {"id": "doc2", "content": "负责后端系统开发"}
]
citations = [{"doc_id": "doc1"}, {"doc_id": "doc2"}]

result = await validate_answer(query, answer, source_docs, citations)

print(f"是否有效: {result.is_valid}")
print(f"综合分数: {result.overall_score}")
print(f"决策: {result.action}")
print(f"事实一致性: {result.validation_details.factual_consistency}")
print(f"幻觉风险: {result.validation_details.hallucination_risk}")
print(f"引用完整性: {result.validation_details.citation_completeness}")
```

### 处理重生成

```python
result = await validate_answer(query, answer, source_docs, citations)

if result.action == "regenerate":
    # 需要重新生成答案
    print("答案质量不足，建议重新生成")
    
    # 查看具体问题
    for issue in result.issues:
        print(f"- [{issue.severity}] {issue.type}: {issue.suggestion}")
    
    # 使用更高温度重新生成
    new_answer = await synthesize_answer(
        query, source_docs,
        temperature=0.7,  # 增加多样性
        previous_issues=result.issues  # 告知之前的问题
    )
```

### 解读质量报告

```python
result = await validate_answer(query, answer, source_docs, citations)

# 检查验证方法
if result.validation_method == "fast_path":
    print("✅ 高质量答案，快速通过")
elif result.validation_method == "standard":
    print("⚠️ 使用 NLI 检测，发现一些问题")
elif result.validation_method == "deep":
    print("🔍 使用 LLM 深度验证，置信度较低")

# 检查幻觉风险
if result.validation_details.hallucination_risk > 0.3:
    print("⚠️ 高幻觉风险！建议人工审核")
```

## 性能优化

### 快速路径优化

**目标**: 90% 查询走快速路径 (<150ms)

**条件**:
```python
preliminary_score >= 0.80 and citation_score >= 0.8
```

**优化建议**:
1. 提高答案生成质量，减少需要 NLI 检测的案例
2. 确保引用完整性，让更多查询走快速路径
3. 调整 `ANSWER_FAST_PATH_THRESHOLD` 阈值

### NLI 模型优化

**性能**:
- CPU 推理: ~50-100ms per check
- GPU 推理: ~10-20ms per check

**优化策略**:
1. **限制检查次数**: `NLI_MAX_CHECKS = 5` (只检查前 5 个高风险事实)
2. **批量推理**: 一次性推理多个 span
3. **模型缓存**: Lazy loading，首次调用后缓存

```python
# NLI 模型懒加载
_nli_model = None

def _get_nli_model():
    global _nli_model
    if _nli_model is None:
        _nli_model = CrossEncoder(NLI_MODEL_NAME)
    return _nli_model
```

### 避免不必要的深度验证

```python
# ✅ 好的做法
if preliminary_score >= 0.6:
    # 使用 NLI 而非 LLM
    return await nli_validation()

# ❌ 坏的做法
# 总是使用最慢的 LLM 验证
return await llm_deep_validation()
```

## 测试

```bash
# 运行 Answer Validator 测试
pytest tests/agents/test_answer_validator.py -v

# 性能测试
pytest tests/agents/test_answer_validator.py -v -k performance

# 幻觉检测测试
pytest tests/agents/test_answer_validator.py::test_answer_validator_hallucination -v
```

## 常见问题

### Q: NLI 模型需要 GPU 吗？

A: 不需要。使用的是轻量级 cross-encoder，在 CPU 上也能快速推理（<100ms）。如果有 GPU 会自动使用。

### Q: 如何降低误报率？

A: 调整 NLI 阈值：
```python
# 在 _check_hallucination() 中
if entailment_score < 0.5:  # 默认阈值
    unsupported += 1

# 改为更宽松的阈值
if entailment_score < 0.3:  # 降低以减少误报
    unsupported += 1
```

### Q: 如何添加新的安全检查？

A: 在 `_quick_validation()` 中添加正则表达式：
```python
unsafe_patterns = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b\d{16}\b',             # Credit card
    r'your_new_pattern',       # 新增模式
]
```

### Q: 为什么有些答案被标记为幻觉但看起来没问题？

A: 可能原因：
1. NLI 模型对某些表述不敏感
2. 源文档表述与答案表述差异较大
3. 数字或专有名词提取不准确

建议：查看 `result.issues` 了解具体哪些内容被标记。

## 相关文档

- [Quality Orchestrator](./quality-orchestrator.md)
- [Enhanced RAG Workflow](./workflow.md)
- [配置指南](./configuration.md)
