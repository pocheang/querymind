"""Rerank baseline retriever (Hybrid + Cross-encoder)."""

import time
from typing import List, Dict, Any

from app.evaluation.baselines.hybrid import HybridRetriever
from app.retrievers.reranker import rerank
from app.evaluation.models import RetrievalResult


class RerankRetriever:
    """Two-stage retrieval: Hybrid search + cross-encoder reranking."""

    def __init__(self, hybrid_retriever: HybridRetriever = None):
        """
        Initialize rerank retriever.

        Args:
            hybrid_retriever: Hybrid retriever instance (creates new if None)
        """
        self.hybrid_retriever = hybrid_retriever or HybridRetriever()

    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """
        Retrieve documents using two-stage retrieval.

        Stage 1: Hybrid search (retrieve top 20 candidates)
        Stage 2: Cross-encoder rerank (select top_k)

        Args:
            query: Query text
            top_k: Number of documents to retrieve

        Returns:
            RetrievalResult with retrieved documents and metadata
        """
        start_time = time.time()

        # Stage 1: Hybrid retrieval (get more candidates)
        candidate_k = max(top_k * 4, 20)  # Get 4x candidates or at least 20
        hybrid_result = self.hybrid_retriever.retrieve(query, top_k=candidate_k)

        stage1_time = (time.time() - start_time) * 1000

        # Prepare candidates for reranking
        candidates = []
        for doc in hybrid_result.retrieved_docs:
            candidates.append({
                "text": doc["content"],
                "metadata": doc["metadata"],
                "hybrid_score": 0.0  # Not used by reranker
            })

        # Stage 2: Rerank with cross-encoder
        rerank_start = time.time()
        reranked = rerank(query, candidates, top_n=top_k)
        stage2_time = (time.time() - rerank_start) * 1000

        total_latency_ms = (time.time() - start_time) * 1000

        # Format results
        retrieved_docs = []
        scores = []

        for item in reranked:
            retrieved_docs.append({
                "id": item["metadata"].get("id", ""),
                "content": item["text"],
                "metadata": item["metadata"],
                "source": item["metadata"].get("source", "")
            })
            scores.append(float(item.get("rerank_score", 0.0)))

        return RetrievalResult(
            query_id="",  # Will be set by evaluation service
            query=query,
            retrieved_docs=retrieved_docs,
            scores=scores,
            latency_ms=total_latency_ms,
            metadata={
                "retriever": "rerank",
                "stage1_latency_ms": stage1_time,
                "stage2_latency_ms": stage2_time,
                "candidate_k": candidate_k,
                "top_k": top_k
            }
        )
