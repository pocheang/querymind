# 配置指南

## 概述

本文档详细说明 Quality Assurance Agents 系统的所有配置参数。

## 配置文件

所有配置参数集中在 `app/agents/quality_config.py`。

## 全局开关

### ENABLE_QUALITY_VALIDATION

**类型**: `bool`  
**默认值**: `True`  
**说明**: 是否启用质量验证系统

```python
# 禁用所有质量验证（开发/测试环境）
ENABLE_QUALITY_VALIDATION = False
```

### ENABLE_CONTEXT_TRACKING

**类型**: `bool`  
**默认值**: `True`  
**说明**: 是否启用上下文跟踪（多轮对话）

### ENABLE_VERBOSE_LOGGING

**类型**: `bool`  
**默认值**: `False`  
**说明**: 是否启用详细日志（调试用）

---

## Route Validator 配置

### 置信度阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ROUTE_HIGH_CONFIDENCE_THRESHOLD` | 0.85 | Layer 1 快速通过阈值 |
| `ROUTE_MEDIUM_CONFIDENCE_THRESHOLD` | 0.60 | Layer 2 规则验证阈值 |
| `ROUTE_LOW_CONFIDENCE_THRESHOLD` | 0.40 | Layer 3 LLM 验证触发阈值 |

**调优建议**:
- **提高 Layer 1 阈值** (0.90): 更严格，更多查询走 Layer 2
- **降低 Layer 1 阈值** (0.80): 更宽松，更多查询快速通过

### 性能参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ROUTE_VALIDATOR_TIMEOUT_MS` | 500 | LLM 验证超时时间 (ms) |
| `ROUTE_VALIDATOR_USE_CACHE` | True | 是否使用缓存 |
| `ROUTE_VALIDATOR_CACHE_TTL` | 3600 | 缓存 TTL (秒) |

---

## Retrieval Quality 配置

### 评分权重

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RETRIEVAL_WEIGHT_COVERAGE` | 0.30 | 覆盖度权重 |
| `RETRIEVAL_WEIGHT_RELEVANCE` | 0.40 | 相关性权重 |
| `RETRIEVAL_WEIGHT_DIVERSITY` | 0.15 | 多样性权重 |
| `RETRIEVAL_WEIGHT_COMPLETENESS` | 0.15 | 完整性权重 |

**权重总和必须为 1.0**

### 质量阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RETRIEVAL_QUALITY_GOOD_THRESHOLD` | 0.70 | 良好阈值 |
| `RETRIEVAL_QUALITY_POOR_THRESHOLD` | 0.50 | 较差阈值 |

### 性能参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `RETRIEVAL_SAMPLE_TOP_K` | 3 | 采样检查的 Top-K 数量 |
| `RETRIEVAL_QUALITY_TIMEOUT_MS` | 200 | 超时时间 (ms) |

---

## Answer Validator 配置

### 路径阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANSWER_FAST_PATH_THRESHOLD` | 0.80 | 快速路径阈值 |
| `ANSWER_STANDARD_PATH_THRESHOLD` | 0.60 | 标准路径阈值 |

**优化建议**:
```python
# 更多查询走快速路径（降低延迟）
ANSWER_FAST_PATH_THRESHOLD = 0.75

# 更严格验证（提高质量）
ANSWER_FAST_PATH_THRESHOLD = 0.85
```

### 评分权重

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANSWER_WEIGHT_FACTUALITY` | 0.40 | 事实性权重（最重要） |
| `ANSWER_WEIGHT_CITATION` | 0.25 | 引用完整性权重 |
| `ANSWER_WEIGHT_QUALITY` | 0.25 | 答案质量权重 |
| `ANSWER_WEIGHT_SAFETY` | 0.10 | 安全性权重 |

### 幻觉检测

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `HALLUCINATION_HIGH_RISK_THRESHOLD` | 0.30 | 高风险阈值 |
| `HALLUCINATION_MEDIUM_RISK_THRESHOLD` | 0.15 | 中等风险阈值 |

**调整建议**:
```python
# 更严格（减少幻觉）
HALLUCINATION_HIGH_RISK_THRESHOLD = 0.20

# 更宽松（减少误报）
HALLUCINATION_HIGH_RISK_THRESHOLD = 0.40
```

### 决策阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANSWER_APPROVE_THRESHOLD` | 0.80 | 批准阈值 |
| `ANSWER_FLAG_THRESHOLD` | 0.60 | 标记阈值 |

**决策逻辑**:
- `>= 0.80`: approve (批准)
- `0.60 - 0.80`: flag (标记但通过)
- `< 0.60`: regenerate (重新生成)

### NLI 模型配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `NLI_MODEL_NAME` | `cross-encoder/nli-MiniLM2-L6-H768` | NLI 模型名称 |
| `NLI_MAX_CHECKS` | 5 | 最大检查次数 |

**替代模型**:
```python
# 更快但精度稍低
NLI_MODEL_NAME = "cross-encoder/nli-deberta-base"

# 更准确但更慢
NLI_MODEL_NAME = "cross-encoder/nli-deberta-v3-large"
```

### 性能参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ANSWER_VALIDATOR_TIMEOUT_MS` | 1000 | 超时时间 (ms) |

---

## Quality Orchestrator 配置

### 融合权重

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `QUALITY_WEIGHT_ROUTE` | 0.15 | 路由决策权重 |
| `QUALITY_WEIGHT_RETRIEVAL` | 0.25 | 检索质量权重 |
| `QUALITY_WEIGHT_ANSWER_FACT` | 0.40 | 答案事实性权重 |
| `QUALITY_WEIGHT_ANSWER_QUALITY` | 0.15 | 答案质量权重 |
| `QUALITY_WEIGHT_CITATION` | 0.05 | 引用完整性权重 |

**权重总和必须为 1.0**

### 质量分级

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `QUALITY_HIGH_THRESHOLD` | 0.85 | 高质量阈值 |
| `QUALITY_MEDIUM_THRESHOLD` | 0.70 | 中等质量阈值 |
| `QUALITY_LOW_THRESHOLD` | 0.50 | 低质量阈值 |

**分级规则**:
- `>= 0.85`: high (高质量)
- `0.70 - 0.85`: medium (中等质量)
- `0.50 - 0.70`: low (低质量)
- `< 0.50`: very_low (极低质量)

---

## Context Tracker 配置

### 历史管理

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CONTEXT_MAX_HISTORY_TURNS` | 10 | 最大保存轮次 |
| `CONTEXT_SUMMARY_FREQUENCY` | 5 | 生成摘要频率 |
| `CONTEXT_SUMMARY_MIN_TURNS` | 3 | 生成摘要最小轮次 |
| `CONTEXT_TTL_SECONDS` | 3600 | 上下文 TTL (秒) |

**调整建议**:
```python
# 更长的对话历史（消耗更多内存）
CONTEXT_MAX_HISTORY_TURNS = 20

# 更频繁的摘要（更好的上下文理解）
CONTEXT_SUMMARY_FREQUENCY = 3
```

---

## 重试策略配置

### 重试限制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_ROUTE_RETRIES` | 1 | 最大路由重试次数 |
| `MAX_ANSWER_RETRIES` | 1 | 最大答案重试次数 |
| `MAX_TOTAL_RETRIES` | 2 | 最大总重试次数 |
| `MAX_TOTAL_TIME_MS` | 10000 | 最大总执行时间 (ms) |

**注意**: 设置过高的重试次数会显著增加延迟

---

## 性能监控配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `PERF_THRESHOLD_FAST` | 2000 | 快速阈值 (ms) |
| `PERF_THRESHOLD_MEDIUM` | 5000 | 中等阈值 (ms) |
| `PERF_THRESHOLD_SLOW` | 8000 | 慢速阈值 (ms) |
| `ENABLE_PERFORMANCE_LOGGING` | True | 是否启用性能日志 |

---

## 降级配置

### 路由降级映射

```python
FALLBACK_ROUTE_MAP = {
    "hybrid": "vector",   # hybrid 失败 → vector
    "graph": "vector",    # graph 失败 → vector
    "react": "vector"     # react 失败 → vector
}
```

### 自动降级开关

```python
ENABLE_AUTO_FALLBACK = True  # 启用自动降级
```

---

## 环境变量

### 通过环境变量覆盖配置

```bash
# .env 文件
ENABLE_QUALITY_VALIDATION=true
ROUTE_HIGH_CONFIDENCE_THRESHOLD=0.85
ANSWER_FAST_PATH_THRESHOLD=0.80
NLI_MODEL_NAME=cross-encoder/nli-MiniLM2-L6-H768
MAX_ROUTE_RETRIES=1
MAX_ANSWER_RETRIES=1
```

### 在代码中读取环境变量

```python
import os
from typing import Final

ENABLE_QUALITY_VALIDATION: Final[bool] = os.getenv(
    "ENABLE_QUALITY_VALIDATION", "true"
).lower() == "true"

ROUTE_HIGH_CONFIDENCE_THRESHOLD: Final[float] = float(
    os.getenv("ROUTE_HIGH_CONFIDENCE_THRESHOLD", "0.85")
)
```

---

## 配置场景示例

### 场景 1: 开发环境（速度优先）

```python
# 快速开发，牺牲部分质量
ENABLE_QUALITY_VALIDATION = False  # 禁用质量验证
ENABLE_CONTEXT_TRACKING = False    # 禁用上下文跟踪
ENABLE_VERBOSE_LOGGING = True      # 启用详细日志
```

### 场景 2: 生产环境（平衡）

```python
# 默认配置（已优化平衡）
ENABLE_QUALITY_VALIDATION = True
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.85
ANSWER_FAST_PATH_THRESHOLD = 0.80
MAX_ROUTE_RETRIES = 1
MAX_ANSWER_RETRIES = 1
```

### 场景 3: 高质量模式（质量优先）

```python
# 最严格验证，可接受更高延迟
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.90  # 更严格
ANSWER_FAST_PATH_THRESHOLD = 0.85       # 更严格
HALLUCINATION_HIGH_RISK_THRESHOLD = 0.20  # 更严格
MAX_ROUTE_RETRIES = 2                   # 更多重试
MAX_ANSWER_RETRIES = 2
```

### 场景 4: 快速模式（速度优先）

```python
# 最快响应，部分牺牲质量
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.75  # 更宽松
ANSWER_FAST_PATH_THRESHOLD = 0.70       # 更宽松
MAX_ROUTE_RETRIES = 0                   # 不重试
MAX_ANSWER_RETRIES = 0
NLI_MAX_CHECKS = 3                      # 减少 NLI 检查
```

---

## 性能调优建议

### 降低延迟

1. **降低阈值**，让更多查询走快速路径
2. **减少重试次数**
3. **减少 NLI 检查次数** (`NLI_MAX_CHECKS`)
4. **使用更快的 NLI 模型**

```python
# 优化示例
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.80  # ↓
ANSWER_FAST_PATH_THRESHOLD = 0.75       # ↓
NLI_MAX_CHECKS = 3                      # ↓
MAX_ROUTE_RETRIES = 0                   # ↓
```

### 提高质量

1. **提高阈值**，触发更多深度验证
2. **增加重试机会**
3. **使用更准确的 NLI 模型**
4. **降低幻觉风险阈值**

```python
# 优化示例
ROUTE_HIGH_CONFIDENCE_THRESHOLD = 0.90  # ↑
ANSWER_FAST_PATH_THRESHOLD = 0.85       # ↑
HALLUCINATION_HIGH_RISK_THRESHOLD = 0.20  # ↓
MAX_ANSWER_RETRIES = 2                  # ↑
```

### 平衡调优

根据实际监控数据调整：

```python
# 监控指标
- 平均延迟: target <250ms
- 快速路径占比: target >90%
- 重试率: target <5%
- 用户满意度: target >8.5/10

# 如果延迟过高
# → 降低阈值或减少重试

# 如果质量不足
# → 提高阈值或增加验证步骤
```

---

## 配置验证

### 运行验证脚本

```python
# scripts/validate_config.py
from app.agents.quality_config import *

def validate_config():
    """验证配置一致性"""
    
    # 检查权重总和
    retrieval_weights = (
        RETRIEVAL_WEIGHT_COVERAGE +
        RETRIEVAL_WEIGHT_RELEVANCE +
        RETRIEVAL_WEIGHT_DIVERSITY +
        RETRIEVAL_WEIGHT_COMPLETENESS
    )
    assert abs(retrieval_weights - 1.0) < 0.01, "Retrieval weights must sum to 1.0"
    
    answer_weights = (
        ANSWER_WEIGHT_FACTUALITY +
        ANSWER_WEIGHT_CITATION +
        ANSWER_WEIGHT_QUALITY +
        ANSWER_WEIGHT_SAFETY
    )
    assert abs(answer_weights - 1.0) < 0.01, "Answer weights must sum to 1.0"
    
    quality_weights = (
        QUALITY_WEIGHT_ROUTE +
        QUALITY_WEIGHT_RETRIEVAL +
        QUALITY_WEIGHT_ANSWER_FACT +
        QUALITY_WEIGHT_ANSWER_QUALITY +
        QUALITY_WEIGHT_CITATION
    )
    assert abs(quality_weights - 1.0) < 0.01, "Quality weights must sum to 1.0"
    
    # 检查阈值范围
    assert 0.0 <= ROUTE_HIGH_CONFIDENCE_THRESHOLD <= 1.0
    assert 0.0 <= ANSWER_FAST_PATH_THRESHOLD <= 1.0
    
    print("✅ 配置验证通过")

if __name__ == "__main__":
    validate_config()
```

---

## 相关文档

- [系统架构](./README.md)
- [API 使用指南](./api-reference.md)
- [性能优化](./performance.md)
- [部署指南](./deployment.md)
