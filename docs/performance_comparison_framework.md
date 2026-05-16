# Performance Comparison Framework

A comprehensive evaluation system for comparing different RAG retrieval strategies.

## Overview

The performance comparison framework provides:

- **Evaluation Metrics**: Precision@K, Recall@K, F1@K, MRR, NDCG@K
- **Baseline Retrievers**: Vector-only, Hybrid (Vector+BM25), Rerank
- **Test Query Management**: Load, filter, and manage test queries with ground truth
- **Evaluation Service**: Orchestrate evaluations and compare multiple systems
- **API Endpoints**: RESTful API for running evaluations

## Architecture

```
app/
├── evaluation/
│   ├── models.py          # Pydantic models for evaluation data
│   ├── metrics.py         # Evaluation metric implementations
│   ├── service.py         # Evaluation orchestration service
│   └── data_loader.py     # Utilities for loading test queries
├── baselines/
│   ├── vector_baseline.py # Vector-only retrieval
│   ├── hybrid_baseline.py # Hybrid (Vector + BM25)
│   └── rerank_baseline.py # Reranking with cross-encoder
└── api/routes/
    └── evaluation.py      # API endpoints

data/evaluation/
└── demo_queries.json      # 15 test queries (HR + technical)
```

## Quick Start

### 1. Load Test Queries

```python
from app.evaluation import load_test_queries

queries = load_test_queries('data/evaluation/demo_queries.json')
print(f"Loaded {len(queries)} queries")
```

### 2. Calculate Metrics

```python
from app.evaluation import calculate_all_metrics

retrieved = ['doc1', 'doc2', 'doc3', 'doc4', 'doc5']
relevant = {'doc1', 'doc3', 'doc5'}

metrics = calculate_all_metrics(retrieved, relevant, k=5)
print(f"Precision@5: {metrics['precision']:.3f}")
print(f"Recall@5: {metrics['recall']:.3f}")
print(f"F1@5: {metrics['f1']:.3f}")
```

### 3. Create a Baseline Retriever

```python
from app.baselines import create_vector_baseline

baseline = create_vector_baseline(
    vectorstore=your_chroma_instance,
    k=5,
    score_threshold=0.5
)

result = baseline.retrieve("What are the vacation policies?", "q001")
print(f"Retrieved: {result.retrieved_docs}")
print(f"Latency: {result.latency_ms:.1f}ms")
```

### 4. Run Evaluation

```python
from app.evaluation import EvaluationService

service = EvaluationService(k=5)
eval_run = service.evaluate_system(
    system=baseline,
    test_queries=queries,
    system_name="vector_only"
)

print(f"Precision@5: {eval_run.metrics.precision_at_5:.3f}")
print(f"Recall@5: {eval_run.metrics.recall_at_5:.3f}")
print(f"F1@5: {eval_run.metrics.f1_at_5:.3f}")
print(f"MRR: {eval_run.metrics.mrr:.3f}")
print(f"NDCG@5: {eval_run.metrics.ndcg_at_5:.3f}")
```

### 5. Compare Multiple Systems

```python
systems = {
    "vector_only": vector_baseline,
    "hybrid": hybrid_baseline,
    "rerank": rerank_baseline
}

comparisons = service.compare_systems(systems, queries)
service.print_comparison(comparisons)
```

## Baseline Retrievers

### Vector-Only Baseline

Pure vector similarity search using Chroma.

```python
from app.baselines import create_vector_baseline

baseline = create_vector_baseline(
    vectorstore=chroma_instance,
    k=5,                      # Number of results
    score_threshold=0.5       # Optional minimum score
)
```

### Hybrid Baseline

Combines vector similarity with BM25 keyword search.

```python
from app.baselines import create_hybrid_baseline

baseline = create_hybrid_baseline(
    vectorstore=chroma_instance,
    bm25_index=bm25_index,
    doc_id_map=doc_id_mapping,
    k=5,
    alpha=0.5,                # 0.5 = equal weight for vector and BM25
    score_threshold=None
)
```

**Alpha parameter**:
- `alpha=1.0`: Pure vector search
- `alpha=0.5`: Equal weight (recommended)
- `alpha=0.0`: Pure BM25 search

### Rerank Baseline

Retrieves more candidates, then reranks with a cross-encoder.

```python
from app.baselines import create_rerank_baseline

def rerank_function(query: str, docs: List[str]) -> List[float]:
    # Your cross-encoder reranking logic
    # Return scores for each document
    return scores

baseline = create_rerank_baseline(
    vectorstore=chroma_instance,
    rerank_fn=rerank_function,
    k=5,                      # Final number of results
    initial_k=20,             # Retrieve 20, rerank to top 5
    score_threshold=None
)
```

## Evaluation Metrics

### Precision@K
Fraction of retrieved documents that are relevant.

```
Precision@K = (# relevant docs in top-K) / K
```

### Recall@K
Fraction of relevant documents that were retrieved.

```
Recall@K = (# relevant docs in top-K) / (total # relevant docs)
```

### F1@K
Harmonic mean of Precision@K and Recall@K.

```
F1@K = 2 * (Precision * Recall) / (Precision + Recall)
```

### Mean Reciprocal Rank (MRR)
Average of reciprocal ranks of the first relevant document.

```
RR = 1 / (rank of first relevant doc)
MRR = average(RR) across all queries
```

### NDCG@K
Normalized Discounted Cumulative Gain - considers ranking quality.

```
DCG@K = Σ (relevance / log2(rank + 1))
NDCG@K = DCG@K / Ideal_DCG@K
```

## Test Query Format

Test queries are stored in JSON format with ground truth annotations.

## Demo Dataset

The framework includes 15 demo queries:

- **Enterprise HR** (9 queries): vacation policies, expense reports, remote work, performance reviews, benefits, safety, job transfers
- **Technical** (6 queries): OAuth setup, API rate limits, GraphQL pagination, database migrations, memory debugging, CI setup, API versioning

**Difficulty distribution**:
- Easy: 4 queries
- Medium: 9 queries
- Hard: 2 queries

## Dependencies

- `scikit-learn>=1.3.0` - For NDCG calculation
- `pydantic>=2.8.0` - For data models
- `langchain-chroma>=0.2.0` - For vector search
- `rank-bm25>=0.2.2` - For BM25 search
