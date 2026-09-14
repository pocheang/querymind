"""Knowledge-graph infrastructure: client, Cypher validation, and extraction."""

from app.graph.knowledge.client import Neo4jClient
from app.graph.knowledge.community import (
    detect_entity_communities,
    global_graph_search,
    is_macro_thematic_query,
)
from app.graph.knowledge.cypher_validation import (
    CypherQueryTemplate,
    ValidationResult,
    get_query_templates,
    get_simpler_query,
    validate_cypher_query,
)
from app.graph.knowledge.table_linking import (
    detect_graph_table_overlap,
    extract_table_entities,
)

__all__ = [
    "Neo4jClient",
    "CypherQueryTemplate",
    "ValidationResult",
    "get_query_templates",
    "get_simpler_query",
    "validate_cypher_query",
    "detect_graph_table_overlap",
    "extract_table_entities",
    "detect_entity_communities",
    "global_graph_search",
    "is_macro_thematic_query",
]
