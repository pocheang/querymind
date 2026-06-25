# 质量保障 Agent 系统设计文档

**项目**: QueryMind 多智能体 RAG 系统  
**日期**: 2026-06-25  
**版本**: 1.0  
**作者**: AI Assistant  

---

## 1. 概述

### 1.1 设计目标

为 QueryMind 添加完整的质量保障体系，通过新增 5 个协作 Agent 系统性提升：
- **路由准确性** - 减少误路由导致的质量问题
- **检索召回率** - 提升相关文档的发现能力
- **答案可信度** - 确保事实准确性，降低幻觉风险
- **用户体验** - 提供透明的质量报告和置信度标注

### 1.2 核心原则

1. **混合模式** - 关键节点串行验证，非关键节点并行监控
2. **性能优先** - 规则优先 + LLM 兜底，平均增加延迟 < 250ms
3. **渐进验证** - 低风险快速通过，高风险深度检查
4. **可追溯性** - 每个环节都有质量评分和可视化报告

### 1.3 新增 Agent 概览

| Agent | 类型 | 职责 | 平均耗时 |
|-------|------|------|---------|
| **Route Validator** | 串行（关键门） | 路由决策验证 | ~30ms |
| **Retrieval Quality** | 并行监控 | 检索质量评估 | ~50ms（异步） |
| **Answer Validator** | 串行（关键门） | 答案验证和事实核查 | ~180ms |
| **Quality Orchestrator** | 协调者 | 质量融合和报告生成 | <5ms |
| **Context Tracker** | 后台服务 | 会话上下文管理 | <10ms |

**总增加延迟**: ~210ms（vs 无质量保障的基线）

---

## 2. 整体架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户查询入口                               │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 1: 路由决策 (关键门 - 串行验证)                            │
├───────────────────────────────────────────────────────────────────┤
│  Router Agent                                                     │
│    ↓                                                              │
│  🔒 Route Validator Agent (新增)                                 │
│    • 验证路由决策的合理性                                         │
│    • 置信度 < 0.6 → 触发重路由                                    │
│    • 输出：validated_route + confidence_score                    │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 2: 检索执行 (并行监控)                                      │
├───────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐        ┌──────────────────────────┐     │
│  │ Vector/Graph/Hybrid │ ←并行→ │ 📊 Retrieval Quality     │     │
│  │ RAG Agent (主流程)   │        │    Agent (新增)          │     │
│  │                     │        │  • 评估检索质量           │     │
│  │ 返回候选文档         │        │  • 计算覆盖度/相关性      │     │
│  └─────────────────────┘        │  • 输出质量分数           │     │
│                                 └──────────────────────────┘     │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 3: 答案生成 (关键门 - 串行验证)                            │
├───────────────────────────────────────────────────────────────────┤
│  Synthesis Agent                                                  │
│    ↓                                                              │
│  🔒 Answer Validator Agent (新增)                                │
│    • 事实一致性检查                                               │
│    • 幻觉检测                                                     │
│    • 引用完整性验证                                               │
│    • 不通过 → 标注低质量 OR 触发重生成                            │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 4: 质量融合与输出                                           │
├───────────────────────────────────────────────────────────────────┤
│  🎯 Quality Orchestrator Agent (新增)                             │
│    • 融合所有质量评估结果                                         │
│    • 计算综合置信度                                               │
│    • 生成质量报告                                                 │
│    • 决策是否需要人工审核提示                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  后台持续服务                                                      │
├───────────────────────────────────────────────────────────────────┤
│  💬 Context Tracker Agent (新增)                                  │
│    • 维护多轮对话上下文                                           │
│    • 跟踪用户意图变化                                             │
│    • 提供上下文相关的路由建议                                     │
└───────────────────────────────────────────────────────────────────┘
```

### 2.2 关键设计原则

1. **关键节点串行验证** - 路由决策和答案质量是成败关键
2. **非关键并行监控** - 检索质量评估不阻塞主流程
3. **动态回退机制** - 低置信度触发重试，而非直接失败
4. **质量可追溯** - 每个环节都有质量分数

---

## 3. Agent 详细设计

### 3.1 Route Validator Agent

**职责**: 验证 Router Agent 的决策是否合理

**快速验证流程（分层决策）**:

```python
# 第一层：规则快速校验（<10ms）
if router_confidence >= 0.85:
    return pass  # 85% 查询走这条路

# 第二层：特征匹配（<50ms）
rule_score = rule_based_validation(query_features, router_decision)
if rule_score >= 0.8:
    return pass  # 10% 查询

# 第三层：LLM 验证（仅低置信度，~300ms）
if router_confidence < 0.6:
    return llm_validation()  # 5% 查询
```

**性能**: 平均 ~30ms

### 3.2 Retrieval Quality Agent

**职责**: 并行评估检索结果质量

**评估维度**:
1. 覆盖度 - 关键概念覆盖
2. 相关性 - Top-K 平均分数
3. 多样性 - 来源多样性
4. 完整性 - 上下文完整性

**实现**: 全部异步并行，使用轻量统计指标

**性能**: ~50ms（异步，对主流程延迟 ≈0）

### 3.3 Answer Validator Agent

**职责**: 验证答案事实性和质量

**多级验证流程**:

```python
# Level 0: 快速筛选（<20ms，规则）
quick_check()  # 长度、引用、敏感词

# Level 1: 引用一致性（<100ms，文本匹配）
citation_validation()  # 90% 走快速路径

# Level 2: 幻觉检测（<200ms，轻量 NLI）
hallucination_check()  # 仅检查高风险内容

# Level 3: LLM 深度验证（<10% 查询，~500ms）
llm_deep_validation()  # 仅低置信度
```

**性能**: 平均 ~180ms

### 3.4 Quality Orchestrator Agent

**职责**: 融合所有质量评估，生成综合报告

**融合算法**:
```python
weights = {
    "route_confidence": 0.15,
    "retrieval_quality": 0.25,
    "answer_factuality": 0.40,  # 最重要
    "answer_quality": 0.15,
    "citation_completeness": 0.05
}

overall = weighted_sum(scores, weights)

# 惩罚项
if hallucination_risk > 0.3:
    overall *= 0.7
```

**质量分级**:
- ≥0.85: 高质量（绿色）
- 0.70-0.85: 中等质量（黄色）
- 0.50-0.70: 低质量（橙色）
- <0.50: 极低质量（红色，需人工审核）

**性能': <5ms

### 3.5 Context Tracker Agent

**职责**: 维护多轮对话状态

**核心功能**:
1. 增量更新对话历史（最近 10 轮）
2. 实体提及统计
3. 代词消解和查询重写
4. 异步生成上下文摘要

**性能**: 增量更新 <5ms，上下文提示 <10ms

---

## 4. 数据模型

### 4.1 核心模型定义

```python
class RouteValidationResult(BaseModel):
    is_valid: bool
    confidence: float
    validation_method: Literal["rule_fast", "rule_feature", "llm", "cache"]
    validation_reason: str
    execution_time_ms: int
    suggested_alternative: Optional[Dict]
    warnings: List[str]

class RetrievalQualityResult(BaseModel):
    overall_quality: float
    metrics: RetrievalQualityMetrics
    execution_time_ms: int
    issues: List[str]
    suggestions: List[str]

class AnswerValidationResult(BaseModel):
    is_valid: bool
    overall_score: float
    validation_details: AnswerValidationDetails
    issues: List[AnswerIssue]
    action: Literal["approve", "flag", "regenerate"]
    execution_time_ms: int
    validation_method: Literal["fast_path", "standard", "deep"]

class QualityReport(BaseModel):
    overall_confidence: float
    quality_level: Literal["high", "medium", "low", "very_low"]
    quality_label: str
    user_prompt: Optional[str]
    breakdown: QualityBreakdown
    issues: List[Dict]
    suggestions: List[str]
    execution_stats: ExecutionStats
```

---

## 5. 回退与重试机制

### 5.1 触发条件

```python
# Route Validator 触发重路由
if route_confidence < 0.6 and route_retry_count < 1:
    use_suggested_alternative()

# Answer Validator 触发重生成
if answer_score < 0.6 and answer_retry_count < 1:
    regenerate_with_higher_temperature()
```

### 5.2 降级策略

```
降级层级：
1. hybrid → vector（减少 Graph RAG 开销）
2. vector + rerank → vector only（跳过重排序）
3. LLM 验证 → 规则验证（跳过 LLM 调用）
4. 完整答案 → 简短摘要（减少生成 tokens）
5. 最终降级 → 返回检索结果 + 错误提示
```

---

## 6. 集成方案

### 6.1 主工作流集成

```python
class EnhancedRAGWorkflow:
    async def execute_query(query, session_id, user_id):
        # Phase 0: 上下文处理
        context_hints = get_context_aware_routing_hints(session_id, query)
        query_resolved = resolve_query_with_context(query, context_hints)
        
        # Phase 1: 路由决策与验证
        route_decision = decide_route(query_resolved)
        route_validation = await validate_route_decision(query_resolved, route_decision)
        
        # 重路由逻辑
        if not route_validation.is_valid and retry_count < 1:
            route_decision = route_validation.suggested_alternative
        
        # Phase 2: 检索执行（并行质量评估）
        retrieval_result = await execute_retrieval(query_resolved, route_decision)
        quality_eval_task = asyncio.create_task(
            evaluate_retrieval_quality(query_resolved, retrieval_result)
        )
        
        # Phase 3: 答案生成与验证
        answer = await synthesize_answer(query_resolved, retrieval_result)
        answer_validation = await validate_answer(query_resolved, answer, retrieval_result)
        
        # 重生成逻辑
        if answer_validation.action == "regenerate" and retry_count < 1:
            answer = await synthesize_answer(..., temperature=0.7)
        
        # Phase 4: 质量融合
        retrieval_quality = await quality_eval_task
        quality_report = orchestrate_quality(
            route_validation,
            retrieval_quality,
            answer_validation,
            execution_metadata
        )
        
        # Phase 5: 更新上下文
        await update_conversation_context(session_id, query, answer)
        
        return {
            "answer": answer,
            "quality_report": quality_report,
            "metadata": {...}
        }
```

### 6.2 配置管理

**全局开关**:
```python
ENABLE_QUALITY_VALIDATION = True  # 启用质量验证
ENABLE_CONTEXT_TRACKING = True    # 启用上下文追踪
MAX_ROUTE_RETRIES = 1              # 最大路由重试
MAX_ANSWER_RETRIES = 1             # 最大答案重试
MAX_TOTAL_TIME_MS = 10000          # 全局超时
```

**性能阈值**:
```python
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.85
ANSWER_FAST_PATH_THRESHOLD = 0.80
HALLUCINATION_HIGH_RISK_THRESHOLD = 0.30
```

---

## 7. API 接口

### 7.1 增强查询接口

```python
POST /api/v1/enhanced/query

Request:
{
    "query": "张三和李四有什么关系？",
    "session_id": "optional-uuid",
    "agent_class_hint": "optional",
    "enable_quality_validation": true,
    "enable_context_tracking": true
}

Response:
{
    "answer": "...",
    "citations": [...],
    "quality_report": {
        "overall_confidence": 0.87,
        "quality_level": "high",
        "breakdown": {...},
        "issues": [],
        "suggestions": [],
        "execution_stats": {
            "total_time_ms": 2500,
            "validation_overhead_ms": 210,
            "retry_count": 0
        }
    },
    "metadata": {...},
    "session_id": "..."
}
```

---

## 8. 性能优化总结

| 优化策略 | 效果 | 应用 Agent |
|---------|------|-----------|
| **规则优先** | 减少 80% LLM 调用 | Route Validator |
| **分层决策** | 快速路径 <30ms | Route Validator |
| **异步并行** | 零额外延迟 | Retrieval Quality |
| **采样检查** | 减少 60% 计算 | Retrieval Quality |
| **快速路径** | 90% 走快速通道 | Answer Validator |
| **轻量 NLI** | 替代大模型调用 | Answer Validator |
| **增量更新** | <10ms 上下文处理 | Context Tracker |

**总体性能**:
- 基线系统平均耗时: ~2000ms
- 增强系统平均耗时: ~2210ms
- **增加延迟: ~210ms (+10.5%)**
- **准确率提升: 预计 +15-25%**

---

## 9. 部署计划

### 9.1 文件结构

```
app/agents/
├── quality_models.py              # 数据模型定义
├── route_validator_agent.py       # 路由验证器
├── retrieval_quality_agent.py     # 检索质量评估器
├── answer_validator_agent.py      # 答案验证器
├── quality_orchestrator_agent.py  # 质量编排器
├── context_tracker_agent.py       # 上下文追踪器
├── enhanced_rag_workflow.py       # 增强工作流
└── quality_config.py              # 配置文件

app/api/routes/
└── enhanced_query.py              # API 接口

tests/
└── test_quality_agents.py         # 单元测试
```

### 9.2 依赖项

```python
# 新增依赖
sentence-transformers==2.5.0       # NLI 模型
redis==5.0.0                       # 上下文缓存（可选）
```

### 9.3 环境变量

```bash
ENABLE_QUALITY_VALIDATION=true
ENABLE_CONTEXT_TRACKING=true
MAX_ROUTE_RETRIES=1
MAX_ANSWER_RETRIES=1
NLI_MODEL_NAME=cross-encoder/nli-MiniLM2-L6-H768
REDIS_URL=redis://localhost:6379/0
```

---

## 10. 测试策略

### 10.1 单元测试

- 每个 Agent 独立测试
- 覆盖所有决策分支
- Mock LLM 调用以保证速度

### 10.2 集成测试

- 端到端工作流测试
- 回退和重试机制验证
- 性能基准测试

### 10.3 A/B 测试

- 对比基线系统和增强系统
- 指标: 准确率、召回率、F1、用户满意度
- 性能: P50/P95/P99 延迟

---

## 11. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 验证延迟过高 | 用户体验下降 | 分层决策、快速路径、异步执行 |
| 误判导致过度重试 | 浪费资源 | 限制重试次数、提高验证准确性 |
| LLM 调用成本 | 运营成本增加 | 规则优先、缓存、轻量模型 |
| 复杂度增加 | 维护困难 | 清晰的模块划分、完善文档 |

---

## 12. 后续扩展

### 12.1 短期（1-2 周）
- 实现核心 5 个 Agent
- 完成基础集成测试
- 部署到测试环境

### 12.2 中期（1-2 个月）
- 收集用户反馈，优化阈值
- 添加质量分析仪表板
- 实现自适应策略

### 12.3 长期（3-6 个月）
- 基于反馈的持续学习
- 迁移到方案 B（自适应架构）
- 多模态内容验证

---

## 13. 总结

本设计方案通过新增 5 个协作 Agent，构建了完整的质量保障体系：

✅ **平衡性能与质量** - 平均增加延迟仅 210ms，预计准确率提升 15-25%  
✅ **混合验证模式** - 关键节点串行，非关键并行，灵活高效  
✅ **渐进式验证** - 90% 查询走快速路径，资源利用率高  
✅ **可扩展架构** - 后续可平滑升级到自适应智能架构  

该方案已充分考虑性能、准确性和可维护性，适合在 QueryMind 系统中落地实施。
