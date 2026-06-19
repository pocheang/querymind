"""
Vector RAG Agent - Document retrieval and context assembly.

Optimizations:
- Uses centralized configuration
- Improved type hints
- Better error handling
- Performance logging
"""

import logging
from pathlib import Path

from app.agents.agent_config import (
    CHUNK_PREVIEW_LENGTH,
    DENSE_SCORE_THRESHOLD,
    MIN_CHUNK_LENGTH,
)
from app.core.config import get_settings
from app.retrievers.hybrid_retriever import hybrid_search_with_diagnostics
from app.services.agent_document_filter import get_sources_by_agent_class

logger = logging.getLogger(__name__)


def run_vector_rag(
    question: str,
    allowed_sources: list[str] | None = None,
    retrieval_strategy: str | None = None,
    agent_class: str | None = None,
) -> dict:
    """
    Run vector-based RAG retrieval and context assembly.

    Args:
        question: User query
        allowed_sources: Optional list of allowed document sources
        retrieval_strategy: Retrieval strategy ("hybrid", "dense", "bm25", "rerank")
        agent_class: Agent class for automatic document filtering

    Returns:
        Dictionary containing:
        - context: Formatted context string
        - citations: List of citation dictionaries
        - retrieved_count: Number of chunks retrieved
        - effective_hit_count: Number of high-quality hits
        - retrieval_diagnostics: Diagnostic information
    """
    settings = get_settings()

    # Auto-apply agent document filtering
    if allowed_sources is None and agent_class:
        allowed_sources = get_sources_by_agent_class(agent_class)
        logger.debug(f"Applied agent filter for {agent_class}: {len(allowed_sources or [])} sources")

    try:
        results, diagnostics = hybrid_search_with_diagnostics(
            question,
            allowed_sources=allowed_sources,
            retrieval_strategy=retrieval_strategy,
        )
    except TypeError:
        # Backward-compatible fallback for monkeypatched/stubbed signatures in tests
        logger.warning("Falling back to legacy hybrid_search_with_diagnostics signature")
        results, diagnostics = hybrid_search_with_diagnostics(
            question,
            allowed_sources=allowed_sources,
        )

    citations = []
    context_blocks = []
    effective_hit_count = 0

    for item in results[: settings.max_context_chunks]:
        metadata = item.get("metadata", {})
        src_full = str(metadata.get("source", "unknown"))
        src = Path(src_full).name if src_full else "unknown"
        chunk = item.get("text", "")[:CHUNK_PREVIEW_LENGTH]

        retrieval_sources = item.get("retrieval_sources", [])
        if not isinstance(retrieval_sources, list):
            retrieval_sources = [str(retrieval_sources)]

        citations.append(
            {
                "source": src,
                "content": chunk,
                "metadata": {
                    **metadata,
                    "dense_score": item.get("dense_score"),
                    "bm25_score": item.get("bm25_score"),
                    "hybrid_score": item.get("hybrid_score"),
                    "rerank_score": item.get("rerank_score"),
                    "rank_feature_score": item.get("rank_feature_score"),
                    "retrieval_sources": retrieval_sources,
                },
            }
        )

        context_blocks.append(
            f"[SOURCE: {src}]\n"
            f"[RETRIEVAL: {','.join(retrieval_sources)}]\n"
            f"{chunk}"
        )

        # Evidence gating: count high-quality hits
        # Prefer score-backed hits, but keep unknown-score hits valid
        dense_score = item.get("dense_score")
        bm25_score = item.get("bm25_score")
        rerank_score = item.get("rerank_score")
        has_valid_score = False

        if isinstance(rerank_score, (int, float)) and float(rerank_score) > 0:
            effective_hit_count += 1
            has_valid_score = True
        elif isinstance(dense_score, (int, float)) and float(dense_score) >= DENSE_SCORE_THRESHOLD:
            effective_hit_count += 1
            has_valid_score = True
        elif isinstance(bm25_score, (int, float)) and float(bm25_score) > 0:
            effective_hit_count += 1
            has_valid_score = True

        # Count unknown-score items if they have valid text content
        if not has_valid_score and len(chunk.strip()) >= MIN_CHUNK_LENGTH:
            effective_hit_count += 1

    logger.info(
        f"Vector RAG retrieved {len(citations)} chunks, {effective_hit_count} effective hits"
    )

    return {
        "context": "\n\n".join(context_blocks),
        "citations": citations,
        "retrieved_count": len(citations),
        "effective_hit_count": effective_hit_count,
        "retrieval_diagnostics": diagnostics,
    }
