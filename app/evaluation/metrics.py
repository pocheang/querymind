"""Evaluation metrics for retrieval systems."""

import numpy as np
from sklearn.metrics import ndcg_score


def precision_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    """Calculate Precision@K.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        Precision@K score (0.0 to 1.0)
    """
    if not retrieved or k == 0:
        return 0.0

    retrieved_at_k = retrieved[:k]
    relevant_retrieved = sum(1 for doc in retrieved_at_k if doc in relevant)
    return relevant_retrieved / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    """Calculate Recall@K.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        Recall@K score (0.0 to 1.0)
    """
    if not relevant:
        return 0.0

    retrieved_at_k = retrieved[:k]
    relevant_retrieved = sum(1 for doc in retrieved_at_k if doc in relevant)
    return relevant_retrieved / len(relevant)


def f1_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    """Calculate F1@K.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        F1@K score (0.0 to 1.0)
    """
    precision = precision_at_k(retrieved, relevant, k)
    recall = recall_at_k(retrieved, relevant, k)

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    """Calculate Reciprocal Rank.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs

    Returns:
        Reciprocal rank (0.0 to 1.0)
    """
    for i, doc in enumerate(retrieved, 1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(results: list[tuple[list[str], set[str]]]) -> float:
    """Calculate Mean Reciprocal Rank across multiple queries.

    Args:
        results: List of (retrieved, relevant) tuples

    Returns:
        Mean reciprocal rank (0.0 to 1.0)
    """
    if not results:
        return 0.0

    rr_scores = [reciprocal_rank(retrieved, relevant) for retrieved, relevant in results]
    return sum(rr_scores) / len(rr_scores)


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int = 5) -> float:
    """Calculate Normalized Discounted Cumulative Gain@K.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        NDCG@K score (0.0 to 1.0)
    """
    if not retrieved or not relevant:
        return 0.0

    # Create binary relevance labels (1 if relevant, 0 otherwise)
    retrieved_at_k = retrieved[:k]
    relevance_scores = [1 if doc in relevant else 0 for doc in retrieved_at_k]

    # If no relevant documents in top-k, return 0
    if sum(relevance_scores) == 0:
        return 0.0

    # Pad to k if needed
    while len(relevance_scores) < k:
        relevance_scores.append(0)

    # Create ideal ranking (all relevant docs first)
    ideal_scores = sorted(relevance_scores, reverse=True)

    # sklearn expects 2D arrays
    y_true = np.array([ideal_scores])
    y_score = np.array([relevance_scores])

    return ndcg_score(y_true, y_score)


def calculate_all_metrics(retrieved: list[str], relevant: set[str], k: int = 5) -> dict:
    """Calculate all evaluation metrics for a single query.

    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: Set of relevant document IDs
        k: Number of top results to consider

    Returns:
        Dictionary with all metric scores
    """
    return {
        "precision": precision_at_k(retrieved, relevant, k),
        "recall": recall_at_k(retrieved, relevant, k),
        "f1": f1_at_k(retrieved, relevant, k),
        "reciprocal_rank": reciprocal_rank(retrieved, relevant),
        "ndcg": ndcg_at_k(retrieved, relevant, k),
    }
