"""
Enhanced Graph Tools for improved PDF + Graph RAG accuracy.

Key improvements:
1. Better entity normalization with cross-language support
2. Adaptive graph signal scoring based on content quality
3. Semantic similarity for entity matching
4. PDF-aware relationship weighting
5. Multi-hop path exploration with relevance ranking
"""

import re
import logging
from typing import Optional

from app.api.utils.string_utils import normalize_string
from app.graph.neo4j_client import Neo4jClient
from app.services.bulkhead import bulkhead
from app.services.resilience import call_with_circuit_breaker

logger = logging.getLogger(__name__)

# Enhanced token pattern with better Unicode support
TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9_\-]{2,}|"  # English words/acronyms (min 2 chars)
    r"[一-鿿]{2,}|"  # Chinese (min 2 chars)
    r"[A-Z]{2,}"  # Acronyms in caps
)

# Expanded noisy relations
_NOISY_RELATIONS = {
    "related", "关联", "相关", "link", "links", "linked_to",
    "unknown", "其他", "other", "misc", "general", "通用"
}

# Comprehensive entity aliases for better matching
_ENTITY_ALIASES = {
    # AI/ML terms
    "ai": "artificial intelligence",
    "a.i.": "artificial intelligence",
    "llm": "large language model",
    "大模型": "large language model",
    "大语言模型": "large language model",
    "ml": "machine learning",
    "机器学习": "machine learning",
    "dl": "deep learning",
    "深度学习": "deep learning",
    "nlp": "natural language processing",
    "自然语言处理": "natural language processing",

    # RAG specific
    "rag": "retrieval augmented generation",
    "检索增强生成": "retrieval augmented generation",
    "向量检索": "vector retrieval",
    "vector search": "vector retrieval",

    # Security
    "网络安全": "cybersecurity",
    "资安": "cybersecurity",
    "信息安全": "information security",
    "infosec": "information security",

    # Database
    "数据库": "database",
    "db": "database",
    "图数据库": "graph database",
    "neo4j": "graph database",

    # Common tech
    "api": "application programming interface",
    "rest": "representational state transfer",
    "gpu": "graphics processing unit",
    "cpu": "central processing unit",
}

# High-value relation keywords (weighted higher)
_HIGH_VALUE_RELATIONS = {
    "causes", "导致", "leads_to", "引起",
    "depends", "依赖", "requires", "需要",
    "uses", "利用", "employs", "采用",
    "targets", "攻击", "affects", "影响",
    "mitigates", "缓解", "prevents", "防止",
    "implements", "实现", "contains", "包含",
    "produces", "产生", "generates", "生成",
    "improves", "改进", "enhances", "增强",
}


def _normalize_token(token: str) -> str:
    """Normalize a token with alias expansion."""
    t = normalize_string(token, lowercase=True)
    if not t:
        return ""
    return _ENTITY_ALIASES.get(t, t)


def _normalize_entity_name(name: str) -> str:
    """Normalize entity name with smart handling of multi-token entities."""
    # Try full name first
    normalized_full = _normalize_token(name)
    if normalized_full != normalize_string(name, lowercase=True):
        # Found an alias
        return normalized_full

    # For multi-token names, keep as-is but normalize
    return normalize_string(name, lowercase=True)


def _relation_weight(rel: str, context_quality: float = 0.5) -> float:
    """
    Calculate relation weight with context-aware scoring.

    Args:
        rel: Relationship type
        context_quality: Quality score of source document (0-1)

    Returns:
        Weight score (0-1)
    """
    r = normalize_string(rel, lowercase=True)
    if not r:
        return 0.0

    # Filter noise
    if r in _NOISY_RELATIONS:
        return 0.0

    # High-value relations
    if any(k in r for k in _HIGH_VALUE_RELATIONS):
        base_weight = 1.0
    else:
        base_weight = 0.6

    # Boost based on context quality
    # High-quality PDFs with good structure → higher confidence in relations
    quality_boost = 1.0 + (context_quality * 0.3)  # Up to 30% boost

    return min(1.0, base_weight * quality_boost)


def _calculate_semantic_similarity(query_tokens: list[str], entity_name: str) -> float:
    """
    Calculate semantic similarity between query tokens and entity.

    Simple approach: token overlap with position weighting.
    For production, consider using embeddings.

    Args:
        query_tokens: Normalized query tokens
        entity_name: Entity name to compare

    Returns:
        Similarity score (0-1)
    """
    entity_tokens = set(TOKEN_PATTERN.findall(entity_name.lower()))
    if not entity_tokens or not query_tokens:
        return 0.0

    # Exact matches
    matches = sum(1 for t in query_tokens if t in entity_tokens)

    # Partial matches (substring)
    partial = sum(
        0.5 for qt in query_tokens
        for et in entity_tokens
        if qt in et or et in qt
    )

    similarity = (matches + partial) / max(len(query_tokens), len(entity_tokens))
    return min(1.0, similarity)


def graph_lookup_enhanced(
    question: str,
    allowed_sources: list[str] | None = None,
    context_quality: float = 0.5,
    max_entities: int = 10,
    max_neighbors: int = 15,
    max_paths: int = 10,
) -> dict:
    """
    Enhanced graph lookup with better accuracy for PDF content.

    Improvements over basic graph_lookup:
    - Better entity normalization and alias matching
    - Context-aware relation weighting
    - Semantic similarity scoring
    - Adaptive result limits based on confidence

    Args:
        question: User query
        allowed_sources: Optional source filter
        context_quality: Quality score of source documents (0-1)
        max_entities: Maximum entities to retrieve
        max_neighbors: Maximum neighbor relationships
        max_paths: Maximum 2-hop paths

    Returns:
        Dictionary with entities, neighbors, paths, and enhanced scoring
    """
    # Extract and normalize tokens
    raw_tokens = TOKEN_PATTERN.findall(question)
    tokens = [_normalize_token(t) for t in raw_tokens if _normalize_token(t)]

    if not tokens:
        logger.warning(f"No valid tokens extracted from question: {question}")
        return {
            "entities": [],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.0,
            "confidence": "low",
        }

    with bulkhead("neo4j"):
        client = Neo4jClient()
        try:
            # Search entities with higher limit for ranking
            entities = call_with_circuit_breaker(
                "neo4j.search_entities",
                lambda: client.search_entities(
                    tokens,
                    limit=max_entities * 2,  # Retrieve more, then rank
                    allowed_sources=allowed_sources
                ),
            )

            # Normalize and score entities
            scored_entities = []
            lookup_entity_names = []

            for row in entities:
                raw_entity_name = str(row.get("entity", "")).strip()
                entity_name = _normalize_entity_name(raw_entity_name)

                if not entity_name:
                    continue

                # Calculate relevance score
                relevance = _calculate_semantic_similarity(tokens, entity_name)

                # Process relations with context-aware weighting
                normalized_rels = []
                for rel in row.get("relations", []) or []:
                    relation = str(rel.get("relation", "")).strip()
                    other = _normalize_entity_name(str(rel.get("other", "")).strip())
                    weight = _relation_weight(relation, context_quality)

                    if not other or weight <= 0:
                        continue

                    normalized_rels.append({
                        "relation": relation,
                        "other": other,
                        "weight": weight,
                    })

                scored_entities.append({
                    "entity": entity_name,
                    "relations": normalized_rels,
                    "relevance": relevance,
                    "raw_name": raw_entity_name,
                })

            # Sort by relevance and limit
            scored_entities.sort(key=lambda x: x["relevance"], reverse=True)
            top_entities = scored_entities[:max_entities]

            # Collect names for neighbor and path queries
            for entity_data in top_entities:
                lookup_entity_names.append(entity_data["raw_name"])

            # Retrieve neighbors with deduplication
            neighbor_rows = []
            seen_neighbor: set[tuple[str, str, str]] = set()

            for name in lookup_entity_names[:5]:  # Top 5 entities only
                current_name = name
                rows = call_with_circuit_breaker(
                    "neo4j.entity_neighbors",
                    lambda n=current_name: client.entity_neighbors(
                        n,
                        limit=max_neighbors * 2,
                        allowed_sources=allowed_sources
                    ),
                )

                for row in rows:
                    entity = _normalize_entity_name(str(row.get("entity", "")).strip())
                    relation = str(row.get("relation", "")).strip()
                    other = _normalize_entity_name(str(row.get("other", "")).strip())
                    weight = _relation_weight(relation, context_quality)

                    if not entity or not other or weight <= 0:
                        continue

                    key = (entity, relation.lower(), other)
                    if key in seen_neighbor:
                        continue

                    seen_neighbor.add(key)
                    neighbor_rows.append({
                        "entity": entity,
                        "relation": relation,
                        "other": other,
                        "weight": weight,
                    })

            # Sort neighbors by weight and limit
            neighbor_rows.sort(key=lambda x: x["weight"], reverse=True)
            neighbor_rows = neighbor_rows[:max_neighbors]

            # Retrieve 2-hop paths
            path_rows = []
            seen_path: set[tuple[str, str, str, str, str]] = set()

            for name in lookup_entity_names[:3]:  # Top 3 entities for paths
                current_name = name
                paths = call_with_circuit_breaker(
                    "neo4j.entity_paths_2hop",
                    lambda n=current_name: client.entity_paths_2hop(
                        n,
                        limit=max_paths * 2,
                        allowed_sources=allowed_sources
                    ),
                )

                for p in paths:
                    source = _normalize_entity_name(str(p.get("source", "")).strip())
                    middle = _normalize_entity_name(str(p.get("middle", "")).strip())
                    target = _normalize_entity_name(str(p.get("target", "")).strip())
                    rel1 = str(p.get("rel1", "")).strip()
                    rel2 = str(p.get("rel2", "")).strip()

                    w1 = _relation_weight(rel1, context_quality)
                    w2 = _relation_weight(rel2, context_quality)

                    if not source or not middle or not target or w1 <= 0 or w2 <= 0:
                        continue

                    pkey = (source, rel1.lower(), middle, rel2.lower(), target)
                    if pkey in seen_path:
                        continue

                    seen_path.add(pkey)
                    path_rows.append({
                        "source": source,
                        "rel1": rel1,
                        "middle": middle,
                        "rel2": rel2,
                        "target": target,
                        "weight": (w1 + w2) / 2.0,
                    })

            # Sort paths by weight and limit
            path_rows.sort(key=lambda x: x["weight"], reverse=True)
            path_rows = path_rows[:max_paths]

            # Calculate enhanced graph signal score
            graph_signal_score = _calculate_enhanced_signal_score(
                top_entities,
                neighbor_rows,
                path_rows,
                context_quality,
            )

            # Determine confidence level
            confidence = _determine_confidence(
                graph_signal_score,
                len(top_entities),
                len(neighbor_rows),
                len(path_rows),
            )

            # Remove internal scoring fields from output
            clean_entities = [
                {"entity": e["entity"], "relations": e["relations"]}
                for e in top_entities
            ]

            return {
                "entities": clean_entities,
                "neighbors": neighbor_rows,
                "paths": path_rows,
                "graph_signal_score": graph_signal_score,
                "confidence": confidence,
                "diagnostics": {
                    "query_tokens": len(tokens),
                    "context_quality": context_quality,
                    "top_entity_relevance": top_entities[0]["relevance"] if top_entities else 0.0,
                },
            }

        finally:
            client.close()


def _calculate_enhanced_signal_score(
    entities: list[dict],
    neighbors: list[dict],
    paths: list[dict],
    context_quality: float,
) -> float:
    """
    Calculate enhanced graph signal score with adaptive weighting.

    Args:
        entities: Scored entity list
        neighbors: Neighbor relationships
        paths: 2-hop paths
        context_quality: Document quality score (0-1)

    Returns:
        Enhanced signal score (0-1)
    """
    # Entity score: count + relevance
    if entities:
        count_score = min(1.0, len(entities) / 5.0)
        avg_relevance = sum(e["relevance"] for e in entities) / len(entities)
        entity_score = (count_score + avg_relevance) / 2.0
    else:
        entity_score = 0.0

    # Neighbor score: weighted average with quality boost
    if neighbors:
        weights = [float(n.get("weight", 0.0)) for n in neighbors]
        neighbor_score = sum(weights) / len(weights)
        # High-quality neighbors from good context get a boost
        if context_quality >= 0.7:
            neighbor_score = min(1.0, neighbor_score * 1.15)
    else:
        neighbor_score = 0.0

    # Path score: multi-hop reasoning bonus
    if paths:
        weights = [float(p.get("weight", 0.0)) for p in paths]
        path_score = sum(weights) / len(weights)
        # Multi-hop paths are valuable, give them a boost
        path_score = min(1.0, path_score * 1.2)
    else:
        path_score = 0.0

    # Adaptive weighting based on what we found
    components = []
    weights = []

    if entities:
        components.append(entity_score)
        weights.append(0.35)  # Higher weight than before

    if neighbors:
        components.append(neighbor_score)
        weights.append(0.40)

    if paths:
        components.append(path_score)
        weights.append(0.25)

    if not components:
        return 0.0

    # Normalize weights
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    # Calculate weighted score
    score = sum(c * w for c, w in zip(components, normalized_weights))

    # Apply context quality multiplier (subtle)
    score = score * (0.9 + context_quality * 0.1)

    return min(1.0, score)


def _determine_confidence(
    signal_score: float,
    entity_count: int,
    neighbor_count: int,
    path_count: int,
) -> str:
    """
    Determine confidence level based on graph coverage.

    Args:
        signal_score: Graph signal score
        entity_count: Number of entities found
        neighbor_count: Number of neighbors found
        path_count: Number of paths found

    Returns:
        Confidence level: "high", "medium", or "low"
    """
    # High confidence: strong signal + good coverage
    if signal_score >= 0.7 and entity_count >= 3 and (neighbor_count >= 5 or path_count >= 3):
        return "high"

    # Medium confidence: decent signal or coverage
    if signal_score >= 0.5 or (entity_count >= 2 and neighbor_count >= 3):
        return "medium"

    # Low confidence: weak signal and poor coverage
    return "low"
