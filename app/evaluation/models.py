"""Pydantic models for evaluation data."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TestQuery(BaseModel):
    """Test query with ground truth."""
    id: str
    query: str
    category: str
    expected_docs: List[str]
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")


class RetrievalResult(BaseModel):
    """Result from a retrieval operation."""
    query_id: str
    query: str
    retrieved_docs: List[Dict[str, Any]]
    scores: List[float]
    latency_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for a system."""
    precision_at_k: Dict[int, float]
    recall_at_k: Dict[int, float]
    f1_at_k: Dict[int, float]
    mrr: float
    ndcg_at_k: Dict[int, float]
    avg_latency_ms: float
    total_queries: int


class SystemComparison(BaseModel):
    """Comparison of multiple systems."""
    systems: List[str]
    metrics: Dict[str, EvaluationMetrics]
    winner: Optional[str] = None
    summary: str = ""


class GroundTruth(BaseModel):
    """Ground truth relevance judgments."""
    query_id: str
    highly_relevant: List[str] = Field(default_factory=list)
    relevant: List[str] = Field(default_factory=list)
    not_relevant: List[str] = Field(default_factory=list)
