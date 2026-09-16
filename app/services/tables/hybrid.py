"""Hybrid Table and Graph Analytical Service.

Enables structured queries on TableStore constrained or guided by entities
discovered in the Knowledge Graph, with strict injection defense and SQL safety.
"""

from __future__ import annotations

import logging
import re

from app.services.security.injection_defense import detect_prompt_injection
from app.services.tables.engine import TableQueryResult, TableSchema
from app.services.tables.nl2sql import translate_nl_to_sql_with_guardrail
from app.services.tables.store import TableStore, get_table_store

logger = logging.getLogger(__name__)


def _sanitize_entity_filter(query: str, entity_filter: list[str] | None) -> tuple[str, list[str]]:
    if not entity_filter:
        return query, []
    sanitized: list[str] = []
    for ent in entity_filter:
        cleaned = re.sub(r"['\";\\]", "", str(ent).strip())
        if cleaned and len(cleaned) >= 2:
            sanitized.append(cleaned)
    augmented = f"{query} (筛选包含: {', '.join(sanitized[:5])})" if sanitized else query
    return augmented, sanitized


def _fallback_entity_query(
    tbl_store: TableStore,
    tenant_id: str,
    table_id: str,
    schema: TableSchema,
    user_id: str | None,
    max_rows: int,
    sanitized_entities: list[str],
    err: str | None,
) -> TableQueryResult:
    if sanitized_entities and schema.sql_columns:
        text_cols = [c for c in schema.sql_columns if schema.column_types.get(c, "TEXT") in ("TEXT", "VARCHAR")]
        in_clause = ", ".join(f"'{e}'" for e in sanitized_entities[:10])
        predicate = " OR ".join(f'"{col}" IN ({in_clause})' for col in (text_cols or schema.sql_columns))
        fallback_sql = f'SELECT * FROM "{schema.table_name}" WHERE {predicate} LIMIT {max_rows}'
        return tbl_store.query_table(tenant_id, table_id, fallback_sql, user_id=user_id, max_rows=max_rows)

    return TableQueryResult(
        columns=[],
        rows=[],
        row_count=0,
        execution_time_ms=0.0,
        markdown_table="",
        engine_used="nl2sql",
        error=err or "Failed to generate valid SQL query",
    )


def query_table_with_graph_entities(
    tenant_id: str,
    table_id: str,
    query: str,
    entity_filter: list[str] | None = None,
    max_rows: int = 100,
    store: TableStore | None = None,
    *,
    user_id: str | None,
) -> TableQueryResult:
    """Execute analytical table query guided by Knowledge Graph entities.

    Args:
        tenant_id: Tenant identifier
        table_id: Target table ID
        query: User analytical question
        entity_filter: Optional entity names from Knowledge Graph to constrain table search
        max_rows: Max rows in result
        store: Optional TableStore instance (defaults to singleton)
        user_id: The reader; the table must be one they may read

    Returns:
        TableQueryResult with results or error explanation
    """
    # 1. Pre-check prompt injection defense
    assessment = detect_prompt_injection(query)
    if assessment.is_blocked:
        logger.warning(
            "Blocked prompt injection in hybrid query: threat=%s risk=%.2f",
            assessment.threat_type,
            assessment.risk_score,
        )
        return TableQueryResult(
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            markdown_table="",
            engine_used="security_guardrail",
            error=f"Query blocked: prompt injection detected ({assessment.threat_type.value if assessment.threat_type else 'threat'})",
        )

    tbl_store = store or get_table_store()
    schema = tbl_store.get_schema(tenant_id, table_id, user_id=user_id)
    if not schema:
        return TableQueryResult(
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            markdown_table="",
            engine_used="error",
            error=f"Table '{table_id}' not found",
        )

    # 2. Enrich query with entity constraints if provided
    augmented_query, sanitized_entities = _sanitize_entity_filter(query, entity_filter)

    # 3. Generate safe SQL via guarded NL2SQL
    table_obj = tbl_store.get_table(tenant_id, table_id, user_id=user_id)
    sample_rows = table_obj.rows if table_obj else None
    sql, err = translate_nl_to_sql_with_guardrail(augmented_query, schema, sample_rows=sample_rows)

    if not sql or err:
        return _fallback_entity_query(
            tbl_store, tenant_id, table_id, schema, user_id, max_rows, sanitized_entities, err
        )

    # 4. Execute validated SQL
    return tbl_store.query_table(tenant_id, table_id, sql, user_id=user_id, max_rows=max_rows)


__all__ = ["query_table_with_graph_entities"]
