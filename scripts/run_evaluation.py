"""
Run evaluation on all baseline systems and compare results.

This script:
1. Loads test queries and ground truth
2. Runs evaluation on vector-only, hybrid, and rerank baselines
3. Compares results and saves to JSON
4. Prints summary table
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from app.evaluation.models import TestQuery, GroundTruth
from app.evaluation.services.evaluation_service import EvaluationService
from app.evaluation.baselines.vector_only import VectorOnlyRetriever
from app.evaluation.baselines.hybrid import HybridRetriever
from app.evaluation.baselines.rerank import RerankRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_test_queries() -> list[TestQuery]:
    """Load test queries from JSON file."""
    queries_path = Path("data/demo/evaluation/test_queries.json")
    with open(queries_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [TestQuery(**q) for q in data]


def load_ground_truth() -> dict:
    """Load ground truth from JSON file."""
    gt_path = Path("data/demo/evaluation/ground_truth.json")
    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {qid: GroundTruth(query_id=qid, **gt_data)
            for qid, gt_data in data.items()}


def print_summary_table(system_results: dict):
    """Print formatted summary table."""
    print("\n" + "="*80)
    print("EVALUATION RESULTS SUMMARY")
    print("="*80)
    print(f"{'System':<20} {'P@5':<10} {'R@5':<10} {'F1@5':<10} {'MRR':<10} {'Latency(ms)':<15}")
    print("-"*80)

    for system_name, metrics in system_results.items():
        p5 = metrics.precision_at_k.get(5, 0.0)
        r5 = metrics.recall_at_k.get(5, 0.0)
        f1_5 = metrics.f1_at_k.get(5, 0.0)
        mrr = metrics.mrr
        latency = metrics.avg_latency_ms

        print(f"{system_name:<20} {p5:<10.3f} {r5:<10.3f} {f1_5:<10.3f} {mrr:<10.3f} {latency:<15.1f}")

    print("="*80)


def main():
    """Run evaluation on all systems."""
    logger.info("Starting evaluation...")

    # Load test data
    logger.info("Loading test queries and ground truth...")
    queries = load_test_queries()
    ground_truth = load_ground_truth()
    logger.info(f"Loaded {len(queries)} test queries")

    # Initialize evaluation service
    service = EvaluationService()

    # Define systems to evaluate
    systems = {
        "vector_only": VectorOnlyRetriever(),
        "hybrid": HybridRetriever(),
        "rerank": RerankRetriever()
    }

    # Run evaluation for each system
    system_results = {}

    for system_name, retriever in systems.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating: {system_name}")
        logger.info(f"{'='*60}")

        try:
            metrics = service.run_evaluation(
                system_name=system_name,
                retriever=retriever,
                test_queries=queries,
                ground_truth=ground_truth
            )
            system_results[system_name] = metrics

        except Exception as e:
            logger.error(f"Error evaluating {system_name}: {e}")
            continue

    # Compare systems
    logger.info("\nComparing systems...")
    comparison = service.compare_systems(system_results)

    # Print summary
    print_summary_table(system_results)
    print(f"\nWinner: {comparison.winner}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("data/evaluation/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    output_path = results_dir / f"comparison_{timestamp}.json"

    results = {
        "timestamp": datetime.now().isoformat(),
        "num_queries": len(queries),
        "systems": list(system_results.keys()),
        "metrics": {name: metrics.model_dump()
                   for name, metrics in system_results.items()},
        "comparison": comparison.model_dump()
    }

    service.save_results(results, output_path)
    logger.info(f"\nResults saved to: {output_path}")

    # Also save as latest
    latest_path = results_dir / "latest_comparison.json"
    service.save_results(results, latest_path)
    logger.info(f"Latest results saved to: {latest_path}")


if __name__ == "__main__":
    main()
