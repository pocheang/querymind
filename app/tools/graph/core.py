import re

from app.domain.text import normalize_string
from app.graph.knowledge.client import Neo4jClient
from app.services.runtime.bulkhead import bulkhead
from app.services.runtime.resilience import call_with_circuit_breaker

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]{2,}")
_NOISY_RELATIONS = {
    "related",
    # `infer_relation` in the rule triplet extractor returns RELATED_TO whenever
    # no keyword matched, so it is the single most common relation in any graph
    # built without an LLM -- and it was the one shape this set missed, scoring
    # 0.6 instead of 0.0. Listing it drops those edges at *read* time, which is
    # the only mitigation available for graphs already written: Neo4j stores no
    # extraction method, and every existing edge carries the same 0.7 the old
    # code stamped on everything.
    "related_to",
    "\u5173\u8054",
    "\u76f8\u5173",
    "link",
    "links",
    "unknown",
    "\u5176\u4ed6",
}
_ENTITY_ALIASES = {
    "ai": "artificial intelligence",
    "a.i.": "artificial intelligence",
    "llm": "large language model",
    "\u5927\u6a21\u578b": "large language model",
    "\u7f51\u7edc\u5b89\u5168": "cybersecurity",
    "\u8d44\u5b89": "cybersecurity",
}
_RELATION_KEYWORDS = (
    "causes",
    "\u5bfc\u81f4",
    "depends",
    "\u4f9d\u8d56",
    "uses",
    "\u5229\u7528",
    "targets",
    "\u653b\u51fb",
    "mitigates",
    "\u7f13\u89e3",
)


def _normalize_token(token: str) -> str:
    t = normalize_string(token, lowercase=True)
    if not t:
        return ""
    return _ENTITY_ALIASES.get(t, t)


def _normalize_entity_name(name: str) -> str:
    return _normalize_token(name)


def _relation_weight(rel: str) -> float:
    r = normalize_string(rel, lowercase=True)
    if not r:
        return 0.0
    if r in _NOISY_RELATIONS:
        return 0.0
    if any(keyword in r for keyword in _RELATION_KEYWORDS):
        return 1.0
    return 0.6


def _fetch_neighbors(
    client: Neo4jClient, entities_to_lookup: list[str], allowed_sources: list[str] | None
) -> dict[str, list[dict]]:
    if hasattr(client, "batch_entity_neighbors"):
        return call_with_circuit_breaker(
            "neo4j.batch_entity_neighbors",
            lambda: client.batch_entity_neighbors(
                entities_to_lookup,
                limit_per_entity=10,
                allowed_sources=allowed_sources,
            ),
        )

    return {
        entity_name: call_with_circuit_breaker(
            "neo4j.entity_neighbors",
            lambda entity_name=entity_name: client.entity_neighbors(
                entity_name,
                limit=10,
                allowed_sources=allowed_sources,
            ),
        )
        for entity_name in entities_to_lookup
    }


def _fetch_paths(
    client: Neo4jClient, entities_to_lookup: list[str], allowed_sources: list[str] | None
) -> dict[str, list[dict]]:
    if hasattr(client, "batch_entity_paths_2hop"):
        return call_with_circuit_breaker(
            "neo4j.batch_entity_paths_2hop",
            lambda: client.batch_entity_paths_2hop(
                entities_to_lookup,
                limit_per_entity=8,
                allowed_sources=allowed_sources,
            ),
        )

    return {
        entity_name: call_with_circuit_breaker(
            "neo4j.entity_paths_2hop",
            lambda entity_name=entity_name: client.entity_paths_2hop(
                entity_name,
                limit=8,
                allowed_sources=allowed_sources,
            ),
        )
        for entity_name in entities_to_lookup
    }


def _lookup_tokens(question: str, use_robust_extraction: bool | None) -> list[str]:
    """The query terms, from robust extraction when it is on and available.

    Robust extraction is best-effort by design: a failure here means a thinner
    query, not a failed one, so it falls back to the same tokenization the
    legacy path uses rather than propagating.
    """

    from app.core.config import get_settings

    settings = get_settings()
    if use_robust_extraction is None:
        use_robust_extraction = settings.graph_entity_extraction_robust

    if use_robust_extraction:
        try:
            from app.graph.knowledge.entity_extraction import extract_entities

            extracted = extract_entities(question, use_llm=settings.graph_entity_extraction_use_llm)
            return [_normalize_token(e["text"]) for e in extracted if _normalize_token(e["text"])]
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning("Robust entity extraction failed, using fallback: %s", e)

    raw_tokens = TOKEN_PATTERN.findall(question)
    return [_normalize_token(t) for t in raw_tokens if _normalize_token(t)]


def _normalized_entities(entities) -> tuple[list[dict], list[str]]:
    """Entities with their relations cleaned, plus the RAW names to look up.

    The two lists are returned together because they must stay aligned, and
    they are not the same strings: the lookup uses the name as stored, while
    the result carries the normalized one.
    """

    normalized_entities: list[dict] = []
    lookup_entity_names: list[str] = []
    for row in entities:
        raw_entity_name = str(row.get("entity", "")).strip()
        entity_name = _normalize_entity_name(raw_entity_name)
        if not entity_name:
            continue
        normalized_rels = []
        for rel in row.get("relations", []) or []:
            relation = str(rel.get("relation", "")).strip()
            other = _normalize_entity_name(str(rel.get("other", "")).strip())
            weight = _relation_weight(relation)
            if not other or weight <= 0:
                continue
            normalized_rels.append({"relation": relation, "other": other, "weight": weight})
        normalized_entities.append({"entity": entity_name, "relations": normalized_rels})
        lookup_entity_names.append(raw_entity_name)
    return normalized_entities, lookup_entity_names


def _neighbor_rows(client, entities_to_lookup: list[str], allowed_sources) -> list[dict]:
    """One row per distinct (entity, relation, other), noisy relations dropped."""

    rows_out: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for rows in _fetch_neighbors(client, entities_to_lookup, allowed_sources).values():
        for row in rows:
            entity = _normalize_entity_name(str(row.get("entity", "")).strip())
            relation = str(row.get("relation", "")).strip()
            other = _normalize_entity_name(str(row.get("other", "")).strip())
            weight = _relation_weight(relation)
            if not entity or not other or weight <= 0:
                continue
            key = (entity, relation.lower(), other)
            if key in seen:
                continue
            seen.add(key)
            rows_out.append({"entity": entity, "relation": relation, "other": other, "weight": weight})
    return rows_out


def _path_rows(client, entities_to_lookup: list[str], allowed_sources) -> list[dict]:
    """Two-hop paths, weighted by the mean of the two relation weights."""

    rows_out: list[dict] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for paths in _fetch_paths(client, entities_to_lookup, allowed_sources).values():
        for p in paths:
            source = _normalize_entity_name(str(p.get("source", "")).strip())
            middle = _normalize_entity_name(str(p.get("middle", "")).strip())
            target = _normalize_entity_name(str(p.get("target", "")).strip())
            rel1 = str(p.get("rel1", "")).strip()
            rel2 = str(p.get("rel2", "")).strip()
            w1 = _relation_weight(rel1)
            w2 = _relation_weight(rel2)
            if not source or not middle or not target or w1 <= 0 or w2 <= 0:
                continue
            pkey = (source, rel1.lower(), middle, rel2.lower(), target)
            if pkey in seen:
                continue
            seen.add(pkey)
            rows_out.append(
                {
                    "source": source,
                    "rel1": rel1,
                    "middle": middle,
                    "rel2": rel2,
                    "target": target,
                    "weight": (w1 + w2) / 2.0,
                }
            )
    return rows_out


def _mean_weight(rows: list[dict], limit: int) -> float:
    weights = [float(x.get("weight", 0.0)) for x in rows[:limit]]
    return min(1.0, sum(weights) / len(weights)) if weights else 0.0


def _graph_signal_score(entities: list[dict], neighbors: list[dict], paths: list[dict]) -> float:
    """A weighted mean over only the components that produced anything.

    Renormalizing by the weight actually spent is what keeps a graph with no
    paths from scoring lower than one with none *and* no neighbours.
    """

    parts = (
        (entities, 0.3, min(1.0, len(entities) / 4.0)),
        (neighbors, 0.4, _mean_weight(neighbors, 12)),
        (paths, 0.3, _mean_weight(paths, 8)),
    )
    weighted_sum = sum(weight * score for rows, weight, score in parts if rows)
    total_weight = sum(weight for rows, weight, _ in parts if rows)
    return (weighted_sum / total_weight) if total_weight > 0 else 0.0


def graph_lookup(
    question: str, allowed_sources: list[str] | None = None, use_robust_extraction: bool | None = None
) -> dict:
    """
    Look up entities and relationships in the graph.

    Args:
        question: Query string
        allowed_sources: Optional list of allowed document sources
        use_robust_extraction: Use robust multi-stage entity extraction (default: from config)

    Returns:
        Dictionary with entities, neighbors, paths, and graph_signal_score
    """
    tokens = _lookup_tokens(question, use_robust_extraction)

    with bulkhead("neo4j"):
        client = Neo4jClient()
        try:
            entities = call_with_circuit_breaker(
                "neo4j.search_entities",
                lambda: client.search_entities(tokens, limit=8, allowed_sources=allowed_sources),
            )
            normalized_entities, lookup_entity_names = _normalized_entities(entities)

            entities_to_lookup = lookup_entity_names[:3]
            neighbor_rows = _neighbor_rows(client, entities_to_lookup, allowed_sources) if entities_to_lookup else []
            path_rows = _path_rows(client, entities_to_lookup, allowed_sources) if entities_to_lookup else []

            return {
                "entities": normalized_entities,
                "neighbors": neighbor_rows,
                "paths": path_rows,
                "graph_signal_score": _graph_signal_score(normalized_entities, neighbor_rows, path_rows),
            }
        finally:
            client.close()
