# Multi-Agent RAG Project Skills

这是针对本项目定制的技能（skills）整理文档。

## 📋 项目特定Skills概览

本项目是一个**企业级多智能体本地RAG系统**，包含以下核心功能：
- 多智能体查询编排（LangGraph）
- 混合检索（向量 + BM25 + 重排序）
- 知识图谱增强（Neo4j）
- 文档摄取与OCR
- 流式对话与会话管理
- RBAC权限控制

## 🎯 推荐Skills工作流

### 1️⃣ 新功能开发

```
适用场景：添加新的RAG功能、新Agent、新API端点

工作流：
1. superpowers:brainstorming
   ├─ 探索需求和技术方案
   └─ 考虑与现有5个Agent的集成
   
2. superpowers:writing-plans
   ├─ 编写实现计划
   └─ 考虑LangGraph流程编排
   
3. superpowers:using-git-worktrees（可选）
   └─ 大型功能需要隔离环境
   
4. superpowers:test-driven-development
   ├─ 先写测试（tests/目录）
   └─ 参考现有50+测试模块
   
5. 实现功能
   ├─ 修改 app/ 目录代码
   └─ 更新 frontend/ 如需UI
   
6. 项目特定验证（见下方"RAG系统验证流程"）
   
7. superpowers:verification-before-completion
   
8. superpowers:requesting-code-review
```

### 2️⃣ Bug修复

```
适用场景：检索失败、Agent超时、查询错误

工作流：
1. superpowers:systematic-debugging
   ├─ Phase 1: 根因分析
   │   ├─ 检查是检索问题还是Agent问题
   │   ├─ 查看 data/logs/app.log
   │   └─ 可选：gitnexus-debugging 追踪调用链
   │
   ├─ Phase 2: 修复方案设计
   │   └─ 参考下方"RAG系统调试检查清单"
   │
   ├─ Phase 3: 实现修复
   │   └─ 可选：superpowers:test-driven-development
   │
   └─ Phase 4: 验证
       └─ 运行RAG特定测试（见下方）

2. superpowers:verification-before-completion

3. superpowers:requesting-code-review
```

### 3️⃣ 重构任务

```
适用场景：优化检索管道、重构Agent逻辑、API重构

工作流：
1. gitnexus-exploring / nexus-query
   └─ 理解现有代码结构
   
2. gitnexus-impact-analysis
   └─ 分析修改影响范围
   
3. superpowers:writing-plans
   
4. superpowers:using-git-worktrees
   └─ 重构建议使用隔离环境
   
5. gitnexus-refactoring（如适用）
   
6. 项目特定验证（见下方）
   
7. superpowers:verification-before-completion
   
8. superpowers:requesting-code-review
```

### 4️⃣ 文档摄取与索引

```
适用场景：添加新文档、重建索引、OCR配置

关键文件：
- scripts/ingest.py - 手动摄取脚本
- app/ingestion/ - 加载器和分块策略
- data/docs/ - 源文档目录

验证步骤：
1. 放置文档到 data/docs/
2. 激活环境：conda activate rag-local
3. 运行摄取：python scripts/ingest.py
4. 验证索引：
   curl http://localhost:8000/documents | jq
5. 测试检索：
   python scripts/eval_retrieval.py
```

### 5️⃣ 性能评估与基准测试

```
适用场景：版本发布前、性能优化后、CI/CD管道

评估脚本：
- scripts/eval_retrieval.py - RAG质量评估
- scripts/benchmark_pipeline.py - 性能基准测试
- scripts/load_test_query.py - 负载测试
- scripts/ci_quality_gate.py - CI质量门禁

质量标准：
✅ Precision ≥ 0.75
✅ Recall ≥ 0.65
✅ F1 Score ≥ 0.70
✅ P95 Latency < 2000ms

Skills配合：
- superpowers:verification-before-completion
  └─ 必须运行这些评估
```

## 🔧 RAG系统调试检查清单

遇到问题时，按此顺序检查：

### 系统健康检查
```bash
# 1. 检查服务状态
curl http://localhost:8000/health
curl http://localhost:8000/ready

# 2. 检查后端日志
tail -f data/logs/app.log

# 3. 检查Neo4j
docker ps | grep neo4j

# 4. 检查模型后端
# Ollama:
curl http://localhost:11434/api/tags
# OpenAI/Anthropic: 检查API密钥
```

### 检索管道诊断
```python
# 测试混合检索器
from app.retrievers.hybrid_retriever import HybridRetriever
retriever = HybridRetriever()
results = retriever.retrieve("测试查询", top_k=5)
print(f"检索到 {len(results)} 个结果")

# 检查ChromaDB
ls -lh data/chromadb/

# 检查BM25索引
ls -lh data/corpus_store.pkl
```

### Agent执行跟踪
```bash
# 前端查看Agent执行
# 访问：http://localhost:5173/app/agent-tracking

# 测试单个Agent
python -c "
from app.agents.router_agent import route_query
result = route_query('测试查询')
print(result)
"
```

### 常见问题快速修复
```bash
# 问题1: 检索结果为空
→ python scripts/ingest.py  # 重新摄取

# 问题2: Agent超时
→ 检查 .env 中的 QUERY_REQUEST_TIMEOUT_MS
→ 验证模型后端可用性

# 问题3: 重排序失败
→ pip install -e ".[reranker]"
→ 或设置 ENABLE_RERANKER=false

# 问题4: Graph RAG错误
→ docker compose up -d neo4j
→ 等待30秒初始化

# 问题5: 流式响应失败
→ 检查 /api/query/stream 端点
→ 验证前端EventSource实现
```

## 📊 RAG系统验证流程

每次修改后必须验证：

### Level 1: 单元测试
```bash
# 运行相关测试
pytest tests/test_routing_logic.py -v
pytest tests/test_hybrid_retriever.py -v
pytest tests/test_agents.py -v

# 全量测试
pytest -q --allow-runtime-unavailable
```

### Level 2: RAG质量评估
```bash
# 检索质量
python scripts/eval_retrieval.py

# 期望输出：
# Precision: 0.75+
# Recall: 0.65+
# F1 Score: 0.70+
```

### Level 3: 性能基准测试
```bash
# 延迟测试
python scripts/benchmark_pipeline.py

# 期望输出：
# Mean latency: < 1500ms
# P95 latency: < 2000ms
# P99 latency: < 3000ms
```

### Level 4: 端到端测试
```bash
# 启动后端
uvicorn app.api.main:app --reload

# 启动前端
cd frontend && npm run dev

# 手动测试：
# 1. 访问 http://localhost:5173/app
# 2. 登录（或注册）
# 3. 提交测试查询
# 4. 验证响应质量
# 5. 检查Agent执行追踪页面
```

## 🎨 前端开发Skills

### 前端相关技能
```
适用场景：UI改进、新页面、组件重构

技术栈：
- React + Vite
- TypeScript
- CSS Modules

工作流：
1. frontend-design
   └─ 构建新组件或页面
   
2. 关键文件：
   ├─ frontend/src/components/
   ├─ frontend/src/pages/
   └─ frontend/src/styles/
   
3. 验证：
   ├─ npm run type-check
   ├─ npm run lint
   └─ npm run build
   
4. superpowers:verification-before-completion

相关页面：
- /app - 主聊天界面（含架构可视化）
- /app/documents - 文档管理
- /app/agent-tracking - Agent执行追踪
- /app/analytics - 检索分析
- /app/advanced-rag - 高级RAG功能
```

## 🔐 安全相关Skills

### 安全审查场景
```
适用场景：认证修改、权限变更、API密钥处理

工作流：
1. superpowers:brainstorming
   └─ 考虑安全影响
   
2. 实现更改（涉及的文件）：
   ├─ app/services/auth/ - 认证服务
   ├─ app/services/rbac.py - RBAC
   └─ app/api/routes/auth.py - 认证路由
   
3. security-review
   └─ 执行安全审查
   
4. 验证：
   ├─ pytest tests/test_auth.py -v
   ├─ 检查密码策略（12+字符）
   ├─ 验证JWT过期
   └─ 测试用户隔离

5. superpowers:requesting-code-review
```

## 📦 集成新模型后端

### 模型集成场景
```
适用场景：添加新LLM提供商、更换嵌入模型

当前支持：
- Ollama（本地）
- OpenAI
- Anthropic

集成新后端：
1. superpowers:brainstorming
   └─ 设计集成方案
   
2. 修改文件：
   ├─ app/core/settings.py - 添加配置
   ├─ app/agents/ - 更新Agent调用
   └─ .env.example - 文档化环境变量
   
3. 验证：
   ├─ 测试聊天模型
   ├─ 测试嵌入模型
   └─ 运行端到端查询
   
4. superpowers:verification-before-completion
```

## 🚀 部署与运维Skills

### 生产部署检查清单
```
superpowers:finishing-a-development-branch

验证项：
✅ 所有测试通过（pytest）
✅ RAG评估达标（precision/recall/F1）
✅ 性能基准符合预期
✅ 安全配置检查：
   - AUTH_COOKIE_SECURE=true
   - 审查API密钥处理
   - 验证CORS设置
✅ 文档更新：
   - CHANGELOG.md
   - docs/VERSION_HISTORY.md
   - README.md（如需要）
✅ 前端构建：npm run build
✅ Docker镜像测试（如适用）

部署后验证：
- 运行 scripts/ci_quality_gate.py
- 监控 /health 和 /ready 端点
- 检查生产日志
- 运行烟雾测试（scripts/dev/）
```

## 🧪 测试策略

### 测试金字塔
```
Level 4: 端到端测试（手动）
  └─ 完整用户流程

Level 3: 集成测试
  ├─ pytest tests/test_workflow_*.py
  └─ 测试Agent协作

Level 2: 模块测试
  ├─ pytest tests/test_routing_logic.py
  ├─ pytest tests/test_hybrid_retriever.py
  └─ pytest tests/test_auth.py

Level 1: 单元测试
  └─ 各组件单独测试

Skills配合：
- superpowers:test-driven-development
  └─ 所有新功能必须先写测试
```

## 📚 技能优先级矩阵

| 任务类型 | 必须使用 | 推荐使用 | 可选使用 |
|---------|---------|---------|---------|
| 新RAG功能 | brainstorming, TDD | writing-plans, worktrees | gitnexus-exploring |
| Bug修复 | systematic-debugging | verification | gitnexus-debugging |
| 检索优化 | verification | eval_retrieval.py | benchmark_pipeline.py |
| Agent修改 | brainstorming, TDD | systematic-debugging | agent-tracking页面 |
| 前端开发 | frontend-design | verification | - |
| 安全变更 | security-review | verification | - |
| 性能调优 | benchmark测试 | eval_retrieval.py | load_test.py |
| 文档摄取 | ingest.py验证 | - | OCR配置 |

## 🔗 相关文档

- [.claude/SKILLS_GUIDE.md](.claude/SKILLS_GUIDE.md) - 通用Skills指南
- [README.md](../README.md) - 项目概览
- [docs/README.md](../docs/README.md) - 文档中心
- [CHANGELOG.md](../CHANGELOG.md) - 版本历史
- [scripts/dev/README.md](../scripts/dev/README.md) - 开发脚本

## 💡 最佳实践

### 开发前
1. ✅ 激活conda环境：`conda activate rag-local`
2. ✅ 拉取最新代码：`git pull`
3. ✅ 运行测试确保基线：`pytest -q`
4. ✅ 使用brainstorming探索方案

### 开发中
1. ✅ 遵循TDD：先测试，后实现
2. ✅ 频繁提交：小步提交，清晰message
3. ✅ 保持日志：检查`data/logs/app.log`
4. ✅ 使用worktrees：大型功能隔离开发

### 开发后
1. ✅ 运行完整测试套件
2. ✅ 执行RAG评估（eval_retrieval.py）
3. ✅ 性能基准测试（benchmark_pipeline.py）
4. ✅ 更新文档和CHANGELOG
5. ✅ 请求代码审查

---

**维护者**：Bronit Team  
**最后更新**：2026-06-08  
**版本**：1.0.0
