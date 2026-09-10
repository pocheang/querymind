from app.retrievers.stores.parent import get_parent_text_map


def _collect_parent_ids(candidates: list[dict]) -> list[str]:
    parent_ids: list[str] = []
    for item in candidates:
        parent_id = str((item.get("metadata", {}) or {}).get("parent_id", "")).strip()
        if parent_id:
            parent_ids.append(parent_id)
    return parent_ids


def _replace_expanded_entry(
    expanded: list[dict],
    parent_id: str,
    item: dict,
    current_score: float,
    metadata: dict,
    parent_map: dict,
) -> bool:
    """Swap in a higher-scoring duplicate's context for the entry already kept.

    Returns whether a matching entry was found and replaced.
    """
    for idx, existing in enumerate(expanded):
        if existing.get("metadata", {}).get("parent_id") != parent_id:
            continue
        updated = dict(item)
        updated["child_text"] = item.get("text", "")
        if parent_map.get(parent_id):
            updated["text"] = parent_map[parent_id]
            metadata["context_granularity"] = "parent"
        else:
            metadata["context_granularity"] = "child"
        updated["metadata"] = metadata
        updated["hybrid_score"] = current_score
        updated["dense_score"] = item.get("dense_score")
        updated["bm25_score"] = item.get("bm25_score")
        updated["rerank_score"] = item.get("rerank_score")
        updated["rank_feature_score"] = item.get("rank_feature_score")
        updated["retrieval_sources"] = item.get("retrieval_sources", [])
        expanded[idx] = updated
        return True
    return False


def _handle_duplicate(
    expanded: list[dict],
    parent_id: str,
    item: dict,
    current_score: float,
    metadata: dict,
    parent_map: dict,
    parent_score_map: dict[str, float],
) -> None:
    """A repeat of a dedupe key: swap in this candidate's context only if it outscores the kept one."""
    if not (parent_id and current_score > parent_score_map.get(parent_id, 0.0)):
        return
    if _replace_expanded_entry(expanded, parent_id, item, current_score, metadata, parent_map):
        parent_score_map[parent_id] = current_score


def _new_expanded_entry(item: dict, parent_id: str, metadata: dict, parent_map: dict) -> dict:
    merged = dict(item)
    if parent_id and parent_map.get(parent_id):
        merged["child_text"] = item.get("text", "")
        merged["text"] = parent_map[parent_id]
        metadata["context_granularity"] = "parent"
    else:
        metadata["context_granularity"] = "child"
    merged["metadata"] = metadata
    return merged


def expand_to_parent_context(candidates: list[dict], *, parent_text_map_fn=None) -> list[dict]:
    """Expand child chunks to parent context while deduplicating.

    ``parent_text_map_fn`` lets a caller substitute the parent-text lookup for
    one call; it defaults to this module's own.  Callers previously achieved the
    same effect by reassigning this module's global, which raced across
    concurrent requests.
    """
    _parent_text_map = parent_text_map_fn or get_parent_text_map
    parent_map = _parent_text_map(_collect_parent_ids(candidates))

    expanded: list[dict] = []
    seen: set[str] = set()
    parent_score_map: dict[str, float] = {}

    for item in candidates:
        metadata = dict(item.get("metadata", {}) or {})
        parent_id = str(metadata.get("parent_id", "")).strip()
        dedupe_key = parent_id or str(item.get("id", ""))

        current_score = item.get("hybrid_score", 0.0)
        if dedupe_key in seen:
            _handle_duplicate(expanded, parent_id, item, current_score, metadata, parent_map, parent_score_map)
            continue

        seen.add(dedupe_key)
        if parent_id:
            parent_score_map[parent_id] = current_score
        expanded.append(_new_expanded_entry(item, parent_id, metadata, parent_map))
    return expanded
