"""Evaluation service for comparing RAG system performance."""

import json
import logging
from pathlib import Path
from typing import Any

from app.evaluation.models import EvaluationMetrics, GroundTruth, SystemComparison, TestQuery

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for evaluating and comparing retrieval systems."""

    def __init__(self):
        """Initialize evaluation service."""
        pass

    def precision_at_k(self, retrieved: list[str], relevant: list[str], k: int) -> float:
        """
        Calculate precision@k.

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Cutoff position

        Returns:
            Precision@k score (0-1)
        """
        if not retrieved or k == 0:
            return 0.0

        retrieved_at_k = retrieved[:k]
        relevant_set = set(relevant)
        relevant_retrieved = sum(1 for doc_id in retrieved_at_k if doc_id in relevant_set)

        return relevant_retrieved / k

    def recall_at_k(self, retrieved: list[str], relevant: list[str], k: int) -> float:
        """
        Calculate recall@k.

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs
            k: Cutoff position

        Returns:
            Recall@k score (0-1)
        """
        if not relevant:
            return 0.0

        retrieved_at_k = retrieved[:k]
        relevant_set = set(relevant)
        relevant_retrieved = sum(1 for doc_id in retrieved_at_k if doc_id in relevant_set)

        return relevant_retrieved / len(relevant)

    def f1_at_k(self, precision: float, recall: float) -> float:
        """
        Calculate F1 score from precision and recall.

        Args:
            precision: Precision score
            recall: Recall score

        Returns:
            F1 score (0-1)
        """
        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    def mean_reciprocal_rank(self, retrieved: list[str], relevant: list[str]) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR).

        Args:
            retrieved: List of retrieved document IDs
            relevant: List of relevant document IDs

        Returns:
            MRR score (0-1)
        """
        relevant_set = set(relevant)

        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                return 1.0 / i

        return 0.0

    def ndcg_at_k(self, retrieved: list[str], relevance_scores: dict[str, float], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG@k).

        Args:
            retrieved: List of retrieved document IDs
            relevance_scores: Dict mapping doc_id to relevance score
            k: Cutoff position

        Returns:
            NDCG@k score (0-1)
        """
        if not retrieved or k == 0:
            return 0.0

        # Calculate DCG
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k], 1):
            rel = relevance_scores.get(doc_id, 0.0)
            dcg += rel / (i**0.5)  # log2(i+1) approximation

        # Calculate IDCG (ideal DCG)
        ideal_scores = sorted(relevance_scores.values(), reverse=True)
        idcg = 0.0
        for i, rel in enumerate(ideal_scores[:k], 1):
            idcg += rel / (i**0.5)

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def run_evaluation(
        self,
        system_name: str,
        retriever,
        test_queries: list[TestQuery],
        ground_truth: dict[str, GroundTruth],
        k_values: list[int] = None,
    ) -> EvaluationMetrics:
        """
        Run evaluation on a retrieval system.

        Args:
            system_name: Name of the system being evaluated
            retriever: Retriever instance with retrieve(query, top_k) method
            test_queries: List of test queries
            ground_truth: Dict mapping query_id to ground truth
            k_values: List of k values for metrics

        Returns:
            EvaluationMetrics with aggregated results
        """
        if k_values is None:
            k_values = [1, 3, 5, 10]
        logger.info(f"Starting evaluation for {system_name} on {len(test_queries)} queries")

        precision_at_k = {k: [] for k in k_values}
        recall_at_k = {k: [] for k in k_values}
        f1_at_k = {k: [] for k in k_values}
        ndcg_at_k = {k: [] for k in k_values}
        mrr_scores = []
        latencies = []

        for i, query in enumerate(test_queries, 1):
            if i % 5 == 0:
                logger.info(f"Evaluated {i}/{len(test_queries)} queries")

            try:
                # Retrieve documents
                max_k = max(k_values)
                result = retriever.retrieve(query.query, top_k=max_k)

                # Get retrieved doc IDs
                retrieved_ids = [doc["id"] for doc in result.retrieved_docs]

                # Get ground truth
                gt = ground_truth.get(query.id)
                if not gt:
                    logger.warning(f"No ground truth for query {query.id}")
                    continue

                # Combine highly relevant and relevant docs
                relevant_ids = gt.highly_relevant + gt.relevant

                # Build relevance scores for NDCG
                relevance_scores = {}
                for doc_id in gt.highly_relevant:
                    relevance_scores[doc_id] = 2.0
                for doc_id in gt.relevant:
                    relevance_scores[doc_id] = 1.0

                # Calculate metrics for each k
                for k in k_values:
                    p = self.precision_at_k(retrieved_ids, relevant_ids, k)
                    r = self.recall_at_k(retrieved_ids, relevant_ids, k)
                    f1 = self.f1_at_k(p, r)
                    ndcg = self.ndcg_at_k(retrieved_ids, relevance_scores, k)

                    precision_at_k[k].append(p)
                    recall_at_k[k].append(r)
                    f1_at_k[k].append(f1)
                    ndcg_at_k[k].append(ndcg)

                # Calculate MRR
                mrr = self.mean_reciprocal_rank(retrieved_ids, relevant_ids)
                mrr_scores.append(mrr)

                # Track latency
                latencies.append(result.latency_ms)

            except Exception as e:
                logger.error(f"Error evaluating query {query.id}: {e}")
                continue

        # Aggregate metrics
        avg_precision = {k: sum(scores) / len(scores) if scores else 0.0 for k, scores in precision_at_k.items()}
        avg_recall = {k: sum(scores) / len(scores) if scores else 0.0 for k, scores in recall_at_k.items()}
        avg_f1 = {k: sum(scores) / len(scores) if scores else 0.0 for k, scores in f1_at_k.items()}
        avg_ndcg = {k: sum(scores) / len(scores) if scores else 0.0 for k, scores in ndcg_at_k.items()}
        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        logger.info(f"Evaluation complete for {system_name}")
        logger.info(f"  Precision@5: {avg_precision.get(5, 0.0):.3f}")
        logger.info(f"  Recall@5: {avg_recall.get(5, 0.0):.3f}")
        logger.info(f"  F1@5: {avg_f1.get(5, 0.0):.3f}")
        logger.info(f"  MRR: {avg_mrr:.3f}")
        logger.info(f"  Avg Latency: {avg_latency:.1f}ms")

        return EvaluationMetrics(
            precision_at_k=avg_precision,
            recall_at_k=avg_recall,
            f1_at_k=avg_f1,
            mrr=avg_mrr,
            ndcg_at_k=avg_ndcg,
            avg_latency_ms=avg_latency,
            total_queries=len(test_queries),
        )

    def compare_systems(self, system_results: dict[str, EvaluationMetrics]) -> SystemComparison:
        """
        Compare multiple systems and determine winner.

        Args:
            system_results: Dict mapping system name to metrics

        Returns:
            SystemComparison with comparative analysis
        """
        if not system_results:
            return SystemComparison(systems=[], metrics={})

        # Determine winner based on F1@5
        winner = None
        best_f1 = 0.0

        for system_name, metrics in system_results.items():
            f1_5 = metrics.f1_at_k.get(5, 0.0)
            if f1_5 > best_f1:
                best_f1 = f1_5
                winner = system_name

        # Generate summary
        summary_lines = []
        for system_name, metrics in system_results.items():
            f1_5 = metrics.f1_at_k.get(5, 0.0)
            mrr = metrics.mrr
            latency = metrics.avg_latency_ms
            summary_lines.append(f"{system_name}: F1@5={f1_5:.3f}, MRR={mrr:.3f}, Latency={latency:.1f}ms")

        summary = "\n".join(summary_lines)
        summary += f"\n\nWinner: {winner} (F1@5={best_f1:.3f})"

        return SystemComparison(
            systems=list(system_results.keys()), metrics=system_results, winner=winner, summary=summary
        )

    def save_results(self, results: dict[str, Any], output_path: Path) -> None:
        """
        Save evaluation results to JSON file.

        Args:
            results: Results dictionary
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_path}")
