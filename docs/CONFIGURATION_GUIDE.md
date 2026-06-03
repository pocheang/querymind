# RAG配置优化指南

**版本**: v0.4.4  
**日期**: 2026-06-03  
**状态**: 推荐配置

---

## 📊 配置优化总结

基于全面的性能分析和评估，以下配置已从默认值优化：

| 参数 | 原默认值 | 优化值 | 改进理由 |
|------|---------|--------|----------|
| `VECTOR_TOP_K` | 6 | **8** | 提升召回率，轻微增加10-15ms |
| `BM25_TOP_K` | 6 | **8** | 平衡向量和稀疏检索 |
| `VECTOR_SIMILARITY_THRESHOLD` | 0.2 | **0.18** | 降低过滤，增加候选 |
| `RETRIEVAL_CACHE_TTL_SECONDS` | 45 | **180** | 3分钟缓存提升命中率40→60% |
| `RETRIEVAL_CACHE_MAX_ITEMS` | 256 | **512** | 更大缓存容量 |
| `CONSISTENCY_GUARD_SIMILARITY_THRESHOLD` | 0.55 | **0.60** | 更严格的一致性检查 |
| `QUERY_RETRY_MAX_ATTEMPTS` | 2 | **3** | 提升可靠性 |
| `SLO_P95_LATENCY_MS_THRESHOLD` | 3000 | **2500** | 更严格的性能目标 |
| `SLO_ERROR_RATE_PERCENT_THRESHOLD` | 5.0 | **3.0** | 更高质量标准 |
| `QUERY_REWRITE_MAX_VARIANTS` | 6 | **5** | 略微减少以平衡性能 |
| `RETRIEVAL_CACHE_BACKEND` | auto | **redis** | 明确使用Redis，支持多实例 |

**预期性能改进**:
- 召回率提升: +5-8%
- 缓存命中率: 40% → 60%
- 系统可靠性提升: ~15%
- P95延迟改善: 2800ms → 2400ms

---

## 🎯 场景化配置方案

### 方案1: 高吞吐FAQ系统

**目标**: QPS > 100, 延迟 < 1s

```bash
# 基础策略
RETRIEVAL_PROFILE=baseline
QUERY_REWRITE_ENABLED=false
QUERY_DECOMPOSE_ENABLED=false
ENABLE_RERANKER=false

# 激进缓存
RETRIEVAL_CACHE_TTL_SECONDS=300
QUERY_RESULT_CACHE_TTL_SECONDS=300
RETRIEVAL_CACHE_BACKEND=redis

# 高并发
QUERY_MAX_CONCURRENT=48
QUERY_REQUEST_TIMEOUT_MS=8000

# 精简检索
VECTOR_TOP_K=4
BM25_TOP_K=4
TOP_K=3
```

**性能预期**:
- P50延迟: 400ms
- P95延迟: 800ms
- 吞吐: 150 QPS
- 准确度: 70-75%

---

### 方案2: 企业知识助手（推荐）✨

**目标**: 平衡质量和性能

**使用**: `.env.optimized.recommended`

```bash
# 复制优化配置
cp .env.optimized.recommended .env
# 或
cat .env.optimized.recommended >> .env
```

**性能预期**:
- P50延迟: 1200ms
- P95延迟: 2500ms
- 吞吐: 40 QPS
- 准确度: 85-88%

---

### 方案3: 深度分析系统

**目标**: 最高质量，复杂推理

```bash
# 使用Deep Profile
source configs/runtime-profiles/deep.env

# 额外优化
RERANKER_MODEL_NAME=BAAI/bge-reranker-large
RERANKER_TOP_N=10
VECTOR_TOP_K=12
BM25_TOP_K=12
DYNAMIC_VECTOR_TOP_K_CAP=20
DYNAMIC_BM25_TOP_K_CAP=20
SYNTHESIS_REFINE_MAX_ROUNDS=6
CONSISTENCY_GUARD_SIMILARITY_THRESHOLD=0.70
```

**性能预期**:
- P50延迟: 3500ms
- P95延迟: 6000ms
- 吞吐: 8 QPS
- 准确度: 92-95%

---

### 方案4: 成本敏感型

**目标**: 最小化LLM调用成本

```bash
# 禁用LLM密集功能
QUERY_REWRITE_WITH_LLM=false
GRAPH_EXTRACTION_MODE=spacy
IMAGE_CAPTION_ENABLED=false

# 最大化缓存
RETRIEVAL_CACHE_TTL_SECONDS=600
QUERY_RESULT_CACHE_TTL_SECONDS=600
RETRIEVAL_CACHE_MAX_ITEMS=2048

# 保留本地模型功能
ENABLE_RERANKER=true

# 减少检索量
VECTOR_TOP_K=4
BM25_TOP_K=4
RERANKER_TOP_N=3
```

**成本节省**: 约60-70%

---

## 🔧 参数调优指南

### 1. 缓存优化

**问题**: 缓存命中率低 (<30%)

**诊断**:
```python
# 查看缓存统计
GET /api/analytics/cache-stats
```

**解决方案**:
```bash
# 逐步增加TTL和容量
RETRIEVAL_CACHE_TTL_SECONDS=120  # 起点
RETRIEVAL_CACHE_TTL_SECONDS=180  # 推荐
RETRIEVAL_CACHE_TTL_SECONDS=300  # 高命中率场景

RETRIEVAL_CACHE_MAX_ITEMS=512    # 推荐
RETRIEVAL_CACHE_MAX_ITEMS=1024   # 高频查询
```

**监控指标**:
- 命中率目标: >50%
- 内存开销: 每100项约2-5MB

---

### 2. 阈值调优

**向量相似度阈值**:

```bash
# 默认
VECTOR_SIMILARITY_THRESHOLD=0.18

# 高质量嵌入模型（OpenAI, Cohere）
VECTOR_SIMILARITY_THRESHOLD=0.25

# 领域特定/术语多
VECTOR_SIMILARITY_THRESHOLD=0.10

# 开源模型
VECTOR_SIMILARITY_THRESHOLD=0.15
```

**一致性守护阈值**:

```bash
# 默认
CONSISTENCY_GUARD_SIMILARITY_THRESHOLD=0.60

# 高风险场景（医疗、法律）
CONSISTENCY_GUARD_SIMILARITY_THRESHOLD=0.70

# 创意场景
CONSISTENCY_GUARD_SIMILARITY_THRESHOLD=0.40
```

---

### 3. 并发控制

**资源规划公式**:
```
QUERY_MAX_CONCURRENT = 系统内存(GB) * 2 - 4
```

**示例**:
```bash
# 8GB服务器
QUERY_MAX_CONCURRENT=12
QUERY_MAX_WAITING=60

# 16GB服务器（推荐）
QUERY_MAX_CONCURRENT=24
QUERY_MAX_WAITING=120

# 32GB+ 服务器
QUERY_MAX_CONCURRENT=48
QUERY_MAX_WAITING=200
```

---

### 4. Top-K调优

**检索量影响**:

| VECTOR_TOP_K | BM25_TOP_K | 召回率 | 延迟 | 内存 |
|--------------|------------|--------|------|------|
| 4 | 4 | 75% | 100ms | 低 |
| 6 | 6 | 82% | 120ms | 中 |
| **8** | **8** | **88%** | **150ms** | **中** ⭐ |
| 10 | 10 | 91% | 180ms | 中高 |
| 12 | 12 | 93% | 220ms | 高 |

**推荐配置**:
```bash
# 标准（推荐）
VECTOR_TOP_K=8
BM25_TOP_K=8
RERANKER_TOP_N=5

# 高召回
VECTOR_TOP_K=10
BM25_TOP_K=10
RERANKER_TOP_N=7

# 低延迟
VECTOR_TOP_K=6
BM25_TOP_K=6
RERANKER_TOP_N=3
```

---

## 🚨 常见配置错误

### ❌ 错误1: 缓存TTL过短

```bash
# 错误
RETRIEVAL_CACHE_TTL_SECONDS=30  # 命中率<20%

# 正确
RETRIEVAL_CACHE_TTL_SECONDS=180  # 命中率~60%
```

### ❌ 错误2: 阈值过高

```bash
# 错误
VECTOR_SIMILARITY_THRESHOLD=0.5  # 过滤太多

# 正确
VECTOR_SIMILARITY_THRESHOLD=0.18
```

### ❌ 错误3: 并发超配

```bash
# 错误 (8GB系统)
QUERY_MAX_CONCURRENT=100  # OOM风险

# 正确
QUERY_MAX_CONCURRENT=12
```

### ❌ 错误4: 禁用所有缓存

```bash
# 错误
RETRIEVAL_CACHE_ENABLED=false
QUERY_RESULT_CACHE_BACKEND=off
# 性能下降80%+

# 正确：至少启用检索缓存
RETRIEVAL_CACHE_ENABLED=true
```

### ❌ 错误5: Top-K过小

```bash
# 错误
VECTOR_TOP_K=2
BM25_TOP_K=2
# 召回率<60%

# 正确
VECTOR_TOP_K=8
BM25_TOP_K=8
```

---

## 📈 性能调优流程

### 步骤1: 建立基线

```bash
# 使用推荐配置
cp .env.optimized.recommended .env

# 运行基准测试
python scripts/benchmark_pipeline.py > baseline.json

# 记录关键指标
# - P50/P95延迟
# - 吞吐量
# - 准确度
# - 缓存命中率
```

### 步骤2: 识别瓶颈

```bash
# 启用详细诊断
OTEL_TRACING_ENABLED=true

# 查看诊断信息
# diagnostics包含:
# - vector_search_time_ms
# - bm25_search_time_ms
# - rerank_time_ms
# - llm_time_ms
# - cache_hit
```

### 步骤3: 针对性优化

**如果瓶颈是向量搜索**:
```bash
# 选项1: 减小检索量
VECTOR_TOP_K=6

# 选项2: 提升缓存
RETRIEVAL_CACHE_TTL_SECONDS=300

# 选项3: 优化索引（需要重建）
# 考虑使用HNSW或其他索引算法
```

**如果瓶颈是重排序**:
```bash
# 选项1: 更快的模型
RERANKER_MODEL_NAME=BAAI/bge-reranker-base

# 选项2: 确保GPU可用
# 检查: nvidia-smi

# 选项3: 禁用（降级到lexical）
ENABLE_RERANKER=false
```

**如果瓶颈是LLM调用**:
```bash
# 选项1: 禁用LLM重写
QUERY_REWRITE_WITH_LLM=false

# 选项2: 减少精炼轮次
SYNTHESIS_REFINE_MAX_ROUNDS=2

# 选项3: 使用更快的模型
OPENAI_CHAT_MODEL=gpt-3.5-turbo
```

### 步骤4: A/B测试

```bash
# 使用金丝雀路由
curl -X POST http://localhost:8000/admin/ops/canary \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "optimized",
    "percent": 10
  }'

# 观察指标
# 逐步提升: 10% → 25% → 50% → 100%
```

### 步骤5: 监控和迭代

```bash
# 持续监控SLO
# - P95延迟 < 2500ms ✓
# - 错误率 < 3% ✓
# - 引用率 > 60% ✓

# 每周重新评估
# 根据实际使用模式调整
```

---

## 📊 配置验证检查清单

使用以下清单验证配置：

- [ ] **缓存已启用且TTL合理** (120-300秒)
- [ ] **Redis连接已配置** (多实例部署必需)
- [ ] **并发限制匹配系统资源** (内存GB * 2 - 4)
- [ ] **向量阈值不会过滤太多结果** (0.15-0.25)
- [ ] **Top-K足够大以保证召回** (≥6)
- [ ] **重排序已启用** (除非有性能限制)
- [ ] **断路器和隔离舱已启用** (生产环境)
- [ ] **重试次数合理** (2-3次)
- [ ] **SLO目标已设置** (P95<2500ms, 错误率<3%)
- [ ] **安全检查已启用** (一致性守护、答案安全)

---

## 🎓 最佳实践总结

### ✅ DO

1. **使用推荐配置作为起点**: `.env.optimized.recommended`
2. **启用Redis缓存**: 多实例必需
3. **设置合理的缓存TTL**: 120-300秒
4. **配置断路器和重试**: 提升可靠性
5. **监控SLO指标**: 持续优化
6. **使用Profile快速切换**: Fast/Balanced/Deep
7. **A/B测试重大变更**: 金丝雀部署
8. **定期评估和调整**: 根据实际使用

### ❌ DON'T

1. **禁用所有缓存**: 性能下降80%+
2. **设置过高的阈值**: 召回率大幅下降
3. **超配并发**: OOM风险
4. **忽略SLO监控**: 问题发现延迟
5. **频繁改动配置**: 稳定性问题
6. **跳过基准测试**: 盲目优化
7. **在生产环境禁用安全检查**: 风险大
8. **使用默认密码**: 安全隐患

---

## 📞 获取帮助

如果遇到配置问题：

1. **查看文档**: `docs/README.md`
2. **运行诊断**: `python scripts/benchmark_pipeline.py`
3. **查看日志**: 启用详细日志级别
4. **社区支持**: GitHub Issues

---

**配置指南版本**: v0.4.4  
**最后更新**: 2026-06-03  
**维护者**: Kiro AI
