"""Pydantic models for evaluation data structures."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class TestQuery(BaseModel):
    """Test query with ground truth annotations."""

    id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Query text")
    category: str = Field(..., description="Query category (e.g., enterprise_hr, technical)")
    expected_docs: List[str] = Field(default_factory=list, description="Expected document IDs")
    difficulty: str = Field(default="medium", description="Query difficulty: easy, medium, hard")


class RetrievalResult(BaseModel):
    """Result from a single retrieval operation."""

    query_id: str = Field(..., description="Query identifier")
    query_text: str = Field(..., description="Original query text")
    retrieved_docs: List[str] = Field(default_factory=list, description="Retrieved document IDs")
    scores: List[float] = Field(default_factory=list, description="Relevance scores")
    latency_ms: float = Field(..., description="Retrieval latency in milliseconds")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata")


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for a retrieval system."""

    precision_at_5: float = Field(..., description="Precision@5")
    recall_at_5: float = Field(..., description="Recall@5")
    f1_at_5: float = Field(..., description="F1@5")
    mrr: float = Field(..., description="Mean Reciprocal Rank")
    ndcg_at_5: float = Field(..., description="NDCG@5")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    total_queries: int = Field(..., description="Total number of queries evaluated")


class QueryEvaluation(BaseModel):
    """Evaluation results for a single query."""

    query_id: str
    precision: float
    recall: float
    f1: float
    reciprocal_rank: float
    ndcg: float
    latency_ms: float
    retrieved_docs: List[str]
    relevant_docs: List[str]


class SystemComparison(BaseModel):
    """Comparative metrics across multiple systems."""

    system_name: str = Field(..., description="System identifier")
    metrics: EvaluationMetrics = Field(..., description="Aggregated metrics")
    query_results: List[QueryEvaluation] = Field(default_factory=list, description="Per-query results")


class EvaluationRun(BaseModel):
    """Complete evaluation run results."""

    run_id: str = Field(..., description="Unique run identifier")
    system_name: str = Field(..., description="System being evaluated")
    timestamp: str = Field(..., description="ISO timestamp of evaluation")
    metrics: EvaluationMetrics = Field(..., description="Aggregated metrics")
    query_results: List[QueryEvaluation] = Field(default_factory=list, description="Per-query results")
    config: Dict = Field(default_factory=dict, description="Evaluation configuration")
