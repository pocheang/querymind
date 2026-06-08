# 项目Skills安装指南

本文档说明如何为这个多智能体RAG项目安装和配置定制skills。

## 📦 Skills文件位置

Skills文件应放置在：
```
~/.claude/skills/
```

或者Windows上：
```
C:\Users\{YourUsername}\.claude\skills\
```

## 🚀 快速安装

### 1. 创建Skills目录

```bash
# Linux/Mac
mkdir -p ~/.claude/skills

# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills"
```

### 2. 复制Skills文件

将以下三个skill文件复制到 `.claude/skills/` 目录：

#### Skill 1: rag-system-debug.skill.md

用于调试RAG系统问题（检索失败、Agent错误、查询处理问题）。

<details>
<summary>点击查看完整内容</summary>

```markdown
---
name: rag-system-debug
description: Debug RAG pipeline issues including retrieval failures, agent errors, and query processing problems
version: 1.0.0
tags: [debugging, rag, retrieval, agents]
---

# RAG System Debugging Skill

[之前生成的完整rag-system-debug内容]
```

</details>

#### Skill 2: rag-ingestion.skill.md

用于文档摄取和索引（OCR、分块、嵌入）。

<details>
<summary>点击查看完整内容</summary>

```markdown
---
name: rag-ingestion
description: Ingest and index documents into the RAG system with OCR, chunking, and embedding
version: 1.0.0
tags: [ingestion, documents, indexing, ocr]
---

# RAG Document Ingestion Skill

[之前生成的完整rag-ingestion内容]
```

</details>

#### Skill 3: rag-evaluation.skill.md

用于评估RAG系统性能（指标、基准测试、负载测试）。

<details>
<summary>点击查看完整内容</summary>

```markdown
---
name: rag-evaluation
description: Evaluate RAG system performance with metrics, baselines, and benchmarks
version: 1.0.0
tags: [evaluation, testing, metrics, benchmarks]
---

# RAG Evaluation Skill

[之前生成的完整rag-evaluation内容]
```

</details>

### 3. 验证安装

重启Claude Code，然后检查skills是否可用：

```bash
# 在Claude Code中，输入斜杠命令查看可用skills
/rag-system-debug
/rag-ingestion
/rag-evaluation
```

## 📋 手动创建Skills文件

如果您更喜欢手动创建，按以下步骤：

### 步骤1: 创建rag-system-debug.skill.md

```bash
# Linux/Mac
cat > ~/.claude/skills/rag-system-debug.skill.md << 'EOF'
---
name: rag-system-debug
description: Debug RAG pipeline issues including retrieval failures, agent errors, and query processing problems
version: 1.0.0
tags: [debugging, rag, retrieval, agents]
---

# RAG System Debugging Skill

Specialized skill for debugging multi-agent RAG system issues.

## When to Use

- Query returns empty or irrelevant results
- Agent execution failures or timeouts
- Hybrid retrieval (vector + BM25) not working as expected
- Reranking issues or degraded precision
- Graph RAG connection problems
- Streaming response failures
- Document ingestion or indexing errors

## Diagnostic Flow

### Phase 1: Identify the Failure Point

\`\`\`bash
# Check system health
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Review recent logs
tail -f data/logs/app.log

# Check agent execution tracking
# Navigate to frontend /agent-tracking page
\`\`\`

### Phase 2: Component-Level Diagnosis

#### Retrieval Pipeline
\`\`\`python
# Test vector retrieval
from app.retrievers.hybrid_retriever import HybridRetriever
retriever = HybridRetriever()
results = retriever.retrieve("test query", top_k=5)

# Check ChromaDB status
from app.core.settings import get_settings
settings = get_settings()
# Verify CHROMA_PERSIST_DIR exists and has collections

# Test BM25
# Check CORPUS_STORE_PATH for indexed documents
\`\`\`

#### Agent Execution
\`\`\`bash
# Check LangGraph workflow
# Review app/graph/studio_entry.py for routing logic

# Test individual agents
python -c "from app.agents.router_agent import route_query; print(route_query('test'))"
\`\`\`

#### Neo4j Graph
\`\`\`bash
# Verify Neo4j connectivity
docker ps | grep neo4j

# Test graph queries
curl -X POST http://localhost:8000/api/query \\
  -H "Content-Type: application/json" \\
  -d '{"query": "test", "strategy": "graph_rag"}'
\`\`\`

### Phase 3: Root Cause Analysis

Common issues and solutions:

1. **Empty retrieval results**
   - Verify documents are ingested: Check \`data/docs/\` and ChromaDB
   - Run manual ingestion: \`python scripts/ingest.py\`
   - Check embedding model availability

2. **Agent timeout errors**
   - Review \`QUERY_REQUEST_TIMEOUT_MS\` in .env
   - Check model backend (Ollama/OpenAI/Anthropic) availability
   - Verify API keys and rate limits

3. **Reranker failures**
   - Check if \`ENABLE_RERANKER=true\` and model is installed
   - Install reranker: \`pip install -e ".[reranker]"\`
   - Fallback: Set \`ENABLE_RERANKER=false\`

4. **Graph RAG errors**
   - Verify Neo4j is running: \`docker compose ps\`
   - Check \`NEO4J_URI\`, \`NEO4J_USER\`, \`NEO4J_PASSWORD\` in .env
   - Test connection: \`docker exec -it neo4j cypher-shell\`

5. **Streaming issues**
   - Check SSE endpoint: \`/api/query/stream\`
   - Review frontend EventSource implementation
   - Verify nginx/proxy doesn't buffer responses

### Phase 4: Validation

\`\`\`bash
# Run backend tests
pytest tests/test_routing_logic.py -v
pytest tests/test_hybrid_retriever.py -v

# Run RAG evaluation
python scripts/eval_retrieval.py

# Benchmark performance
python scripts/benchmark_pipeline.py
\`\`\`

## Key Files to Check

- \`app/graph/studio_entry.py\` - LangGraph workflow orchestration
- \`app/agents/\` - Individual agent implementations
- \`app/retrievers/hybrid_retriever.py\` - Retrieval pipeline
- \`app/services/runtime_metrics.py\` - Performance monitoring
- \`app/api/routes/query.py\` - Query endpoint handlers
- \`data/logs/app.log\` - Application logs

## Environment Variables to Verify

\`\`\`bash
# Model configuration
MODEL_BACKEND=
OPENAI_API_KEY= / ANTHROPIC_API_KEY= / OLLAMA_BASE_URL=

# Retrieval configuration
TOP_K=
ENABLE_RERANKER=
RETRIEVAL_PROFILE=

# Timeouts
QUERY_REQUEST_TIMEOUT_MS=
EMBEDDING_TIMEOUT_MS=

# Storage paths
CHROMA_PERSIST_DIR=
CORPUS_STORE_PATH=
DATA_DIR=
\`\`\`

## Quick Fixes

\`\`\`bash
# Restart backend with fresh logs
pkill -f uvicorn
uvicorn app.api.main:app --reload --log-level debug

# Clear and rebuild ChromaDB
rm -rf data/chromadb/*
python scripts/ingest.py

# Reset Neo4j graph
docker compose down neo4j
docker compose up -d neo4j
# Wait 30s for initialization

# Verify conda environment
conda activate rag-local
pip list | grep -E "(langchain|chromadb|neo4j)"
\`\`\`

## Monitoring Dashboard

Check real-time metrics at:
- Agent execution: \`http://localhost:5173/app/agent-tracking\`
- Retrieval analytics: \`http://localhost:5173/app/analytics\`
- System health: \`http://localhost:8000/health\`

## Related Skills

- \`superpowers:systematic-debugging\` - General debugging workflow
- \`gitnexus-debugging\` - Code-level call chain tracing
- Use this skill BEFORE those for RAG-specific diagnostics
EOF
```

### 步骤2: 创建rag-ingestion.skill.md

使用类似的方法创建其他两个skill文件。

## 🔄 Skills使用指南

### 调用Skills

在Claude Code中，使用斜杠命令调用：

```
/rag-system-debug
/rag-ingestion
/rag-evaluation
```

### 典型使用场景

#### 场景1: 查询返回空结果

```
用户: "我的查询没有返回任何结果"

Claude: 让我使用RAG系统调试skill来诊断...
/rag-system-debug

[执行诊断流程]
1. 检查文档是否已摄取
2. 验证ChromaDB索引
3. 测试检索管道
4. 提供修复方案
```

#### 场景2: 添加新文档

```
用户: "如何添加新的PDF文档到系统？"

Claude: 让我使用文档摄取skill指导您...
/rag-ingestion

[提供详细步骤]
1. 放置文档到data/docs/
2. 激活conda环境
3. 运行摄取脚本
4. 验证索引
5. 测试检索
```

#### 场景3: 评估系统性能

```
用户: "如何评估RAG系统的质量？"

Claude: 让我使用RAG评估skill...
/rag-evaluation

[运行评估流程]
1. 执行检索质量评估
2. 运行性能基准测试
3. 分析指标
4. 提供优化建议
```

## 🔧 Skills配置

### 与通用Skills的集成

这些项目特定skills与通用skills配合使用：

```
遇到RAG问题流程：
1. /rag-system-debug（先用项目特定skill诊断）
2. superpowers:systematic-debugging（如需深入调试）
3. gitnexus-debugging（如需追踪代码调用链）

开发新RAG功能流程：
1. superpowers:brainstorming（探索需求）
2. superpowers:writing-plans（编写计划）
3. superpowers:test-driven-development（TDD实现）
4. /rag-evaluation（评估质量）
5. superpowers:verification-before-completion（验证）
6. superpowers:requesting-code-review（请求审查）
```

### Skills优先级

| 问题类型 | 首选Skill | 次选Skill |
|---------|----------|----------|
| RAG检索问题 | /rag-system-debug | systematic-debugging |
| 文档摄取 | /rag-ingestion | - |
| 性能评估 | /rag-evaluation | verification-before-completion |
| 代码Bug | systematic-debugging | /rag-system-debug |
| 重构 | gitnexus-refactoring | /rag-evaluation |

## 📚 进一步阅读

- [PROJECT_SKILLS.md](PROJECT_SKILLS.md) - 项目Skills完整指南
- [.claude/SKILLS_GUIDE.md](../../.claude/SKILLS_GUIDE.md) - 通用Skills指南
- [README.md](../../README.md) - 项目文档

## 🤝 贡献

如果您创建了新的项目特定skill或改进了现有skill，请：

1. 更新skill文件
2. 更新此安装指南
3. 更新PROJECT_SKILLS.md
4. 提交PR

---

**维护者**：Bronit Team  
**最后更新**：2026-06-08
