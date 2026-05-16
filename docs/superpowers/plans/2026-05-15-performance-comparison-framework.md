# Implementation Plan: Performance Comparison Framework

**Date**: 2026-05-15  
**Estimated Duration**: 2 days  
**Dependencies**: None (foundational module)  
**Related Spec**: [Interview Demo Improvements Design](../specs/2026-05-15-interview-demo-improvements-design.md)

## Objective

Build a comprehensive performance evaluation framework that compares our multi-agent RAG system against three baseline systems, providing quantitative metrics to demonstrate improvements for interview presentation.

## Scope

### In Scope
- Three baseline system implementations (vector-only, hybrid, rerank)
- Evaluation service with standard IR metrics (Precision, Recall, F1, MRR)
- Demo dataset preparation (enterprise + technical documents)
- Test query set with ground truth annotations
- API endpoints for running evaluations and retrieving results
- JSON output format for dashboard consumption

### Out of Scope
- Frontend dashboard (covered in separate plan)
- Real-time evaluation streaming
- Historical trend analysis (future enhancement)
- A/B testing infrastructure

## Architecture

```
app/evaluation/
├── baselines/
│   ├── __init__.py
│   ├── vector_only.py          # Pure vector search baseline
│   ├── hybrid.py                # Vector + BM25 hybrid
│   └── rerank.py                # Hybrid + cross-encoder rerank
├── services/
│   ├── __init__.py
│   └── evaluation_service.py   # Core evaluation logic
└── models.py                    # Data models

data/demo/
├── enterprise/                  # HR, IT, Finance docs
├── technical/                   # FastAPI, LangGraph, RAG papers
└── evaluation/
    ├── test_queries.json        # 25 test queries
    └── ground_truth.json        # Relevance judgments

app/api/routes/
└── evaluation.py                # API endpoints
```

## File Details

### 1. `app/evaluation/baselines/vector_only.py` (~150 lines)
**Purpose**: Pure vector similarity search baseline  
**Key Components**:
- `VectorOnlyRetriever` class
- `retrieve(query, top_k)` method
- Integration with existing vector store

### 2. `app/evaluation/baselines/hybrid.py` (~180 lines)
**Purpose**: Vector + BM25 hybrid search baseline  
**Key Components**:
- `HybridRetriever` class
- BM25 implementation using `rank-bm25` library
- Score fusion (weighted average: 0.7 vector + 0.3 BM25)

### 3. `app/evaluation/baselines/rerank.py` (~200 lines)
**Purpose**: Hybrid search + cross-encoder reranking  
**Key Components**:
- `RerankRetriever` class
- Cross-encoder model integration (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- Two-stage retrieval: hybrid (top 20) → rerank (top 5)

### 4. `app/evaluation/services/evaluation_service.py` (~250 lines)
**Purpose**: Core evaluation logic and metrics calculation  
**Key Components**:
- `EvaluationService` class
- Metrics: `precision_at_k`, `recall_at_k`, `f1_at_k`, `mrr`, `ndcg`
- `run_evaluation(system_name, queries)` method
- `compare_systems(results_list)` method
- Result persistence to JSON

### 5. `app/evaluation/models.py` (~100 lines)
**Purpose**: Pydantic models for evaluation data  
**Models**:
- `TestQuery`: query text, expected doc IDs, category
- `RetrievalResult`: query, retrieved docs, scores, latency
- `EvaluationMetrics`: precision, recall, F1, MRR, NDCG
- `SystemComparison`: comparative metrics across systems

### 6. `app/api/routes/evaluation.py` (~150 lines)
**Purpose**: API endpoints for evaluation  
**Endpoints**:
- `POST /api/evaluation/run`: Run evaluation on specified system
- `GET /api/evaluation/results/{run_id}`: Get evaluation results
- `GET /api/evaluation/compare`: Compare multiple systems
- `GET /api/evaluation/queries`: List test queries

### 7. `data/demo/evaluation/test_queries.json`
**Purpose**: Test query set with ground truth  
**Structure**:
```json
[
  {
    "id": "q001",
    "query": "年假政策是什么？",
    "category": "enterprise_hr",
    "expected_docs": ["hr_policy.pdf:section_3"],
    "difficulty": "easy"
  },
  ...
]
```
**Size**: 25 queries (10 enterprise, 10 technical, 5 complex)

### 8. `data/demo/evaluation/ground_truth.json`
**Purpose**: Relevance judgments for evaluation  
**Structure**:
```json
{
  "q001": {
    "highly_relevant": ["hr_policy.pdf:section_3"],
    "relevant": ["hr_policy.pdf:section_1"],
    "not_relevant": ["it_guide.pdf:section_2"]
  },
  ...
}
```

## Implementation Tasks

### Task 1: Setup Evaluation Module Structure
**Duration**: 1 hour  
**Steps**:
1. Create directory structure: `app/evaluation/baselines/`, `app/evaluation/services/`
2. Create `__init__.py` files
3. Create `app/evaluation/models.py` with Pydantic models
4. Add evaluation dependencies to `requirements.txt`:
   - `rank-bm25==0.2.2`
   - `sentence-transformers==2.2.2` (for cross-encoder)
5. Run `pip install -r requirements.txt`

**Verification**:
- [ ] Directory structure exists
- [ ] Can import `app.evaluation.models`
- [ ] Dependencies installed successfully

### Task 2: Implement Vector-Only Baseline
**Duration**: 2 hours  
**Steps**:
1. Create `app/evaluation/baselines/vector_only.py`
2. Implement `VectorOnlyRetriever` class:
   - `__init__(vector_store)`: Initialize with existing vector store
   - `retrieve(query: str, top_k: int = 5)`: Perform vector search
   - `_format_results(raw_results)`: Convert to standard format
3. Add logging for retrieval latency
4. Write unit tests in `tests/unit/test_vector_only_baseline.py`
5. Test with sample queries

**Verification**:
- [ ] Can retrieve documents using vector search
- [ ] Returns results in standard format (doc_id, score, content)
- [ ] Latency is logged
- [ ] Unit tests pass

### Task 3: Implement Hybrid Baseline
**Duration**: 3 hours  
**Steps**:
1. Create `app/evaluation/baselines/hybrid.py`
2. Implement BM25 indexing:
   - Load documents from vector store
   - Tokenize using simple whitespace + lowercase
   - Build BM25 index using `rank-bm25`
3. Implement `HybridRetriever` class:
   - `__init__(vector_store, bm25_index)`: Initialize both retrievers
   - `retrieve(query, top_k)`: Retrieve from both, fuse scores
   - `_fuse_scores(vector_results, bm25_results)`: Weighted average (0.7/0.3)
4. Add caching for BM25 index (pickle to disk)
5. Write unit tests
6. Compare results with vector-only baseline

**Verification**:
- [ ] BM25 index builds successfully
- [ ] Hybrid retrieval returns fused results
- [ ] Score fusion is correct (0.7 vector + 0.3 BM25)
- [ ] BM25 index caches to disk
- [ ] Unit tests pass

### Task 4: Implement Rerank Baseline
**Duration**: 3 hours  
**Steps**:
1. Create `app/evaluation/baselines/rerank.py`
2. Load cross-encoder model:
   - Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
   - Add model caching to avoid re-downloading
3. Implement `RerankRetriever` class:
   - `__init__(hybrid_retriever, cross_encoder)`: Initialize
   - `retrieve(query, top_k)`: Two-stage retrieval
     - Stage 1: Hybrid retrieval (top 20)
     - Stage 2: Cross-encoder rerank (top 5)
   - `_rerank(query, candidates)`: Score with cross-encoder
4. Add latency tracking for both stages
5. Write unit tests
6. Compare with hybrid baseline

**Verification**:
- [ ] Cross-encoder model loads successfully
- [ ] Two-stage retrieval works correctly
- [ ] Reranking improves relevance (manual spot check)
- [ ] Latency is tracked for both stages
- [ ] Unit tests pass

### Task 5: Implement Evaluation Service
**Duration**: 4 hours  
**Steps**:
1. Create `app/evaluation/services/evaluation_service.py`
2. Implement metric calculation functions:
   - `precision_at_k(retrieved, relevant, k)`
   - `recall_at_k(retrieved, relevant, k)`
   - `f1_at_k(precision, recall)`
   - `mean_reciprocal_rank(retrieved, relevant)`
   - `ndcg_at_k(retrieved, relevance_scores, k)`
3. Implement `EvaluationService` class:
   - `run_evaluation(system, queries, ground_truth)`:
     - For each query: retrieve docs, calculate metrics
     - Aggregate metrics across queries
     - Track latency and cost (token usage)
   - `compare_systems(system_results)`: Generate comparison table
   - `save_results(results, output_path)`: Persist to JSON
4. Add progress logging (e.g., "Evaluated 10/25 queries")
5. Write unit tests with mock retrievers
6. Test with sample queries and ground truth

**Verification**:
- [ ] All metric functions work correctly
- [ ] `run_evaluation` produces complete results
- [ ] Results save to JSON in correct format
- [ ] Progress is logged during evaluation
- [ ] Unit tests pass

### Task 6: Prepare Demo Dataset
**Duration**: 3 hours  
**Steps**:
1. Create directory structure: `data/demo/enterprise/`, `data/demo/technical/`
2. Prepare enterprise documents:
   - `hr_policy.pdf`: HR policies (annual leave, sick leave, benefits)
   - `it_guide.pdf`: IT guidelines (VPN, software, security)
   - `finance.pdf`: Finance policies (expense reports, budgets)
3. Prepare technical documents:
   - `fastapi_docs.md`: FastAPI documentation excerpts
   - `langgraph.md`: LangGraph tutorial and examples
   - `rag_papers.pdf`: RAG research paper summaries
4. Ingest documents into vector store:
   - Run ingestion script for each document
   - Verify embeddings are created
   - Check document chunks in vector store
5. Document the dataset in `data/demo/README.md`

**Verification**:
- [ ] All documents exist in `data/demo/`
- [ ] Documents are ingested into vector store
- [ ] Can retrieve chunks from each document
- [ ] Dataset README is complete

### Task 7: Create Test Query Set
**Duration**: 2 hours  
**Steps**:
1. Create `data/demo/evaluation/test_queries.json`
2. Write 25 test queries:
   - 10 enterprise queries (HR, IT, Finance)
   - 10 technical queries (FastAPI, LangGraph, RAG)
   - 5 complex queries (comparison, multi-hop)
3. For each query, specify:
   - Query text (Chinese and English mix)
   - Category
   - Expected document IDs
   - Difficulty level (easy/medium/hard)
4. Create `data/demo/evaluation/ground_truth.json`
5. For each query, annotate relevance:
   - Highly relevant docs (score 2)
   - Relevant docs (score 1)
   - Not relevant docs (score 0)
6. Validate JSON format

**Verification**:
- [ ] 25 queries created with diverse categories
- [ ] Each query has expected docs specified
- [ ] Ground truth annotations are complete
- [ ] JSON files are valid

### Task 8: Implement API Endpoints
**Duration**: 2 hours  
**Steps**:
1. Create `app/api/routes/evaluation.py`
2. Implement endpoints:
   - `POST /api/evaluation/run`:
     - Request: `{system: "vector_only" | "hybrid" | "rerank" | "full", queries?: string[]}`
     - Response: `{run_id, status, results}`
   - `GET /api/evaluation/results/{run_id}`:
     - Response: `{metrics, query_results, latency, cost}`
   - `GET /api/evaluation/compare`:
     - Query params: `systems=vector_only,hybrid,rerank,full`
     - Response: Comparison table with all metrics
   - `GET /api/evaluation/queries`:
     - Response: List of test queries
3. Add error handling and validation
4. Register routes in `app/api/main.py`
5. Test endpoints with curl/Postman
6. Write API tests in `tests/api/test_evaluation_routes.py`

**Verification**:
- [ ] All endpoints are accessible
- [ ] Can run evaluation via API
- [ ] Can retrieve and compare results
- [ ] Error handling works correctly
- [ ] API tests pass

### Task 9: Run Initial Evaluation
**Duration**: 1 hour  
**Steps**:
1. Run evaluation for all 4 systems:
   - Vector-only baseline
   - Hybrid baseline
   - Rerank baseline
   - Full multi-agent system
2. Save results to `data/evaluation/results/initial_comparison_2026-05-15.json`
3. Analyze results:
   - Compare precision/recall/F1 across systems
   - Identify queries where each system performs best
   - Calculate average latency and cost
4. Document findings in `docs/evaluation_results.md`
5. Create summary table for README

**Verification**:
- [ ] Evaluation completes for all 4 systems
- [ ] Results are saved to JSON
- [ ] Metrics show expected improvements (full > rerank > hybrid > vector-only)
- [ ] Findings are documented

## Testing Strategy

### Unit Tests
- Test each baseline retriever independently
- Test metric calculation functions with known inputs
- Test data model validation
- Mock external dependencies (vector store, LLM)

### Integration Tests
- Test end-to-end evaluation flow
- Test API endpoints with real retrievers
- Test result persistence and retrieval

### Manual Testing
- Spot check retrieval results for sample queries
- Verify metric calculations manually for 2-3 queries
- Test API endpoints with curl

## Acceptance Criteria

- [ ] Three baseline systems implemented and tested
- [ ] Evaluation service calculates all required metrics
- [ ] Demo dataset prepared and ingested (6 documents)
- [ ] Test query set created (25 queries with ground truth)
- [ ] API endpoints functional and tested
- [ ] Initial evaluation completed for all 4 systems
- [ ] Results show expected performance hierarchy: full > rerank > hybrid > vector-only
- [ ] All unit and integration tests pass
- [ ] Code follows project style (type hints, docstrings, error handling)
- [ ] Documentation updated (README, API docs)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| BM25 index build is slow for large corpus | Medium | Cache index to disk, build incrementally |
| Cross-encoder reranking adds significant latency | Medium | Only rerank top 20 candidates, use smaller model |
| Ground truth annotation is subjective | Low | Use clear relevance criteria, document edge cases |
| Test queries don't cover all use cases | Low | Include diverse query types, iterate based on findings |

## Dependencies

- Existing vector store and embeddings
- `rank-bm25` library for BM25 implementation
- `sentence-transformers` for cross-encoder model
- Demo documents (to be prepared)

## Next Steps

After completing this plan:
1. Proceed to Plan 2: Agent Execution Flow Visualization
2. Use evaluation results to validate improvements in Plans 3 and 4
3. Integrate evaluation metrics into performance dashboard
