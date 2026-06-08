# 问题修复计划

**日期**: 2026-06-03  
**状态**: 进行中

---

## 🔴 高优先级（立即修复）

### 1. Git状态清理 ✅ 准备执行
- **问题**: v0.4.4实现未提交，大量未跟踪文件
- **影响**: 代码管理混乱，无法回滚
- **修复**:
  - [ ] 审查修改的文件（caching.py, fusion.py）
  - [ ] 提交v0.4.4核心组件
  - [ ] 添加适当的commit message

**修改内容**:
- `app/retrievers/hybrid/caching.py`: 添加logging导入和logger
- `app/retrievers/hybrid/fusion.py`: 添加RRF函数（65行新代码）
- 新增文件: 6个核心组件 + 2个测试脚本 + 2个文档

**命令**:
```bash
git add app/retrievers/hybrid/caching.py app/retrievers/hybrid/fusion.py
git add app/core/optimized_config.py
git add app/retrievers/fast_reranker.py
git add app/retrievers/multi_path_retriever.py
git add app/services/adaptive_strategy.py
git add app/services/optimized_prompts.py
git add app/services/optimized_rag_pipeline.py
git add app/services/rule_compressor.py
git add scripts/test_components_simple.py
git add scripts/test_optimized_pipeline.py
git add docs/v0.4.4-implementation-guide.md
git add docs/v0.4.4-quick-reference.md
git add .claude/completed/2026-06-03-*.md
git add .claude/plans/v0.4.4-*.md

git commit -m "feat: implement v0.4.4 accuracy and speed optimizations

- Add multi-path parallel retrieval (300ms target)
- Implement fast GPU reranker (200ms target)
- Add rule-based compression (50ms target)
- Implement adaptive query routing
- Add optimized RAG pipeline with caching
- Create optimized prompts (60% shorter)
- Add comprehensive testing framework

Performance targets:
- Standard mode: 800ms (from 1500ms, -40%)
- Fast mode: 400ms
- Precise mode: 1500ms

Expected accuracy improvements:
- Recall@10: 65-70% → 85-88% (+20%)
- Precision@10: 50-55% → 68-72% (+18%)
- Answer Relevance: 70% → 85-88% (+17%)"
```

---

### 2. 优化RAG配置默认值 ⏳ 等待测试
- **问题**: 部分默认值不够优化
- **影响**: 性能和准确度未达到最佳
- **修复**:
  - [ ] 更新.env.example
  - [ ] 提升缓存TTL
  - [ ] 调整阈值
  - [ ] 文档说明

**建议修改**:
```bash
# 当前 → 推荐
RETRIEVAL_CACHE_TTL_SECONDS=45 → 180
RETRIEVAL_CACHE_MAX_ITEMS=256 → 512
VECTOR_SIMILARITY_THRESHOLD=0.2 → 0.18
VECTOR_TOP_K=6 → 8
BM25_TOP_K=6 → 8
CONSISTENCY_GUARD_SIMILARITY_THRESHOLD=0.55 → 0.60
QUERY_RETRY_MAX_ATTEMPTS=2 → 3
SLO_P95_LATENCY_MS_THRESHOLD=3000 → 2500
```

---

### 3. 运行v0.4.4测试验证 ⏳ 待执行
- **问题**: v0.4.4实现未经测试
- **影响**: 不确定功能是否正常
- **修复**:
  - [ ] 激活conda环境
  - [ ] 运行测试脚本
  - [ ] 修复发现的问题
  - [ ] 记录测试结果

**命令**:
```bash
conda activate rag-local
python scripts/test_optimized_pipeline.py
python scripts/test_components_simple.py
pytest tests/ -v
```

---

## 🟡 中优先级（本周完成）

### 4. 添加覆盖率报告
- **问题**: 缺少可见的测试覆盖率
- **修复**:
  ```bash
  pytest --cov=app --cov-report=html --cov-report=term
  # 添加徽章到README.md
  ```

### 5. 配置验证器
- **问题**: 启动时未验证配置合理性
- **修复**: 创建`app/core/config_validator.py`

### 6. 增强RRF权重使用
- **问题**: 权重仅用于归一化，未实际影响RRF分数
- **修复**: 实现加权RRF

---

## 🟢 低优先级（后续优化）

### 7. 扩展复杂度关键词列表
### 8. 更新停用词表
### 9. jieba分词集成到BM25
### 10. E2E测试套件（Playwright）
### 11. Prometheus集成
### 12. 容器化（Docker + K8s）

---

## 📊 执行状态

- ✅ 完成
- ⏳ 进行中
- ⏸️ 暂停
- ❌ 失败
- 🔄 重做

**当前状态**: 高优先级任务准备执行

