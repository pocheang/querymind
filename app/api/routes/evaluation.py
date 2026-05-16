"""API endpoints for evaluation."""

import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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


def get_retriever(system_name: str):
    """Get retriever instance by system name.
    
    Note: This is a placeholder. In a real implementation, this would
    return actual retriever instances configured with the vectorstore,
    BM25 index, and reranking model.
    """
    # TODO: Implement actual retriever instantiation
    # This requires:
    # 1. Access to the Chroma vectorstore
    # 2. BM25 index for hybrid search
    # 3. Reranking model for rerank baseline
    
    raise HTTPException(
        status_code=501,
        detail=f"Retriever instantiation not yet implemented. "
               f"Please use the evaluation module directly for now."
    )


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
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                raise HTTPException(
                    status_code=400,
                    detail="No matching queries found"
                )
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
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(
            status_code=404,
            detail=f"Results not found for run_id: {run_id}"
        )

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
        raise HTTPException(status_code=500, detail=str(e))


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
