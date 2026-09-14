"""
Tests for modern GraphRAG capabilities:
- Rich Property Graph schema (types and descriptions)
- Community detection and Global Search
- Fulltext index and search fallback
- Backward compatibility and table overlap grounding
"""

from __future__ import annotations

from app.agents.rag.enhanced_graph import (
    _format_entity_lines,
    _format_graph_lines,
    should_use_graph_rag,
)
from app.graph.knowledge.community import (
    detect_entity_communities,
    is_macro_thematic_query,
)
from app.graph.knowledge.table_linking import detect_graph_table_overlap
from app.ingestion.graph_extractor import (
    GraphTriplet,
    _extract_json_array,
    _stamp,
    filter_triplets,
)


def test_graph_triplet_backward_compatibility():
    """Ensure GraphTriplet works with legacy 5 positional args, and defaults new fields."""
    legacy = GraphTriplet("Alpha", "DEPENDS_ON", "Beta", 0.7, "llm")
    assert legacy.head == "Alpha"
    assert legacy.relation == "DEPENDS_ON"
    assert legacy.tail == "Beta"
    assert legacy.confidence == 0.7
    assert legacy.method == "llm"
    assert legacy.head_type == "CONCEPT"
    assert legacy.tail_type == "CONCEPT"
    assert legacy.head_description == ""
    assert legacy.tail_description == ""
    assert legacy.relation_description == ""


def test_graph_triplet_rich_attributes():
    """Ensure GraphTriplet retains rich types and descriptions."""
    rich = GraphTriplet(
        head="FastAPI",
        relation="USES",
        tail="Pydantic",
        confidence=0.85,
        method="llm",
        head_type="TECHNOLOGY",
        tail_type="TECHNOLOGY",
        head_description="High-performance async web framework",
        tail_description="Data validation library",
        relation_description="FastAPI uses Pydantic for request and response body parsing",
    )
    assert rich.head_type == "TECHNOLOGY"
    assert rich.tail_description == "Data validation library"
    assert rich.relation_description.startswith("FastAPI uses Pydantic")


def test_stamp_and_filter_triplets_preserves_rich_properties():
    raw = [
        {
            "head": "FastAPI",
            "relation": "DEPENDS_ON",
            "tail": "Starlette",
            "head_type": "TECHNOLOGY",
            "tail_type": "TECHNOLOGY",
            "head_description": "Web framework",
            "tail_description": "ASGI toolkit",
            "relation_description": "Direct inheritance",
        },
        ("ServiceA", "CALLS", "ServiceB"),  # Legacy tuple
    ]
    stamped = _stamp(raw, confidence=0.75, method="llm")
    assert len(stamped) == 2
    assert stamped[0].head == "FastAPI"
    assert stamped[0].head_type == "TECHNOLOGY"
    assert stamped[0].head_description == "Web framework"
    assert stamped[1].head == "ServiceA"
    assert stamped[1].head_type == "CONCEPT"

    filtered = filter_triplets(stamped, min_confidence=0.5)
    assert len(filtered) == 2
    assert filtered[0].head_type == "TECHNOLOGY"


def test_extract_json_array_parses_rich_format():
    json_str = """
    [
      {
        "head": "OAuth2",
        "head_type": "PROTOCOL",
        "head_description": "Authorization protocol",
        "relation": "AUTHENTICATES",
        "tail": "UserSession",
        "tail_type": "CONCEPT",
        "tail_description": "Active user state",
        "relation_description": "Issues bearer token for sessions"
      }
    ]
    """
    parsed = _extract_json_array(json_str)
    assert len(parsed) == 1
    assert parsed[0]["head"] == "OAuth2"
    assert parsed[0]["head_type"] == "PROTOCOL"
    assert parsed[0]["relation"] == "AUTHENTICATES"


def test_macro_thematic_query_detection():
    assert is_macro_thematic_query("总结全库的核心系统架构") is True
    assert is_macro_thematic_query("Give me an architectural overview and summary of main themes") is True
    assert is_macro_thematic_query("文档的主要趋势和概括是什么") is True
    assert is_macro_thematic_query("What is the port for redis?") is False
    assert is_macro_thematic_query("Query order status where id is 123") is False


def test_community_detection_clustering():
    entities = [
        {"entity": "ServiceA", "type": "MICROSERVICE", "description": "Payment service"},
        {"entity": "ServiceB", "type": "MICROSERVICE", "description": "Order service"},
        {"entity": "DB1", "type": "DATABASE", "description": "Postgres database"},
        {"entity": "UserFront", "type": "UI", "description": "Web portal"},
    ]
    relations = [
        {"source": "ServiceA", "target": "DB1"},
        {"source": "ServiceB", "target": "DB1"},
        {"source": "ServiceA", "target": "ServiceB"},
    ]
    communities = detect_entity_communities(entities, relations)
    assert len(communities) >= 1
    comm1 = communities[0]
    assert "ServiceA" in comm1["entity_names"] or "DB1" in comm1["entity_names"]
    assert "Community" in comm1["title"]
    assert len(comm1["findings"]) >= 1


def test_format_entity_lines_with_types_and_descriptions():
    entities = [
        {
            "entity": "PayService",
            "type": "MICROSERVICE",
            "description": "Core payment gateway",
            "relations": [
                {"relation": "DEPENDS_ON", "other": "MySQL", "weight": 0.95, "rel_desc": "Persists transactions"}
            ],
        },
        {
            "entity": "OrderService",
            "relations": [{"relation": "CALLS", "other": "PayService", "weight": 0.9}],
        },
    ]
    lines = _format_entity_lines(entities)
    text = "\n".join(lines)
    assert "Entity: PayService [MICROSERVICE] - Core payment gateway" in text
    assert "DEPENDS_ON (0.95) -> MySQL (Persists transactions)" in text
    assert "Entity: OrderService" in text


def test_rich_graph_lines_preserves_table_overlap():
    """Verify detect_graph_table_overlap still parses entities out of the modernized format."""
    entities = [
        {
            "entity": "PayService",
            "type": "MICROSERVICE",
            "description": "Payment handler",
            "relations": [],
        }
    ]
    neighbors = [{"entity": "PayService", "relation": "runs_on", "other": "node-102", "weight": 0.9}]
    paths = [
        {
            "source": "OrderService",
            "rel1": "calls",
            "middle": "PayService",
            "rel2": "runs_on",
            "target": "node-102",
            "weight": 0.85,
        }
    ]

    formatted = _format_graph_lines(
        entities,
        neighbors,
        paths,
        community_context="### 知识图谱宏观社区概览 (Global Community Insights)\n- **微服务群落**",
    )
    graph_content = "\n".join(formatted)

    table_content = """
    | Service Name | Host Node | Status |
    | --- | --- | --- |
    | PayService | node-102 | running |
    | OrderService | node-101 | running |
    """
    overlapping = detect_graph_table_overlap(graph_content, table_content)
    assert "PayService" in overlapping
    assert "OrderService" in overlapping or "node-102" in overlapping


def test_should_use_graph_rag_on_macro_thematic_query():
    use, reason = should_use_graph_rag("请概述一下整体系统架构与核心模块")
    assert use is True
    assert "global_graph" in reason or "thematic" in reason


def test_build_communities_from_rows():
    from unittest.mock import MagicMock

    from app.graph.knowledge.community import build_communities_from_rows

    rows = [
        {
            "head": "FastAPI",
            "head_type": "TECHNOLOGY",
            "head_description": "Web framework",
            "relation": "DEPENDS_ON",
            "tail": "Starlette",
            "tail_type": "TECHNOLOGY",
            "tail_description": "ASGI toolkit",
            "source": "uploads/alice/stack.md",
        },
        {
            "head": "FastAPI",
            "head_type": "TECHNOLOGY",
            "head_description": "Web framework",
            "relation": "USES",
            "tail": "Pydantic",
            "tail_type": "TECHNOLOGY",
            "tail_description": "Validation library",
            "source": "uploads/alice/stack.md",
        },
    ]
    mock_client = MagicMock()
    mock_client.save_community_summaries.return_value = 1

    saved = build_communities_from_rows(rows, client=mock_client)
    assert saved == 1
    assert mock_client.save_community_summaries.called
    saved_comms = mock_client.save_community_summaries.call_args[0][0]
    assert len(saved_comms) >= 1
    assert "FastAPI" in saved_comms[0]["entity_names"]
    # Attribution is what makes a summary readable on a scoped query at all.
    assert saved_comms[0]["sources"] == ["uploads/alice/stack.md"]


def test_communities_are_never_clustered_across_sources():
    """A summary embeds its members' descriptions, and entity nodes are shared by
    name across tenants. One cluster spanning two sources would put alice's
    description of a shared entity into a summary bob can read."""
    from unittest.mock import MagicMock

    from app.graph.knowledge.community import build_communities_from_rows

    rows = [
        {
            "head": "Acme",
            "head_description": "alice's confidential acquisition target",
            "relation": "OWNS",
            "tail": "Widget",
            "source": "uploads/alice/deal.md",
        },
        {
            "head": "Acme",
            "head_description": "a supplier",
            "relation": "SUPPLIES",
            "tail": "Bolt",
            "source": "uploads/bob/vendors.md",
        },
        {"head": "Orphan", "relation": "RELATED_TO", "tail": "Row", "source": ""},
    ]
    mock_client = MagicMock()
    mock_client.save_community_summaries.side_effect = len

    build_communities_from_rows(rows, client=mock_client)

    saved = mock_client.save_community_summaries.call_args[0][0]
    by_source = {tuple(comm["sources"]): comm for comm in saved}
    assert set(by_source) == {("uploads/alice/deal.md",), ("uploads/bob/vendors.md",)}
    assert "confidential" not in by_source[("uploads/bob/vendors.md",)]["summary"]
    # Ids are per source, so rebuilding one source cannot overwrite the other's.
    assert len({comm["id"] for comm in saved}) == len(saved)
    assert all("Orphan" not in comm["entity_names"] for comm in saved)
