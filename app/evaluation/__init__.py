"""Evaluation module for comparing retrieval system performance."""

from app.evaluation.models import (
    TestQuery,
    RetrievalResult,
    EvaluationMetrics,
    QueryEvaluation,
    SystemComparison,
    EvaluationRun,
)
from app.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    f1_at_k,
    reciprocal_rank,
    mean_reciprocal_rank,
    ndcg_at_k,
    calculate_all_metrics,
)
from app.evaluation.service import EvaluationService
from app.evaluation.data_loader import (
    load_test_queries,
    save_test_queries,
    filter_queries_by_category,
    filter_queries_by_difficulty,
)

__all__ = [
    # Models
    "TestQuery",
    "RetrievalResult",
    "EvaluationMetrics",
    "QueryEvaluation",
    "SystemComparison",
    "EvaluationRun",
    # Metrics
    "precision_at_k",
    "recall_at_k",
    "f1_at_k",
    "reciprocal_rank",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "calculate_all_metrics",
    # Service
    "EvaluationService",
    # Data loading
    "load_test_queries",
    "save_test_queries",
    "filter_queries_by_category",
    "filter_queries_by_difficulty",
]
