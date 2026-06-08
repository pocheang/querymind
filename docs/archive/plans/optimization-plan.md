# RAG 系统智能化优化方案

## 🎯 优化目标
让系统更智能地理解用户意图，提供更准确的检索结果和回答。

---

## 📊 当前问题分析

### 1. 意图识别问题
- **现状**: 使用正则表达式匹配关键词
- **问题**: 
  - 容易误判（如"给我介绍"被判为闲聊）
  - 无法理解语义（"有哪些知识"和"介绍知识"意思相同但匹配不同）
  - 无法处理复杂句式
- **影响**: 用户体验差，检索不到相关内容

### 2. 检索质量问题
- **现状**: 直接用用户原始问题检索
- **问题**:
  - 口语化问题检索效果差
  - 缺少查询扩展
  - 向量检索和BM25权重固定
- **影响**: 检索召回率低，相关文档排名靠后

### 3. Agent分类问题
- **现状**: 基于关键词规则分类
- **问题**:
  - 跨领域问题无法处理
  - 置信度不明确
  - 无法学习和改进
- **影响**: 文档过滤不准确，遗漏相关内容

---

## 🔧 优化方案

### 阶段1：基础数据完善（1-2天）

#### 1.1 导入知识图谱
```bash
conda activate rag-local
python scripts/ingest.py
```
**预期效果**: 
- Neo4j中有实体和关系
- 图谱检索能返回结果
- 混合检索效果提升

#### 1.2 验证数据质量
```bash
python scripts/check_agent_labels.py
python scripts/eval_retrieval.py
```

---

### 阶段2：LLM驱动的意图识别（3-5天）

#### 2.1 实现智能意图分类器

**文件**: `app/services/llm_intent_classifier.py`

```python
from app.llm.ollama_client import get_ollama_client

def classify_intent_with_llm(question: str) -> dict:
    """
    使用LLM分类用户意图
    
    返回:
    {
        "intent": "information_query" | "casual_chat" | "task_request",
        "agent_class": "cybersecurity" | "artificial_intelligence" | "general",
        "confidence": 0.0-1.0,
        "reasoning": "分类理由"
    }
    """
    prompt = f"""分析以下用户问题的意图和领域分类。

用户问题: {question}

请判断:
1. 意图类型:
   - information_query: 查询信息、知识、文档
   - casual_chat: 闲聊、问候、感谢
   - task_request: 要求执行任务（分析、总结、生成等）

2. 领域分类:
   - cybersecurity: 网络安全、攻击防御、漏洞、威胁
   - artificial_intelligence: AI、机器学习、RAG、LLM
   - general: 通用或不明确

3. 置信度: 0.0-1.0

以JSON格式返回:
{{"intent": "...", "agent_class": "...", "confidence": 0.0, "reasoning": "..."}}
"""
    
    client = get_ollama_client()
    response = client.generate(
        model="qwen2.5:7b-instruct",
        prompt=prompt,
        options={"temperature": 0.1}
    )
    
    # 解析JSON响应
    import json
    result = json.loads(response["response"])
    return result
```

#### 2.2 混合策略（规则+LLM）

**文件**: `app/services/hybrid_intent_classifier.py`

```python
def classify_intent_hybrid(question: str) -> dict:
    """
    混合策略: 规则快速判断 + LLM精确分类
    """
    # 1. 快速规则判断明确的情况
    if is_obvious_greeting(question):
        return {"intent": "casual_chat", "confidence": 0.95}
    
    if is_obvious_task(question):
        return {"intent": "task_request", "confidence": 0.9}
    
    # 2. 不明确的情况用LLM
    if is_ambiguous(question):
        return classify_intent_with_llm(question)
    
    # 3. 默认用规则
    return classify_intent_by_rules(question)
```

**优点**:
- 快速响应（规则判断<1ms）
- 准确率高（LLM理解语义）
- 成本可控（只在必要时调用LLM）

---

### 阶段3：查询改写和扩展（5-7天）

#### 3.1 查询改写

**文件**: `app/services/query_rewriter.py`

```python
def rewrite_query_for_retrieval(question: str, agent_class: str) -> list[str]:
    """
    将口语化问题改写为适合检索的查询
    
    返回: [原始问题, 改写版本1, 改写版本2, ...]
    """
    prompt = f"""将以下用户问题改写为更适合文档检索的查询。

用户问题: {question}
领域: {agent_class}

要求:
1. 提取核心关键词
2. 扩展同义词和相关术语
3. 生成2-3个不同角度的查询

示例:
用户: "给我介绍一下有哪些知识"
改写:
- 知识库内容概览
- 文档分类和主题
- 可用的知识资源

以JSON数组返回: ["查询1", "查询2", "查询3"]
"""
    
    # 调用LLM生成
    queries = call_llm(prompt)
    return [question] + queries  # 保留原始问题
```

#### 3.2 多查询检索

```python
def multi_query_retrieval(queries: list[str], top_k: int = 5) -> list:
    """
    对多个查询分别检索，合并结果
    """
    all_results = []
    for query in queries:
        results = hybrid_search(query, top_k=top_k)
        all_results.extend(results)
    
    # 去重和重排序
    unique_results = deduplicate_by_source(all_results)
    reranked = rerank_results(unique_results, queries[0])
    return reranked[:top_k]
```

---

### 阶段4：自适应检索策略（7-10天）

#### 4.1 动态参数调整

**文件**: `app/services/adaptive_retrieval.py`

```python
def get_retrieval_params(question: str, agent_class: str) -> dict:
    """
    根据问题类型和领域动态调整检索参数
    """
    params = {
        "top_k": 5,
        "vector_weight": 0.5,
        "bm25_weight": 0.5,
        "rerank_top_n": 5,
        "similarity_threshold": 0.3
    }
    
    # 网络安全问题需要更多上下文
    if agent_class == "cybersecurity":
        params["top_k"] = 10
        params["similarity_threshold"] = 0.25
    
    # AI问题更精确
    elif agent_class == "artificial_intelligence":
        params["top_k"] = 5
        params["similarity_threshold"] = 0.4
        params["vector_weight"] = 0.7  # 更依赖语义
    
    # 复杂问题增加检索深度
    if is_complex_question(question):
        params["top_k"] *= 2
    
    return params
```

#### 4.2 检索质量评估

```python
def evaluate_retrieval_quality(question: str, results: list) -> dict:
    """
    评估检索结果质量
    """
    if not results:
        return {"quality": "poor", "action": "expand_search"}
    
    # 检查相似度分数
    avg_score = sum(r["score"] for r in results) / len(results)
    
    if avg_score < 0.3:
        return {"quality": "poor", "action": "rewrite_query"}
    elif avg_score < 0.5:
        return {"quality": "medium", "action": "add_web_search"}
    else:
        return {"quality": "good", "action": "proceed"}
```

---

### 阶段5：用户反馈闭环（10-14天）

#### 5.1 前端反馈按钮

**文件**: `frontend/src/pages/chat/components/FeedbackButtons.tsx`

```typescript
export function FeedbackButtons({ messageId, onFeedback }) {
  return (
    <div className="feedback-buttons">
      <button onClick={() => onFeedback('helpful')}>
        👍 有帮助
      </button>
      <button onClick={() => onFeedback('not_helpful')}>
        👎 没帮助
      </button>
      <button onClick={() => onFeedback('wrong_agent')}>
        🔄 分类错误
      </button>
    </div>
  );
}
```

#### 5.2 反馈数据收集

**文件**: `app/api/routes/feedback.py`

```python
@router.post("/feedback")
async def submit_feedback(
    message_id: str,
    feedback_type: str,
    correct_agent: str | None = None
):
    """
    收集用户反馈
    """
    feedback = {
        "message_id": message_id,
        "feedback_type": feedback_type,
        "correct_agent": correct_agent,
        "timestamp": datetime.now()
    }
    
    # 保存到数据库
    save_feedback(feedback)
    
    # 如果是分类错误，记录用于改进
    if feedback_type == "wrong_agent":
        log_misclassification(message_id, correct_agent)
    
    return {"status": "ok"}
```

#### 5.3 持续改进

```python
def analyze_feedback_and_improve():
    """
    分析反馈数据，改进分类规则
    """
    # 1. 找出高频误判的问题模式
    misclassifications = get_misclassification_patterns()
    
    # 2. 生成新的规则或调整LLM prompt
    for pattern in misclassifications:
        if pattern["count"] > 10:
            suggest_rule_improvement(pattern)
    
    # 3. A/B测试新规则
    deploy_rule_to_test_group(new_rules)
```

---

## 📈 预期效果

### 短期（1-2周）
- ✅ 意图识别准确率从 70% → 90%
- ✅ 检索召回率提升 30%
- ✅ 用户满意度提升

### 中期（1个月）
- ✅ 支持复杂多轮对话
- ✅ 自动学习和改进
- ✅ 跨领域问题处理能力

### 长期（2-3个月）
- ✅ 个性化推荐
- ✅ 主动知识发现
- ✅ 智能问题建议

---

## 🛠️ 实施建议

### 优先级排序
1. **P0 (必须做)**: 阶段1 - 数据完善
2. **P1 (高优先级)**: 阶段2 - LLM意图识别
3. **P2 (中优先级)**: 阶段3 - 查询改写
4. **P3 (低优先级)**: 阶段4、5 - 自适应和反馈

### 资源需求
- **开发时间**: 2-3周全职开发
- **计算资源**: Ollama本地运行，无额外成本
- **存储**: 反馈数据约10MB/月

### 风险控制
- **性能**: LLM调用增加延迟（缓存常见问题）
- **准确性**: 逐步灰度发布，A/B测试
- **成本**: 本地模型，无API费用

---

## 🎓 学习资源

- **查询改写**: HyDE (Hypothetical Document Embeddings)
- **多查询检索**: RAG-Fusion
- **自适应检索**: Self-RAG, Adaptive RAG
- **反馈学习**: RLHF for RAG

---

## 📝 下一步行动

1. **今天**: 运行 `python scripts/ingest.py` 导入图谱
2. **明天**: 实现 `llm_intent_classifier.py`
3. **本周**: 完成阶段2，测试效果
4. **下周**: 根据效果决定是否继续阶段3

需要我帮你实现哪个阶段？
