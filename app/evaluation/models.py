"""Pydantic models for evaluation data structures."""

from pydantic import BaseModel, Field


class TestQuery(BaseModel):
    """Test query with ground truth annotations."""

    id: str = Field(..., description="Unique query identifier")
    query: str = Field(..., description="Query text")
    category: str = Field(..., description="Query category (e.g., enterprise_hr, technical)")
    # Source identifiers, not document ids. Every baseline puts
    # `metadata["source"]` into `RetrievalResult.retrieved_docs`, and scoring is a
    # set membership test against this list, so an entry written as a document id
    # matches nothing -- and scores 0.0 forever, which looks exactly like a
    # retrieval failure.
    expected_docs: list[str] = Field(default_factory=list, description="Expected source identifiers")
    # Optional graded judgements, source -> grade. 0 means judged and not
    # relevant, which is not the same as unjudged: it lets a corpus record a
    # near-miss without it counting toward recall. `expected_docs` stays the
    # simple form and every existing query set keeps working -- see
    # `graded_relevance`, which is the one place the two are reconciled.
    #
    # Worth having because the shipped corpus is single-gold, which caps
    # Precision@5 at 0.2 and leaves it unable to say anything about *ordering*.
    # nDCG over grades is the metric with range once judgements exist.
    relevance: dict[str, float] = Field(
        default_factory=dict,
        description="Optional source -> relevance grade (0 = not relevant, higher = more relevant)",
    )
    difficulty: str = Field(default="medium", description="Query difficulty: easy, medium, hard")

    def graded_relevance(self) -> dict[str, float]:
        """The judgements for this query, whichever form they were written in.

        `expected_docs` contributes grade 1 for anything `relevance` does not
        already mention, so a query may carry both: the list for the documents
        that are simply relevant, the map for the ones worth grading. An explicit
        0 in the map wins, which is how a document is marked judged-irrelevant.
        """

        graded = {source: float(grade) for source, grade in self.relevance.items()}
        for source in self.expected_docs:
            graded.setdefault(source, 1.0)
        return graded


class RetrievalResult(BaseModel):
    """Result from a single retrieval operation."""

    query_id: str = Field(..., description="Query identifier")
    query_text: str = Field(..., description="Original query text")
    retrieved_docs: list[str] = Field(default_factory=list, description="Retrieved document IDs")
    scores: list[float] = Field(default_factory=list, description="Relevance scores")
    latency_ms: float = Field(..., description="Retrieval latency in milliseconds")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


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
    retrieved_docs: list[str]
    relevant_docs: list[str]


class SystemComparison(BaseModel):
    """Comparative metrics across multiple systems."""

    system_name: str = Field(..., description="System identifier")
    metrics: EvaluationMetrics = Field(..., description="Aggregated metrics")
    query_results: list[QueryEvaluation] = Field(default_factory=list, description="Per-query results")


class EvaluationRun(BaseModel):
    """Complete evaluation run results."""

    run_id: str = Field(..., description="Unique run identifier")
    system_name: str = Field(..., description="System being evaluated")
    timestamp: str = Field(..., description="ISO timestamp of evaluation")
    metrics: EvaluationMetrics = Field(..., description="Aggregated metrics")
    query_results: list[QueryEvaluation] = Field(default_factory=list, description="Per-query results")
    config: dict = Field(default_factory=dict, description="Evaluation configuration")
