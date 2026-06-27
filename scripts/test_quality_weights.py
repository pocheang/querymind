"""
A/B Testing script for quality score fusion weight optimization.

Tests different weight configurations and measures correlation with human judgments.
"""

import sys
import os
import statistics
from typing import List, Dict, Any, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.golden_dataset import get_dataset
from app.agents.quality_orchestrator_agent import orchestrate_quality
from app.agents.quality_models import (
    RouteValidationResult,
    RetrievalQualityResult,
    RetrievalQualityMetrics,
    AnswerValidationResult,
    AnswerValidationDetails
)


def calculate_correlation(predicted_scores: List[float], human_scores: List[float]) -> float:
    """
    Calculate Pearson correlation coefficient between predicted and human scores.

    Args:
        predicted_scores: Model-predicted quality scores
        human_scores: Human-judged quality scores

    Returns:
        Pearson correlation coefficient [-1.0, 1.0]
    """
    if len(predicted_scores) != len(human_scores):
        raise ValueError("Score lists must have the same length")

    if len(predicted_scores) < 2:
        raise ValueError("Need at least 2 data points for correlation")

    n = len(predicted_scores)

    # Calculate means
    mean_pred = statistics.mean(predicted_scores)
    mean_human = statistics.mean(human_scores)

    # Calculate covariance and standard deviations
    covariance = sum((predicted_scores[i] - mean_pred) * (human_scores[i] - mean_human)
                     for i in range(n)) / n

    std_pred = statistics.stdev(predicted_scores)
    std_human = statistics.stdev(human_scores)

    # Handle edge case of zero standard deviation
    if std_pred == 0 or std_human == 0:
        return 0.0

    # Pearson correlation
    correlation = covariance / (std_pred * std_human)

    return correlation


def simulate_quality_score(
    query_data: Dict[str, Any],
    route_weight: float,
    retrieval_weight: float,
    fact_weight: float,
    quality_weight: float,
    citation_weight: float
) -> float:
    """
    Simulate quality score for a query using given weights.

    Simulates validation results based on query complexity and category,
    then applies the specified weights to calculate overall quality score.
    """
    complexity = query_data["complexity"]
    category = query_data["category"]
    expected_route = query_data["expected_route"]

    # Simulate scores based on query characteristics
    # Higher complexity → lower scores
    complexity_factor = {"simple": 1.0, "medium": 0.9, "complex": 0.8}[complexity]

    # Route confidence depends on query clarity
    route_confidence = 0.9 * complexity_factor if complexity == "simple" else 0.8 * complexity_factor

    # Retrieval quality varies by category
    category_retrieval = {
        "factual": 0.88,
        "analytical": 0.82,
        "procedural": 0.80,
        "comparative": 0.78
    }
    retrieval_quality = category_retrieval[category] * complexity_factor

    # Answer scores
    factual_consistency = 0.90 * complexity_factor if category == "factual" else 0.82 * complexity_factor
    answer_quality_score = 0.85 * complexity_factor
    citation_completeness = 0.88 * complexity_factor if category in ["factual", "analytical"] else 0.75 * complexity_factor

    # Create mock validation results
    route_validation = RouteValidationResult(
        is_valid=True,
        confidence=route_confidence,
        validation_method="rule_fast",
        validation_reason="Simulated validation",
        execution_time_ms=10,
        warnings=[]
    )

    metrics = RetrievalQualityMetrics(
        coverage_score=retrieval_quality * 0.95,
        relevance_score=retrieval_quality * 1.02,
        diversity_score=retrieval_quality * 0.92,
        completeness_score=retrieval_quality * 0.98
    )

    retrieval_result = RetrievalQualityResult(
        overall_quality=retrieval_quality,
        metrics=metrics,
        execution_time_ms=20,
        issues=[],
        suggestions=[]
    )

    validation_details = AnswerValidationDetails(
        factual_consistency=factual_consistency,
        answer_quality=answer_quality_score,
        citation_completeness=citation_completeness,
        hallucination_risk=0.1,
        safety_score=0.95
    )

    answer_validation = AnswerValidationResult(
        is_valid=True,
        overall_score=0.85,
        validation_details=validation_details,
        issues=[],
        action="approve",
        execution_time_ms=30,
        validation_method="standard"
    )

    # Calculate weighted score manually (without penalties for simulation)
    overall_score = (
        route_confidence * route_weight +
        retrieval_quality * retrieval_weight +
        factual_consistency * fact_weight +
        answer_quality_score * quality_weight +
        citation_completeness * citation_weight
    )

    return round(max(0.0, min(1.0, overall_score)), 3)


def run_ab_test() -> Dict[str, Any]:
    """
    Run A/B test comparing current weights vs alternative weights.

    Returns:
        Dictionary containing test results and correlations
    """
    dataset = get_dataset()

    # Current weights: Route 15%, Retrieval 25%, Fact 40%, Quality 15%, Cite 5%
    current_weights = {
        "route": 0.15,
        "retrieval": 0.25,
        "fact": 0.40,
        "quality": 0.15,
        "citation": 0.05
    }

    # Alternative weights: Route 10%, Retrieval 30%, Fact 45%, Quality 10%, Cite 5%
    alternative_weights = {
        "route": 0.10,
        "retrieval": 0.30,
        "fact": 0.45,
        "quality": 0.10,
        "citation": 0.05
    }

    # Collect human scores
    human_scores = [item["human_quality_score"] for item in dataset]

    # Calculate predicted scores with current weights
    current_predicted = []
    for item in dataset:
        score = simulate_quality_score(
            item,
            current_weights["route"],
            current_weights["retrieval"],
            current_weights["fact"],
            current_weights["quality"],
            current_weights["citation"]
        )
        current_predicted.append(score)

    # Calculate predicted scores with alternative weights
    alternative_predicted = []
    for item in dataset:
        score = simulate_quality_score(
            item,
            alternative_weights["route"],
            alternative_weights["retrieval"],
            alternative_weights["fact"],
            alternative_weights["quality"],
            alternative_weights["citation"]
        )
        alternative_predicted.append(score)

    # Calculate correlations
    current_correlation = calculate_correlation(current_predicted, human_scores)
    alternative_correlation = calculate_correlation(alternative_predicted, human_scores)

    # Calculate mean absolute errors
    current_mae = statistics.mean([abs(current_predicted[i] - human_scores[i])
                                   for i in range(len(dataset))])
    alternative_mae = statistics.mean([abs(alternative_predicted[i] - human_scores[i])
                                       for i in range(len(dataset))])

    results = {
        "current_weights": current_weights,
        "alternative_weights": alternative_weights,
        "current_correlation": current_correlation,
        "alternative_correlation": alternative_correlation,
        "current_mae": current_mae,
        "alternative_mae": alternative_mae,
        "dataset_size": len(dataset),
        "winner": "alternative" if alternative_correlation > current_correlation else "current"
    }

    return results


def print_results(results: Dict[str, Any]) -> None:
    """Print A/B test results in a readable format."""
    print("=" * 80)
    print("QUALITY WEIGHT OPTIMIZATION - A/B TEST RESULTS")
    print("=" * 80)
    print()
    print(f"Dataset Size: {results['dataset_size']} queries")
    print()
    print("CURRENT WEIGHTS:")
    for key, value in results["current_weights"].items():
        print(f"  {key.capitalize():12s}: {value:.2%}")
    print(f"  Correlation: {results['current_correlation']:.4f}")
    print(f"  MAE:         {results['current_mae']:.4f}")
    print()
    print("ALTERNATIVE WEIGHTS:")
    for key, value in results["alternative_weights"].items():
        print(f"  {key.capitalize():12s}: {value:.2%}")
    print(f"  Correlation: {results['alternative_correlation']:.4f}")
    print(f"  MAE:         {results['alternative_mae']:.4f}")
    print()
    print("-" * 80)
    correlation_improvement = results["alternative_correlation"] - results["current_correlation"]
    mae_improvement = results["current_mae"] - results["alternative_mae"]

    print(f"WINNER: {results['winner'].upper()}")
    print(f"Correlation Improvement: {correlation_improvement:+.4f}")
    print(f"MAE Improvement:         {mae_improvement:+.4f}")
    print()

    if results["winner"] == "alternative":
        print("✓ Alternative weights show better correlation with human judgments")
        print("  Recommend updating quality_config.py with alternative weights")
    else:
        print("✓ Current weights already optimal")
        print("  No changes recommended")
    print("=" * 80)


if __name__ == "__main__":
    print("Running A/B test for quality weight optimization...")
    print()

    results = run_ab_test()
    print_results(results)
