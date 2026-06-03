"""
Optimized RAG Pipeline for v0.4.4 accuracy improvements.

Integrates all speed-optimized components:
- 3-path parallel retrieval (300ms)
- Fast single-model reranking (200ms)
- Rule-based compression (50ms)
- Adaptive strategy routing
- Multi-level caching

Target: 25-35% accuracy improvement with <1.5s response time
"""

import asyncio
import logging
import time
from typing import Optional

from app.retrievers.multi_path_retriever import MultiPathRetriever
from app.retrievers.fast_reranker import FastReranker
from app.services.rule_compressor import RuleBasedCompressor
from app.services.adaptive_strategy import AdaptiveStrategyRouter
from app.services.tracing import traced_span

logger = logging.getLogger(__name__)


class OptimizedRAGPipeline:
    """
    Optimized RAG pipeline with speed/accuracy balance.

    Pipeline stages:
    1. Query complexity analysis (1ms)
    2. Adaptive strategy selection (0ms)
    3. Multi-path retrieval (300ms, parallel)
    4. Fast reranking (200ms, GPU)
    5. Rule-based compression (50ms)
    6. Answer generation (600ms, streaming)

    Total target: 800-1200ms (depending on strategy)
    """

    def __init__(
        self,
        enable_3_path: bool = True,
        enable_fast_rerank: bool = True,
        enable_compression: bool = True,
        enable_dynamic_routing: bool = True,
        enable_cache: bool = True,
    ):
        """
        Initialize optimized pipeline.

        Args:
            enable_3_path: Enable 3-path retrieval
            enable_fast_rerank: Enable fast reranking
            enable_compression: Enable rule-based compression
            enable_dynamic_routing: Enable adaptive strategy routing
            enable_cache: Enable multi-level caching
        """
        self.enable_3_path = enable_3_path
        self.enable_fast_rerank = enable_fast_rerank
        self.enable_compression = enable_compression
        self.enable_dynamic_routing = enable_dynamic_routing
        self.enable_cache = enable_cache

        # Initialize components
        self.retriever = MultiPathRetriever() if enable_3_path else None
        self.reranker = FastReranker() if enable_fast_rerank else None
        self.compressor = RuleBasedCompressor() if enable_compression else None
        self.router = AdaptiveStrategyRouter() if enable_dynamic_routing else None

        # Cache (simple in-memory for now)
        self.cache: dict[str, tuple] = {}

    async def query(
        self,
        query: str,
        allowed_sources: Optional[list[str]] = None,
        strategy: str = "auto",
        top_k: int = 10,
    ) -> dict:
        """
        Execute optimized RAG query.

        Args:
            query: User query
            allowed_sources: Optional source filter
            strategy: Strategy to use ("auto", "fast", "standard", "precise")
            top_k: Number of final documents to return

        Returns:
            Query results with context, citations, and diagnostics
        """
        pipeline_start = time.time()
        stage_timings = {}

        with traced_span("pipeline.optimized_rag", {"strategy": strategy}):
            # Check cache first
            if self.enable_cache:
                cache_key = self._get_cache_key(query, allowed_sources, strategy)
                if cache_key in self.cache:
                    cached_result, cache_time = self.cache[cache_key]
                    logger.info(f"Cache hit for query (age: {time.time() - cache_time:.1f}s)")
                    cached_result["cache_hit"] = True
                    cached_result["total_time_ms"] = round((time.time() - pipeline_start) * 1000, 2)
                    return cached_result

            # Stage 1: Adaptive strategy routing
            if self.enable_dynamic_routing and strategy == "auto":
                t0 = time.time()
                strategy_name, strategy_config = self.router.route(query)
                stage_timings["routing"] = round((time.time() - t0) * 1000, 2)
            else:
                strategy_name = strategy if strategy != "auto" else "standard"
                strategy_config = self.router.get_strategy_config(strategy_name) if self.router else {}

            logger.info(f"Executing pipeline with strategy: {strategy_name}")

            # Stage 2: Multi-path retrieval
            t0 = time.time()
            if self.enable_3_path and self.retriever:
                retrieved_docs, retrieval_diag = await self.retriever.retrieve(
                    query=query,
                    top_k=50,  # Get more candidates for reranking
                    allowed_sources=allowed_sources,
                )
            else:
                # Fallback to hybrid search
                from app.retrievers.hybrid_retriever import hybrid_search_with_diagnostics
                retrieved_docs, retrieval_diag = hybrid_search_with_diagnostics(
                    query,
                    allowed_sources=allowed_sources,
                )

            stage_timings["retrieval"] = round((time.time() - t0) * 1000, 2)

            # Stage 3: Fast reranking
            if self.enable_fast_rerank and self.reranker:
                t0 = time.time()

                # Get rerank config from strategy
                rerank_candidates = strategy_config.get("rerank_candidates", 30)

                reranked_docs, rerank_diag = self.reranker.rerank(
                    query=query,
                    documents=retrieved_docs,
                    top_k=top_k,
                    pre_filter_k=rerank_candidates,
                )
                stage_timings["reranking"] = round((time.time() - t0) * 1000, 2)
            else:
                # Skip reranking
                reranked_docs = retrieved_docs[:top_k]
                rerank_diag = {"status": "disabled"}
                stage_timings["reranking"] = 0

            # Stage 4: Rule-based compression
            if self.enable_compression and self.compressor:
                t0 = time.time()

                compression_ratio = strategy_config.get("compression_ratio", 0.6)
                max_length = int(4000 * (1 / compression_ratio))  # Adjust target based on ratio

                compressed_docs, compress_diag = self.compressor.compress(
                    query=query,
                    documents=reranked_docs,
                    max_length=max_length,
                )
                stage_timings["compression"] = round((time.time() - t0) * 1000, 2)
            else:
                # Skip compression
                compressed_docs = reranked_docs
                compress_diag = {"status": "disabled"}
                stage_timings["compression"] = 0

            # Stage 5: Format context and citations
            context = self._format_context(compressed_docs)
            citations = self._extract_citations(compressed_docs)

            # Compile results
            total_time = time.time() - pipeline_start

            result = {
                "context": context,
                "citations": citations,
                "retrieved_count": len(retrieved_docs),
                "reranked_count": len(reranked_docs),
                "final_count": len(compressed_docs),
                "strategy_used": strategy_name,
                "strategy_config": strategy_config,
                "cache_hit": False,
                "diagnostics": {
                    "total_time_ms": round(total_time * 1000, 2),
                    "stage_timings": stage_timings,
                    "retrieval": retrieval_diag,
                    "reranking": rerank_diag,
                    "compression": compress_diag,
                },
            }

            # Cache result
            if self.enable_cache:
                cache_key = self._get_cache_key(query, allowed_sources, strategy)
                self.cache[cache_key] = (result, time.time())

                # Simple cache eviction (keep last 1000 entries)
                if len(self.cache) > 1000:
                    # Remove oldest 20%
                    oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])[:200]
                    for key in oldest_keys:
                        del self.cache[key]

            logger.info(
                f"Pipeline completed in {result['diagnostics']['total_time_ms']}ms: "
                f"Retrieved {result['retrieved_count']} → "
                f"Reranked {result['reranked_count']} → "
                f"Final {result['final_count']} docs"
            )

            return result

    def _get_cache_key(self, query: str, allowed_sources: Optional[list[str]], strategy: str) -> str:
        """Generate cache key for query."""
        sources_key = ",".join(sorted(allowed_sources)) if allowed_sources else "all"
        return f"{query}|{sources_key}|{strategy}"

    def _format_context(self, documents: list[dict]) -> str:
        """Format documents into context string."""
        parts = []

        for i, doc in enumerate(documents, 1):
            text = doc.get("text", "") or doc.get("content", "")
            source = doc.get("metadata", {}).get("source", f"Document {i}")

            # Format: [Source] Text
            parts.append(f"[{i}. {source}]\n{text}")

        return "\n\n".join(parts)

    def _extract_citations(self, documents: list[dict]) -> list[dict]:
        """Extract citation information from documents."""
        citations = []

        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})

            citation = {
                "index": i,
                "source": metadata.get("source", f"Document {i}"),
                "score": doc.get("rerank_score", doc.get("score", 0)),
                "chunk_index": metadata.get("chunk_index"),
                "retrieval_path": doc.get("retrieval_path"),
                "path_count": doc.get("path_count", 1),
            }

            citations.append(citation)

        return citations

    def clear_cache(self):
        """Clear the query cache."""
        self.cache.clear()
        logger.info("Pipeline cache cleared")

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": 1000,
            "utilization": round(len(self.cache) / 1000 * 100, 1),
        }


# Global pipeline instance
_pipeline: Optional[OptimizedRAGPipeline] = None


def get_optimized_pipeline(
    enable_3_path: bool = True,
    enable_fast_rerank: bool = True,
    enable_compression: bool = True,
    enable_dynamic_routing: bool = True,
    enable_cache: bool = True,
) -> OptimizedRAGPipeline:
    """
    Get or create global optimized pipeline instance.

    Args:
        enable_3_path: Enable 3-path retrieval
        enable_fast_rerank: Enable fast reranking
        enable_compression: Enable rule-based compression
        enable_dynamic_routing: Enable adaptive strategy routing
        enable_cache: Enable caching

    Returns:
        OptimizedRAGPipeline instance
    """
    global _pipeline

    if _pipeline is None:
        _pipeline = OptimizedRAGPipeline(
            enable_3_path=enable_3_path,
            enable_fast_rerank=enable_fast_rerank,
            enable_compression=enable_compression,
            enable_dynamic_routing=enable_dynamic_routing,
            enable_cache=enable_cache,
        )

    return _pipeline


async def optimized_query(
    query: str,
    allowed_sources: Optional[list[str]] = None,
    strategy: str = "auto",
    top_k: int = 10,
) -> dict:
    """
    Convenience function for optimized RAG query.

    Args:
        query: User query
        allowed_sources: Optional source filter
        strategy: Strategy to use ("auto", "fast", "standard", "precise")
        top_k: Number of final documents to return

    Returns:
        Query results with context, citations, and diagnostics
    """
    pipeline = get_optimized_pipeline()
    return await pipeline.query(query, allowed_sources, strategy, top_k)
