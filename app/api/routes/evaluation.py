"""API endpoints for evaluation."""

import json
import logging
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.utils.error_responses import not_found, bad_request, internal_error, not_implemented
from app.core.config import get_settings
from app.retrievers.hybrid_retriever import hybrid_search_with_diagnostics
from app.retrievers.vector_store import similarity_search
from app.evaluation.models import RetrievalResult

from app.evaluation import (
    TestQuery,
    EvaluationMetrics,
    SystemComparison,
    EvaluationService,
    load_test_queries,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


# Request/Response models
class RunEvaluationRequest(BaseModel):
    system: str  # "vector_only", "hybrid", "rerank"
    queries: Optional[List[str]] = None  # Optional: specific query IDs
    query_file: str = "data/evaluation/demo_queries.json"


class RunEvaluationResponse(BaseModel):
    run_id: str
    system: str
    status: str
    metrics: Optional[EvaluationMetrics] = None
    message: str


class CompareSystemsRequest(BaseModel):
    systems: List[str]  # List of system names to compare
    query_file: str = "data/evaluation/demo_queries.json"


class EvaluationMetricsResponse(BaseModel):
    precision_at_5: float
    recall_at_5: float
    f1_at_5: float
    mrr: float
    ndcg_at_5: float
    avg_latency_ms: float
    total_queries: int


class SystemComparisonResponse(BaseModel):
    system_name: str
    metrics: EvaluationMetricsResponse


class SimpleRetriever:
    """Simple retriever wrapper for evaluation."""

    def __init__(self, system_name: str):
        """Initialize retriever with system configuration.

        Args:
            system_name: "vector_only", "hybrid", or "rerank"
        """
        self.system_name = system_name
        self.settings = get_settings()

    def retrieve(self, query: str, query_id: str = "") -> RetrievalResult:
        """Retrieve documents for a query.

        Args:
            query: Query text
            query_id: Optional query ID for tracking

        Returns:
            RetrievalResult with retrieved document IDs and latency
        """
        start_time = time.time()

        try:
            if self.system_name == "vector_only":
                # Pure vector search
                results = similarity_search(
                    query=query,
                    top_k=self.settings.vector_top_k or 10,
                    allowed_sources=None
                )
                retrieved_docs = [doc.get("source", "") for doc in results]

            elif self.system_name == "hybrid":
                # Hybrid search without reranking
                results, _ = hybrid_search_with_diagnostics(
                    query=query,
                    allowed_sources=None,
                    retrieval_strategy="baseline"  # No reranking
                )
                retrieved_docs = [doc.get("source", "") for doc in results]

            elif self.system_name == "rerank":
                # Hybrid search with reranking
                results, _ = hybrid_search_with_diagnostics(
                    query=query,
                    allowed_sources=None,
                    retrieval_strategy="advanced"  # With reranking
                )
                retrieved_docs = [doc.get("source", "") for doc in results]

            else:
                raise ValueError(f"Unknown system: {self.system_name}")

            latency_ms = (time.time() - start_time) * 1000

            return RetrievalResult(
                query_id=query_id,
                query=query,
                retrieved_docs=retrieved_docs,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Retrieval failed for query '{query}': {e}")
            # Return empty result on error
            latency_ms = (time.time() - start_time) * 1000
            return RetrievalResult(
                query_id=query_id,
                query=query,
                retrieved_docs=[],
                latency_ms=latency_ms
            )

    def batch_retrieve(
        self,
        queries: List[tuple[str, str]]
    ) -> List[RetrievalResult]:
        """Retrieve documents for multiple queries.

        Args:
            queries: List of (query_text, query_id) tuples

        Returns:
            List of RetrievalResult objects
        """
        results = []
        for query_text, query_id in queries:
            result = self.retrieve(query_text, query_id)
            results.append(result)
        return results


def get_retriever(system_name: str):
    """Get retriever instance by system name.

    Args:
        system_name: "vector_only", "hybrid", or "rerank"

    Returns:
        SimpleRetriever instance configured for the system

    Raises:
        HTTPException: If system name is invalid
    """
    valid_systems = ["vector_only", "hybrid", "rerank"]

    if system_name not in valid_systems:
        raise bad_request(
            f"Unknown system: {system_name}. "
            f"Available systems: {', '.join(valid_systems)}"
        )

    return SimpleRetriever(system_name)


@router.get("/queries", response_model=List[TestQuery])
async def list_queries(
    query_file: str = "data/evaluation/demo_queries.json",
    category: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """
    List all test queries.
    
    Args:
        query_file: Path to test query JSON file
        category: Optional category filter
        difficulty: Optional difficulty filter

    Returns:
        List of test queries
    """
    try:
        queries = load_test_queries(query_file)
        
        if category:
            queries = [q for q in queries if q.category == category]
        
        if difficulty:
            queries = [q for q in queries if q.difficulty == difficulty]
        
        return queries
    except FileNotFoundError as e:
        raise not_found(str(e))
    except Exception as e:
        logger.error(f"Error loading queries: {e}")
        raise internal_error(str(e))


@router.post("/run", response_model=RunEvaluationResponse)
async def run_evaluation(request: RunEvaluationRequest):
    """
    Run evaluation on a specified system.

    Args:
        request: RunEvaluationRequest with system name and optional query IDs

    Returns:
        RunEvaluationResponse with metrics and run ID
        
    Note: This endpoint requires retriever implementation to be completed.
    """
    try:
        # Load test queries
        all_queries = load_test_queries(request.query_file)

        # Filter queries if specific IDs provided
        if request.queries:
            queries = [q for q in all_queries if q.id in request.queries]
            if not queries:
                raise bad_request("No matching queries found")
        else:
            queries = all_queries

        # Get retriever (currently not implemented)
        retriever = get_retriever(request.system)

        # Run evaluation
        logger.info(f"Running evaluation for {request.system} on {len(queries)} queries")
        service = EvaluationService()
        eval_run = service.evaluate_system(retriever, queries, request.system)

        # Save results
        results_dir = Path("data/evaluation/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        results_path = results_dir / f"{eval_run.run_id}.json"

        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(eval_run.model_dump(), f, indent=2)

        return RunEvaluationResponse(
            run_id=eval_run.run_id,
            system=request.system,
            status="completed",
            metrics=eval_run.metrics,
            message=f"Evaluation completed successfully on {len(queries)} queries"
        )

    except FileNotFoundError as e:
        raise not_found(str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")
        raise internal_error(str(e))


@router.get("/results/{run_id}")
async def get_results(run_id: str):
    """
    Get evaluation results by run ID.

    Args:
        run_id: Run ID from previous evaluation

    Returns:
        Evaluation results
    """
    results_path = Path(f"data/evaluation/results/{run_id}.json")

    if not results_path.exists():
        raise not_found(f"Results not found for run_id: {run_id}")

    with open(results_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@router.post("/compare", response_model=List[SystemComparisonResponse])
async def compare_systems(request: CompareSystemsRequest):
    """
    Compare multiple systems.

    Args:
        request: CompareSystemsRequest with list of system names

    Returns:
        List of SystemComparison with comparative metrics
        
    Note: This endpoint requires retriever implementation to be completed.
    """
    try:
        # Load test queries
        queries = load_test_queries(request.query_file)

        # Get retrievers for each system
        retrievers = {}
        for system_name in request.systems:
            logger.info(f"Loading retriever for {system_name}...")
            retrievers[system_name] = get_retriever(system_name)

        # Run comparison
        service = EvaluationService()
        comparisons = service.compare_systems(retrievers, queries)

        # Convert to response format
        return [
            SystemComparisonResponse(
                system_name=comp.system_name,
                metrics=EvaluationMetricsResponse(**comp.metrics.model_dump())
            )
            for comp in comparisons
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing systems: {e}")
        raise internal_error(str(e))


@router.get("/systems")
async def list_systems():
    """
    List available retrieval systems for evaluation.

    Returns:
        Dictionary of available system names
    """
    return {
        "systems": ["vector_only", "hybrid", "rerank"],
        "count": 3,
        "note": "Retriever instantiation not yet implemented. Use evaluation module directly."
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "evaluation",
        "timestamp": datetime.now().isoformat()
    }
