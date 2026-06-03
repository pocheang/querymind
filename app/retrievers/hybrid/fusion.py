def rrf_score(rank: int, k: int) -> float:
    """Calculate Reciprocal Rank Fusion score."""
    return 1.0 / (k + rank)


def hybrid_weights(settings) -> tuple[float, float]:
    """Get normalized vector and BM25 weights from settings."""
    vector_weight = float(getattr(settings, "hybrid_vector_weight", 0.95) or 0.95)
    bm25_weight = float(getattr(settings, "hybrid_bm25_weight", 0.05) or 0.05)
    total = vector_weight + bm25_weight
    if total <= 0:
        return 0.95, 0.05
    return vector_weight / total, bm25_weight / total


def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion for combining vector and BM25 results.

    Args:
        vector_results: Results from vector search
        bm25_results: Results from BM25 search
        k: RRF constant (default: 60)

    Returns:
        Fused results sorted by RRF score
    """
    from collections import defaultdict

    scores = defaultdict(float)
    doc_map = {}

    # Process vector results
    for rank, doc in enumerate(vector_results, start=1):
        doc_id = _get_doc_id(doc)
        scores[doc_id] += rrf_score(rank, k)
        if doc_id not in doc_map:
            doc_map[doc_id] = doc

    # Process BM25 results
    for rank, doc in enumerate(bm25_results, start=1):
        doc_id = _get_doc_id(doc)
        scores[doc_id] += rrf_score(rank, k)
        if doc_id not in doc_map:
            doc_map[doc_id] = doc

    # Create fused results with RRF scores
    fused = []
    for doc_id, score in scores.items():
        doc = dict(doc_map[doc_id])
        doc['hybrid_score'] = score
        fused.append(doc)

    # Sort by RRF score descending
    fused.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)

    return fused


def _get_doc_id(doc: dict) -> str:
    """Get unique document ID for deduplication."""
    metadata = doc.get('metadata', {})
    source = metadata.get('source', '')
    chunk_idx = metadata.get('chunk_index', '')

    if source:
        return f"{source}_{chunk_idx}"

    # Fallback to text hash
    text = doc.get('text', '') or doc.get('content', '')
    return f"text_{hash(text)}"
