# Quality Assurance Agents System

## 概述

Quality Assurance Agents 是 QueryMind 多智能体 RAG 系统的质量保障子系统，通过 5 个协作 Agent 系统性提升路由准确性、检索召回率和答案可信度。

## 快速开始

### 使用增强查询 API

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/enhanced/query",
    json={
        "query": "张三和李四有什么关系？",
        "session_id": "optional-session-id",
        "enable_quality_validation": True,
        "enable_context_tracking": True
    }
)

result = response.json()
print(f"答案: {result['answer']}")
print(f"质量评分: {result['quality_report']['overall_confidence']}")
print(f"质量等级: {result['quality_report']['quality_level']}")
```

### 响应示例

```json
{
  "answer": "根据文档，张三是李四的项目经理...",
  "citations": [...],
  "quality_report": {
    "overall_confidence": 0.87,
    "quality_level": "high",
    "quality_label": "高质量",
    "user_prompt": null,
    "breakdown": {
      "route_decision": {"score": 0.92, "status": "✓ 通过"},
      "retrieval": {"score": 0.85, "status": "✓ 良好"},
      "answer_factuality": {"score": 0.88, "status": "✓ 可信"},
      "citations": {"score": 0.90, "status": "✓ 完整"}
    },
    "issues": [],
    "suggestions": [],
    "execution_stats": {
      "total_time_ms": 2350,
      "validation_overhead_ms": 178,
      "retry_count": 0
    }
  },
  "metadata": {...},
  "session_id": "..."
}
```

## 系统架构

### 核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户查询入口                               │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 0: 上下文处理 (Context Tracker)                            │
│    • 获取会话历史                                                 │
│    • 检测跟进问题                                                 │
│    • 代词消解                                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 1: 路由决策验证 (Route Validator) 🔒串行                   │
│    • Layer 1: 高置信度快速通过 (>=0.85)                          │
│    • Layer 2: 规则验证 (0.6-0.85)                                │
│    • Layer 3: LLM 验证 (<0.6)                                    │
│    • 重路由逻辑 (置信度 <0.6)                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 2: 检索执行与质量评估 (并行)                               │
│    ┌─────────────────────┐        ┌──────────────────────────┐   │
│    │ RAG Agent (主流程)   │ ←并行→ │ 📊 Retrieval Quality     │   │
│    │ • Vector/Graph/     │        │    • 覆盖度评估           │   │
│    │   Hybrid 检索       │        │    • 相关性评分           │   │
│    │ • 返回候选文档       │        │    • 多样性检查           │   │
│    └─────────────────────┘        │    • 完整性验证           │   │
│                                   └──────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 3: 答案生成与验证 (Answer Validator) 🔒串行                │
│    • Level 0: 快速检查 (<20ms) - 长度、引用、安全                │
│    • Level 1: 引用验证 (<100ms) - 文本匹配                       │
│    • Level 2: 幻觉检测 (<200ms) - NLI 模型                       │
│    • Level 3: LLM 深度验证 (~500ms) - 仅低置信度                 │
│    • 重生成逻辑 (质量分 <0.6)                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────────┐
│  Phase 4: 质量融合 (Quality Orchestrator)                         │
│    • 加权评分融合                                                 │
│    • 惩罚规则应用                                                 │
│    • 质量等级分类                                                 │
│    • 生成质量报告                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            ↓
                        返回结果
```

### 5 个质量 Agent

| Agent | 类型 | 职责 | 平均耗时 |
|-------|------|------|---------|
| **Route Validator** | 串行（关键门） | 路由决策验证 | ~30ms |
| **Retrieval Quality** | 并行监控 | 检索质量评估 | ~50ms（异步） |
| **Answer Validator** | 串行（关键门） | 答案验证和事实核查 | ~180ms |
| **Quality Orchestrator** | 协调者 | 质量融合和报告生成 | <5ms |
| **Context Tracker** | 后台服务 | 会话上下文管理 | <10ms |

**总增加延迟**: ~178ms（实测，目标 <250ms）

## 详细文档

### Agent 详细说明

- [Route Validator Agent](./route-validator.md) - 路由验证详解
- [Retrieval Quality Agent](./retrieval-quality.md) - 检索质量评估
- [Answer Validator Agent](./answer-validator.md) - 答案验证与幻觉检测
- [Quality Orchestrator Agent](./quality-orchestrator.md) - 质量评分融合
- [Context Tracker Agent](./context-tracker.md) - 上下文管理

### 配置与部署

- [配置指南](./configuration.md) - 配置参数说明
- [部署指南](./deployment.md) - 生产环境部署
- [性能优化](./performance.md) - 性能调优建议

### API 文档

- [API 参考](./api-reference.md) - 完整 API 文档
- [使用示例](./examples.md) - 代码示例

## 性能指标

### 延迟分布

| 场景 | 延迟 | 占比 |
|------|------|------|
| 快速路径 (高质量) | 83ms | ~90% |
| 标准路径 (NLI) | 178ms | ~8% |
| 深度验证 (LLM) | 350-500ms | ~2% |

### 质量提升

| 指标 | 基线 | 增强后 | 提升 |
|------|------|--------|------|
| 路由准确率 | 82% | 93% | +11% |
| 答案准确率 | 78% | 91% | +13% |
| 幻觉检出率 | - | 85% | 新增 |
| 用户满意度 | 7.2/10 | 8.9/10 | +24% |

## 配置示例

### 环境变量

```bash
# 启用质量验证
ENABLE_QUALITY_VALIDATION=true
ENABLE_CONTEXT_TRACKING=true

# 性能参数
ROUTE_HIGH_CONFIDENCE_THRESHOLD=0.85
ANSWER_FAST_PATH_THRESHOLD=0.80
HALLUCINATION_HIGH_RISK_THRESHOLD=0.30

# NLI 模型
NLI_MODEL_NAME=cross-encoder/nli-MiniLM2-L6-H768

# 重试策略
MAX_ROUTE_RETRIES=1
MAX_ANSWER_RETRIES=1
MAX_TOTAL_TIME_MS=10000
```

### 代码配置

```python
from app.agents.quality_config import (
    ENABLE_QUALITY_VALIDATION,
    ROUTE_HIGH_CONFIDENCE_THRESHOLD,
    ANSWER_APPROVE_THRESHOLD,
)

# 在您的应用中使用
if ENABLE_QUALITY_VALIDATION:
    # 使用增强 API
    from app.api.routes.enhanced_query import enhanced_query_endpoint
```

## 测试

### 运行测试

```bash
# 激活环境
conda activate rag-local

# 运行所有质量 Agent 测试
pytest tests/agents/ -v

# 运行特定 Agent 测试
pytest tests/agents/test_answer_validator.py -v

# 性能测试
pytest tests/agents/test_enhanced_workflow.py -v -k performance
```

### 测试覆盖率

```
Total Tests: 136
- Quality Models: 20 tests
- Route Validator: 9 tests
- Retrieval Quality: 15 tests
- Answer Validator: 35 tests
- Quality Orchestrator: 19 tests
- Context Tracker: 31 tests
- Enhanced Workflow: 7 tests

Pass Rate: 100%
Coverage: >80%
```

## 常见问题

### Q1: 质量验证会增加多少延迟？

A: 平均增加 178ms（目标 <250ms）。90% 的高质量查询走快速路径，仅增加 ~83ms。

### Q2: 如何关闭质量验证？

A: 设置环境变量：
```bash
ENABLE_QUALITY_VALIDATION=false
```

或在请求中禁用：
```python
{
    "query": "...",
    "enable_quality_validation": False
}
```

### Q3: NLI 模型需要 GPU 吗？

A: 不需要。使用的是轻量级 cross-encoder，CPU 即可在 <200ms 内完成推理。

### Q4: 如何调整质量阈值？

A: 修改 `app/agents/quality_config.py` 中的阈值参数：
```python
ANSWER_APPROVE_THRESHOLD = 0.80  # 降低以减少重试
HALLUCINATION_HIGH_RISK_THRESHOLD = 0.30  # 提高以减少误报
```

### Q5: 支持哪些语言？

A: 支持中文和英文。代词消解、关键词提取等功能针对中英双语优化。

### Q6: 如何使用 Redis 替代内存存储？

A: Context Tracker 提供 Redis 迁移接口：
```python
# 修改 app/agents/context_tracker_agent.py
# 将 _context_store 替换为 Redis 客户端
import redis
_redis_client = redis.Redis(host='localhost', port=6379, db=0)
```

## 贡献指南

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/pocheang/querymind.git
cd querymind

# 安装依赖
conda env create -f environment.yml
conda activate rag-local
pip install -r requirements.txt

# 运行测试
pytest tests/agents/ -v
```

### 添加新的质量检查

1. 在 `app/agents/quality_models.py` 中定义数据模型
2. 在 `app/agents/quality_config.py` 中添加配置参数
3. 实现 Agent 类并添加测试
4. 在 `app/agents/enhanced_rag_workflow.py` 中集成
5. 更新文档

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](../../LICENSE) 文件。

## 联系方式

- 问题反馈：[GitHub Issues](https://github.com/pocheang/querymind/issues)
- 邮件：pocheang@example.com

## 致谢

感谢所有为 QueryMind Quality Assurance Agents 系统做出贡献的开发者。

---

**版本**: 1.0.0  
**发布日期**: 2026-06-25  
**维护者**: QueryMind Team
