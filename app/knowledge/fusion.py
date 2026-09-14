"""Reusable multi-source fusion and reranking stages."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence

from app.domain.contracts import EvidenceItem
from app.knowledge.deduplication import evidence_dedup_key
from app.retrievers.hybrid.fusion import rrf_score
from app.retrievers.reranker import lexical_rerank, rerank_with_diagnostics


def reciprocal_rank_fuse(
    ranked_lists: Iterable[Sequence[EvidenceItem]],
    *,
    rrf_k: int,
) -> tuple[EvidenceItem, ...]:
    """Fuse arbitrary ranked source lists using the established RRF formula."""

    scores: dict[tuple[object, ...], float] = {}
    items: dict[tuple[object, ...], EvidenceItem] = {}
    retrievers: dict[tuple[object, ...], set[str]] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            key = evidence_dedup_key(item)
            scores[key] = scores.get(key, 0.0) + rrf_score(rank, rrf_k)
            retrievers.setdefault(key, set()).update(label for label in item.retriever.split("+") if label)
            current = items.get(key)
            if current is None or _score(item) > _score(current):
                items[key] = item
    fused = [
        items[key].model_copy(
            update={
                "score": min(1.0, score),
                "retriever": "+".join(sorted(retrievers[key])),
            }
        )
        for key, score in scores.items()
    ]
    return tuple(sorted(fused, key=lambda item: item.score or 0.0, reverse=True))


async def rerank_evidence(
    query: str,
    items: Sequence[EvidenceItem],
    *,
    top_n: int,
    timeout_ms: int,
    enabled: bool,
) -> tuple[tuple[EvidenceItem, ...], dict[str, object]]:
    """Run BGE reranking off-loop and use lexical fallback on timeout."""

    if not items:
        return (), {"reranker_backend": "none", "reranker_fallback_reason": "no_candidates"}
    candidates = [_candidate(item) for item in items]
    if not enabled:
        reranked = lexical_rerank(query, candidates, top_n)
        return _restore_items(items, reranked), {
            "reranker_backend": "lexical",
            "reranker_fallback_reason": "disabled",
        }
    try:
        reranked, diagnostics = await asyncio.wait_for(
            asyncio.to_thread(rerank_with_diagnostics, query, candidates, top_n),
            timeout=timeout_ms / 1000,
        )
    except TimeoutError:
        reranked = lexical_rerank(query, candidates, top_n)
        diagnostics = {
            "reranker_backend": "lexical",
            "reranker_fallback_reason": "timeout",
        }
    return _restore_items(items, reranked), diagnostics


def _restore_items(
    items: Sequence[EvidenceItem],
    reranked: Sequence[dict[str, object]],
) -> tuple[EvidenceItem, ...]:
    item_map = {item.item_id: item for item in items}
    output: list[EvidenceItem] = []
    for candidate in reranked:
        item = item_map.get(str(candidate.get("item_id") or ""))
        if item is None:
            continue
        raw_score = candidate.get("rerank_score", candidate.get("hybrid_score", item.score))
        try:
            score = min(1.0, max(0.0, float(raw_score)))
        except (TypeError, ValueError):
            score = item.score
        output.append(item.model_copy(update={"score": score}))
    return tuple(output)


def _candidate(item: EvidenceItem) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "text": item.content,
        "hybrid_score": item.score or 0.0,
    }


def _score(item: EvidenceItem) -> float:
    return item.score if item.score is not None else -1.0


def cross_modal_hybrid_resonance(
    items: Sequence[EvidenceItem],
    *,
    resonance_boost: float = 0.08,
) -> tuple[tuple[EvidenceItem, ...], int]:
    """Identify cross-modal business entities shared between graph triples and tabular data.

    Boosts mutually reinforcing evidence items so linked tabular facts and graph
    topological structures rise to top attention in context assembly.

    Returns:
        tuple[fused_items, match_count]
    """
    if not items:
        return (), 0

    from app.graph.knowledge.table_linking import detect_graph_table_overlap

    # Separate graph and table evidence
    graph_indices = [i for i, item in enumerate(items) if item.modality == "graph"]
    table_indices = [i for i, item in enumerate(items) if item.modality == "table"]

    if not graph_indices or not table_indices:
        return tuple(items), 0

    boosted_items = list(items)
    matched_pairs = 0

    # Cross-check graph items against table items
    for g_idx in graph_indices:
        g_item = boosted_items[g_idx]
        for t_idx in table_indices:
            t_item = boosted_items[t_idx]
            overlap = detect_graph_table_overlap(g_item.content, t_item.content)
            if overlap:
                matched_pairs += 1
                # Apply resonance boost to both items
                g_score = min(1.0, (g_item.score or 0.0) + resonance_boost)
                t_score = min(1.0, (t_item.score or 0.0) + resonance_boost)
                boosted_items[g_idx] = g_item.model_copy(update={"score": g_score})
                boosted_items[t_idx] = t_item.model_copy(update={"score": t_score})

    if matched_pairs > 0:
        # Re-sort preserving relative order of ties
        boosted_items.sort(key=lambda item: item.score or 0.0, reverse=True)

    return tuple(boosted_items), matched_pairs


__all__ = ["reciprocal_rank_fuse", "rerank_evidence", "cross_modal_hybrid_resonance"]
