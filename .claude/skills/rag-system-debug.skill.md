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

```bash
# Check system health
curl http://localhost:8000/health
curl http://localhost:8000/ready

# Review recent logs
tail -f data/logs/app.log

# Check agent execution tracking
# Navigate to frontend /agent-tracking page
```

### Phase 2: Component-Level Diagnosis

#### Retrieval Pipeline
```python
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
```

#### Agent Execution
```bash
# Check LangGraph workflow
# Review app/graph/studio_entry.py for routing logic

# Test individual agents
python -c "from app.agents.router_agent import route_query; print(route_query('test'))"
```

#### Neo4j Graph
```bash
# Verify Neo4j connectivity
docker ps | grep neo4j

# Test graph queries
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "strategy": "graph_rag"}'
```

### Phase 3: Root Cause Analysis

Common issues and solutions:

1. **Empty retrieval results**
   - Verify documents are ingested: Check `data/docs/` and ChromaDB
   - Run manual ingestion: `python scripts/ingest.py`
   - Check embedding model availability

2. **Agent timeout errors**
   - Review `QUERY_REQUEST_TIMEOUT_MS` in .env
   - Check model backend (Ollama/OpenAI/Anthropic) availability
   - Verify API keys and rate limits

3. **Reranker failures**
   - Check if `ENABLE_RERANKER=true` and model is installed
   - Install reranker: `pip install -e ".[reranker]"`
   - Fallback: Set `ENABLE_RERANKER=false`

4. **Graph RAG errors**
   - Verify Neo4j is running: `docker compose ps`
   - Check `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in .env
   - Test connection: `docker exec -it neo4j cypher-shell`

5. **Streaming issues**
   - Check SSE endpoint: `/api/query/stream`
   - Review frontend EventSource implementation
   - Verify nginx/proxy doesn't buffer responses

### Phase 4: Validation

```bash
# Run backend tests
pytest tests/test_routing_logic.py -v
pytest tests/test_hybrid_retriever.py -v

# Run RAG evaluation
python scripts/eval_retrieval.py

# Benchmark performance
python scripts/benchmark_pipeline.py
```

## Key Files to Check

- `app/graph/studio_entry.py` - LangGraph workflow orchestration
- `app/agents/` - Individual agent implementations
- `app/retrievers/hybrid_retriever.py` - Retrieval pipeline
- `app/services/runtime_metrics.py` - Performance monitoring
- `app/api/routes/query.py` - Query endpoint handlers
- `data/logs/app.log` - Application logs

## Environment Variables to Verify

```bash
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
```

## Quick Fixes

```bash
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
```

## Monitoring Dashboard

Check real-time metrics at:
- Agent execution: `http://localhost:5173/app/agent-tracking`
- Retrieval analytics: `http://localhost:5173/app/analytics`
- System health: `http://localhost:8000/health`

## Related Skills

- `superpowers:systematic-debugging` - General debugging workflow
- `gitnexus-debugging` - Code-level call chain tracing
- Use this skill BEFORE those for RAG-specific diagnostics
