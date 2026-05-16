"""API endpoints for evaluation."""

import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.evaluation.models import TestQuery, GroundTruth, EvaluationMetrics, SystemComparison
from app.evaluation.services.evaluation_service import EvaluationService
from app.evaluation.baselines.vector_only import VectorOnlyRetriever
from app.evaluation.baselines.hybrid import HybridRetriever
from app.evaluation.baselines.rerank import RerankRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


# Request/Response models
class RunEvaluationRequest(BaseModel):
    system: str  # "vector_only", "hybrid", "rerank", "full"
    queries: Optional[List[str]] = None  # Optional: specific query IDs


class RunEvaluationResponse(BaseModel):
    run_id: str
    system: str
    status: str
    metrics: Optional[EvaluationMetrics] = None
    message: str


class CompareSystemsRequest(BaseModel):
    systems: List[str]  # List of system names to compare


# Load test queries and ground truth
def load_test_queries() -> List[TestQuery]:
    """Load test queries from JSON file."""
    queries_path = Path("data/demo/evaluation/test_queries.json")
    if not queries_path.exists():
        raise FileNotFoundError(f"Test queries not found at {queries_path}")

    with open(queries_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return [TestQuery(**q) for q in data]


def load_ground_truth() -> dict:
    """Load ground truth from JSON file."""
    gt_path = Path("data/demo/evaluation/ground_truth.json")
    if not gt_path.exists():
        raise FileNotFoundError(f"Ground truth not found at {gt_path}")

    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return {qid: GroundTruth(query_id=qid, **gt_data)
            for qid, gt_data in data.items()}


def get_retriever(system_name: str):
    """Get retriever instance by system name."""
    if system_name == "vector_only":
        return VectorOnlyRetriever()
    elif system_name == "hybrid":
        return HybridRetriever()
    elif system_name == "rerank":
        return RerankRetriever()
    elif system_name == "full":
        # TODO: Implement full multi-agent system retriever
        raise HTTPException(
            status_code=501,
            detail="Full multi-agent system not yet implemented"
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown system: {system_name}"
        )


@router.post("/run", response_model=RunEvaluationResponse)
async def run_evaluation(request: RunEvaluationRequest):
    """
    Run evaluation on a specified system.

    Args:
        request: RunEvaluationRequest with system name and optional query IDs

    Returns:
        RunEvaluationResponse with metrics and run ID
    """
    try:
        # Load test data
        all_queries = load_test_queries()
        ground_truth = load_ground_truth()

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

        # Get retriever
        retriever = get_retriever(request.system)

        # Run evaluation
        logger.info(f"Running evaluation for {request.system} on {len(queries)} queries")
        service = EvaluationService()
        metrics = service.run_evaluation(
            system_name=request.system,
            retriever=retriever,
            test_queries=queries,
            ground_truth=ground_truth
        )

        # Generate run ID
        run_id = f"{request.system}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Save results
        results_dir = Path("data/evaluation/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        results_path = results_dir / f"{run_id}.json"

        service.save_results(
            {
                "run_id": run_id,
                "system": request.system,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics.model_dump(),
                "num_queries": len(queries)
            },
            results_path
        )

        return RunEvaluationResponse(
            run_id=run_id,
            system=request.system,
            status="completed",
            metrics=metrics,
            message=f"Evaluation completed successfully on {len(queries)} queries"
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
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


@router.post("/compare", response_model=SystemComparison)
async def compare_systems(request: CompareSystemsRequest):
    """
    Compare multiple systems.

    Args:
        request: CompareSystemsRequest with list of system names

    Returns:
        SystemComparison with comparative metrics
    """
    try:
        # Load test data
        queries = load_test_queries()
        ground_truth = load_ground_truth()

        # Run evaluation for each system
        service = EvaluationService()
        system_results = {}

        for system_name in request.systems:
            logger.info(f"Evaluating {system_name}...")
            retriever = get_retriever(system_name)
            metrics = service.run_evaluation(
                system_name=system_name,
                retriever=retriever,
                test_queries=queries,
                ground_truth=ground_truth
            )
            system_results[system_name] = metrics

        # Compare systems
        comparison = service.compare_systems(system_results)

        return comparison

    except Exception as e:
        logger.error(f"Error comparing systems: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries", response_model=List[TestQuery])
async def list_queries():
    """
    List all test queries.

    Returns:
        List of test queries
    """
    try:
        queries = load_test_queries()
        return queries
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "evaluation",
        "timestamp": datetime.now().isoformat()
    }
