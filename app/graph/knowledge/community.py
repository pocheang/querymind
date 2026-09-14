"""
Community detection and Global Search for GraphRAG.

Implements the modern Microsoft GraphRAG global search paradigm:
1. Hierarchical or cluster-based community detection over knowledge graph entities.
2. Community report and summary generation.
3. Global Search: answering macro, thematic, or corpus-wide overview queries
   using community-level insights.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from app.graph.knowledge.client import Neo4jClient

logger = logging.getLogger(__name__)

# Patterns indicating high-level, thematic, or macro summary queries (Global Search intent)
_MACRO_THEMATIC_PATTERNS = re.compile(
    r"(?i)\b(summary|summarize|overview|architecture|themes|trends|high[- ]level|overall|core concept|key takeaways)\b"
    r"|总结|概述|概括|整体架构|核心模块|主要趋势|全貌|核心内容|主要功能|架构图|整体概况"
)


def is_macro_thematic_query(query: str) -> bool:
    """Determine if a query is high-level / thematic (suitable for Global Search)."""
    if not query or not query.strip():
        return False
    return bool(_MACRO_THEMATIC_PATTERNS.search(query.strip()))


def detect_entity_communities(
    entities: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    max_community_size: int = 15,
) -> list[dict[str, Any]]:
    """
    Cluster entities into cohesive communities based on graph connectivity.

    Uses adjacency and component clustering without requiring external heavy graph libraries.
    """
    if not entities:
        return []

    # Map entity name to its properties
    entity_map = {str(e.get("entity", "")).strip(): e for e in entities if e.get("entity")}
    adj: dict[str, set[str]] = {name: set() for name in entity_map}

    # Populate adjacency from relations
    for rel in relations:
        src = str(rel.get("entity") or rel.get("source") or "").strip()
        tgt = str(rel.get("other") or rel.get("target") or "").strip()
        if src in adj and tgt in adj:
            adj[src].add(tgt)
            adj[tgt].add(src)

    # Also check relations embedded within entity dicts
    for name, e in entity_map.items():
        for r in e.get("relations", []) or []:
            other = str(r.get("other", "")).strip()
            if other in adj:
                adj[name].add(other)
                adj[other].add(name)

    # Connected component traversal
    visited: set[str] = set()
    raw_clusters: list[list[str]] = []

    for node in sorted(adj.keys(), key=lambda k: len(adj[k]), reverse=True):
        if node in visited:
            continue
        cluster = []
        queue = [node]
        visited.add(node)
        while queue and len(cluster) < max_community_size:
            curr = queue.pop(0)
            cluster.append(curr)
            for neighbor in sorted(adj[curr], key=lambda n: len(adj[n]), reverse=True):
                if neighbor not in visited and len(cluster) + len(queue) < max_community_size:
                    visited.add(neighbor)
                    queue.append(neighbor)
        if cluster:
            raw_clusters.append(cluster)

    # Convert clusters to community structures
    communities: list[dict[str, Any]] = []
    for idx, cluster in enumerate(raw_clusters, start=1):
        if not cluster:
            continue
        primary = cluster[0]
        primary_info = entity_map.get(primary, {})
        primary_type = primary_info.get("type", "CONCEPT")
        title = f"{primary} 及相关 {primary_type} 核心群落 (Community #{idx})"

        # Generate summary description from constituent entities
        descriptions = []
        for name in cluster[:5]:
            info = entity_map.get(name, {})
            desc = info.get("description", "")
            ent_type = info.get("type", "CONCEPT")
            if desc:
                descriptions.append(f"{name} ({ent_type}): {desc}")
            else:
                descriptions.append(f"{name} ({ent_type})")

        summary = f"涵盖 {', '.join(cluster[:6])} 等关键实体的领域社群。核心组成包括：{'；'.join(descriptions)}。"
        findings = [
            f"群落核心枢纽为 {primary}，关联实体数: {len(cluster)}",
            f"包含主要成员: {', '.join(cluster[:8])}",
        ]

        communities.append(
            {
                "id": f"comm_{idx}_{primary.lower().replace(' ', '_')[:20]}",
                "title": title,
                "level": 0,
                "summary": summary,
                "findings": findings,
                "entity_names": cluster,
            }
        )

    return communities


def global_graph_search(
    question: str,
    limit: int = 4,
    allowed_sources: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute Global Search over community summaries.

    Args:
        question: User query
        limit: Max number of community reports to retrieve
        allowed_sources: Optional source scoping

    Returns:
        Dictionary containing:
        - communities: Retrieved community dicts
        - context: Formatted Markdown context of community reports
        - global_signal_score: Confidence score of global retrieval
    """
    client = Neo4jClient()
    raw_communities = client.get_community_summaries(
        limit=limit * 2,
        allowed_sources=allowed_sources,
    )

    if not raw_communities:
        return {
            "communities": [],
            "context": "",
            "global_signal_score": 0.0,
        }

    # Score communities against query keywords
    query_tokens = [w.lower() for w in re.findall(r"\w+|[\u4e00-\u9fff]{2,}", question)]
    scored_communities: list[tuple[float, dict[str, Any]]] = []

    for comm in raw_communities:
        text = f"{comm.get('title', '')} {comm.get('summary', '')} {' '.join(comm.get('findings', []))}".lower()
        score = 0.0
        for token in query_tokens:
            if token in text:
                score += 1.0
        # Normalize by query length
        norm_score = min(1.0, score / max(1, len(query_tokens))) if query_tokens else 0.5
        scored_communities.append((norm_score, comm))

    scored_communities.sort(key=lambda x: x[0], reverse=True)
    top_communities = [c for _, c in scored_communities[:limit]]

    # Format into structured Markdown report context
    context_lines = ["### 知识图谱宏观社区概览 (Global Community Insights)"]
    for c in top_communities:
        title = c.get("title", "未命名社群")
        summary = c.get("summary", "")
        entities = c.get("entities", [])
        context_lines.append(f"- **{title}**")
        if summary:
            context_lines.append(f"  - 概要: {summary}")
        if entities:
            context_lines.append(f"  - 关键实体: {', '.join(entities[:10])}")
        for finding in c.get("findings", [])[:2]:
            context_lines.append(f"  - 发现: {finding}")

    max_score = scored_communities[0][0] if scored_communities else 0.0
    return {
        "communities": top_communities,
        "context": "\n".join(context_lines),
        "global_signal_score": max_score,
    }


def _communities_for_source(source: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cluster one source's triplets; every community records that source."""
    entities_dict: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, Any]] = []

    for r in rows:
        head = str(r.get("head", "")).strip()
        tail = str(r.get("tail", "")).strip()
        rel = str(r.get("relation", "")).strip()
        if head and head not in entities_dict:
            entities_dict[head] = {
                "entity": head,
                "type": r.get("head_type", "CONCEPT"),
                "description": r.get("head_description", ""),
            }
        if tail and tail not in entities_dict:
            entities_dict[tail] = {
                "entity": tail,
                "type": r.get("tail_type", "CONCEPT"),
                "description": r.get("tail_description", ""),
            }
        if head and tail:
            relations.append({"source": head, "relation": rel, "target": tail})

    communities = detect_entity_communities(list(entities_dict.values()), relations)
    source_key = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    for idx, community in enumerate(communities, start=1):
        community["id"] = f"comm_{source_key}_{idx}"
        community["sources"] = [source]
    return communities


def build_communities_from_rows(rows: list[dict[str, Any]], client: Neo4jClient | None = None) -> int:
    """Build and persist communities from triplet rows, one set per source.

    Communities are never clustered across sources. A summary embeds its members'
    descriptions, and entity nodes are shared by name across every tenant -- so
    a cross-source cluster would put one tenant's descriptions into a summary
    another tenant reaches through a single shared name. Rows with no source are
    skipped for the same reason: a summary nobody can be authorized for.
    """
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows or []:
        source = str(row.get("source", "") or "").strip()
        if source:
            by_source.setdefault(source, []).append(row)

    communities = [
        community
        for source, source_rows in by_source.items()
        for community in _communities_for_source(source, source_rows)
    ]
    if not communities:
        return 0

    c = client or Neo4jClient()
    return c.save_community_summaries(communities)


def build_all_communities(client: Neo4jClient | None = None) -> int:
    """Rebuild every source's communities from what the graph holds for it.

    Each relationship is read once per source it records, with the entity
    descriptions *that source* wrote, so the rebuild has exactly the per-source
    shape ingest produces.
    """
    c = client or Neo4jClient()
    cypher = """
    MATCH (h:Entity)-[r:RELATED]->(t:Entity)
    UNWIND coalesce(r.sources, []) AS source
    OPTIONAL MATCH (h)-[mh:MENTIONED_IN]->(:Source {name: source})
    OPTIONAL MATCH (t)-[mt:MENTIONED_IN]->(:Source {name: source})
    RETURN source,
           h.name AS head, coalesce(h.type, 'CONCEPT') AS head_type, coalesce(mh.description, '') AS head_description,
           r.type AS relation,
           t.name AS tail, coalesce(t.type, 'CONCEPT') AS tail_type, coalesce(mt.description, '') AS tail_description
    LIMIT 5000
    """
    with c.driver.session() as session:
        try:
            rows = [dict(r) for r in session.run(cypher)]
        except Exception as e:
            logger.warning("Failed to fetch graph data for community generation: %s", e)
            return 0

    return build_communities_from_rows(rows, client=c)


__all__ = [
    "is_macro_thematic_query",
    "detect_entity_communities",
    "global_graph_search",
    "build_communities_from_rows",
    "build_all_communities",
]
