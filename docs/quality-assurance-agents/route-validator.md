# Route Validator Agent

## 概述

Route Validator Agent 负责验证 Router Agent 的路由决策是否合理，采用三层渐进验证策略，确保 85% 以上的查询在 30ms 内完成验证。

## 验证流程

### Layer 1: 高置信度快速通过 (>=0.85)

**触发条件**: Router confidence >= 0.85

**处理逻辑**: 
- 直接通过，无需额外验证
- 执行时间: ~5ms
- 覆盖率: ~85% 查询

```python
if router_confidence >= 0.85:
    return RouteValidationResult(
        is_valid=True,
        confidence=router_confidence,
        validation_method="rule_fast",
        validation_reason="high_confidence_fast_pass"
    )
```

### Layer 2: 规则特征验证 (0.6-0.85)

**触发条件**: 0.6 <= Router confidence < 0.85

**验证维度**:
1. **查询特征匹配**
   - 关系查询关键词 → 应路由到 graph
   - 对比查询关键词 → 应使用 compare_entities skill
   - PDF 查询关键词 → 应使用 pdf_text_reader skill
   - 安全查询关键词 → 应路由到 cybersecurity agent class

2. **路由一致性检查**
   - 验证 route 是否在 VALID_ROUTES 中
   - 验证 skill 是否在 VALID_SKILLS 中
   - 验证 agent_class 与查询内容匹配

**执行时间**: ~30ms

**示例**:
```python
query = "张三和李四有什么关系？"
route_decision = RouteDecision(
    route="vector",  # ❌ 应该是 graph
    skill="answer_with_citations",
    confidence=0.75
)

result = await validate_route_decision(query, route_decision)
# result.is_valid = True (通过但有警告)
# result.warnings = ["query_has_relation_keywords_but_route_is_not_graph"]
```

### Layer 3: LLM 深度验证 (<0.6)

**触发条件**: Router confidence < 0.6

**验证方式**:
- 使用 LLM 判断路由决策的合理性
- 如果不合理，建议替代路由
- 执行时间: ~300-500ms
- 超时保护: 500ms

**Prompt 模板**:
```
Validate this routing decision for quality assurance.

Query: {query}

Routing Decision:
- Route: {route}
- Skill: {skill}
- Agent Class: {agent_class}
- Reason: {reason}

Is this routing decision appropriate? If not, suggest an alternative.

Respond in this format:
VALID: yes/no
CONFIDENCE: 0.0-1.0
REASON: brief explanation
ALTERNATIVE_ROUTE: route (if VALID=no)
ALTERNATIVE_SKILL: skill (if VALID=no)
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ROUTE_HIGH_CONFIDENCE_THRESHOLD` | 0.85 | Layer 1 快速通过阈值 |
| `ROUTE_MEDIUM_CONFIDENCE_THRESHOLD` | 0.60 | Layer 2 规则验证阈值 |
| `ROUTE_LOW_CONFIDENCE_THRESHOLD` | 0.40 | Layer 3 LLM 验证触发阈值 |
| `ROUTE_VALIDATOR_TIMEOUT_MS` | 500 | LLM 验证超时时间 |

## 返回结果

```python
RouteValidationResult(
    is_valid: bool,              # 是否有效
    confidence: float,           # 置信度 (0.0-1.0)
    validation_method: str,      # "rule_fast" | "rule_feature" | "llm"
    validation_reason: str,      # 验证原因
    execution_time_ms: int,      # 执行时间 (ms)
    suggested_alternative: Optional[Dict],  # 建议的替代路由
    warnings: List[str]          # 警告信息
)
```

## 使用示例

### 基础用法

```python
from app.agents.route_validator_agent import validate_route_decision
from app.agents.router_agent import RouteDecision

# 路由决策
route_decision = RouteDecision(
    route="vector",
    reason="general_query",
    skill="answer_with_citations",
    agent_class="general",
    confidence=0.92
)

# 验证
result = await validate_route_decision(
    query="什么是机器学习？",
    route_decision=route_decision
)

print(f"验证结果: {result.is_valid}")
print(f"置信度: {result.confidence}")
print(f"方法: {result.validation_method}")
print(f"耗时: {result.execution_time_ms}ms")
```

### 处理重路由

```python
result = await validate_route_decision(query, route_decision)

if not result.is_valid and result.suggested_alternative:
    # 使用建议的替代路由
    new_route = result.suggested_alternative["route"]
    new_skill = result.suggested_alternative["skill"]
    
    # 重新路由
    route_decision = RouteDecision(
        route=new_route,
        skill=new_skill,
        reason=f"route_validator_suggestion: {result.validation_reason}",
        confidence=result.confidence
    )
```

## 性能优化

### 快速路径优化

**目标**: 85% 查询 <30ms

**策略**:
1. **高置信度快速通过**: 直接返回，不做额外检查
2. **特征缓存**: 查询特征提取结果缓存
3. **规则预编译**: 关键词列表预加载到内存

### 避免不必要的 LLM 调用

```python
# ✅ 好的做法
if confidence >= 0.6:
    # 使用规则验证，避免 LLM
    return rule_based_validation()

# ❌ 坏的做法
# 总是调用 LLM
return llm_validation()
```

## 测试

```bash
# 运行 Route Validator 测试
pytest tests/agents/test_route_validator.py -v

# 性能测试
pytest tests/agents/test_route_validator.py::test_route_validator_high_confidence_fast_pass -v
```

## 常见问题

### Q: 如何调整快速路径阈值？

A: 修改 `quality_config.py`:
```python
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.80  # 降低以提高覆盖率
```

### Q: 如果 LLM 验证超时怎么办？

A: 自动降级到规则验证：
```python
try:
    result = await asyncio.wait_for(llm_validation(), timeout=0.5)
except asyncio.TimeoutError:
    # 自动降级
    result = rule_based_validation()
```

### Q: 如何添加新的验证规则？

A: 在 `_rule_based_validation()` 中添加：
```python
def _rule_based_validation(query, route_decision):
    features = _extract_query_features(query)
    
    # 添加新规则
    if features["has_xxx_keywords"]:
        if route_decision.route != "expected_route":
            issues.append("xxx_mismatch")
            confidence -= 0.3
    
    return {"confidence": confidence, "warnings": issues}
```

## 相关文档

- [Router Agent](../agents/router.md)
- [Quality Config](./configuration.md)
- [Enhanced RAG Workflow](./workflow.md)
