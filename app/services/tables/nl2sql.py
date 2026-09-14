"""Natural language to SQL translation and assistance for structured tables."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.services.tables.engine import TableSchema

logger = logging.getLogger(__name__)

NL2SQL_SYSTEM_PROMPT = """You are an expert SQL analyst. Given a table schema and sample data, translate the user's analytical question into a precise, read-only SQLite/DuckDB SQL query.

Rules:
1. Output ONLY the raw SQL query inside a single ```sql ``` code block. Do not provide explanations.
2. Use ONLY the table name and column names provided in the schema.
3. The query MUST be a read-only SELECT or WITH statement. Never use DROP, DELETE, INSERT, UPDATE, ALTER, or PRAGMA.
4. If the question asks for aggregations (sum, average, count, max, min), use the corresponding SQL aggregate functions.
5. If the question asks for sorting or ranking, use ORDER BY ... DESC/ASC and LIMIT.
"""


def format_table_schema_for_prompt(schema: TableSchema, sample_rows: list[list[Any]] | None = None) -> str:
    """Format table schema and sample rows into a readable description for LLM prompting."""
    lines = [
        f"Table Name: {schema.table_name}",
        f"Total Rows: {schema.row_count}",
        "Columns:",
    ]
    for sql_col in schema.sql_columns:
        orig = schema.reverse_mapping.get(sql_col, sql_col)
        c_type = schema.column_types.get(sql_col, "TEXT")
        lines.append(f"  - {sql_col} ({c_type}): Original header '{orig}'")

    if sample_rows:
        lines.append("\nSample Data (first 3 rows):")
        for r in sample_rows[:3]:
            lines.append("  " + " | ".join(str(c if c is not None else "") for c in r))

    return "\n".join(lines)


_SYNONYMS: dict[str, tuple[str, ...]] = {
    "部门": ("dept", "department", "org", "group"),
    "薪资": ("salary", "wage", "pay", "income"),
    "工资": ("salary", "wage", "pay", "income"),
    "金额": ("amount", "price", "cost", "revenue", "budget"),
    "预算": ("budget", "cost", "expenditure"),
    "姓名": ("name", "employee", "staff"),
    "评分": ("rating", "score"),
    "绩效": ("rating", "score", "performance"),
}


def _matches_col(query_text: str, sql_col: str, orig_col: str) -> bool:
    q_low = query_text.lower()
    c_low = sql_col.lower()
    o_low = orig_col.lower()

    if (len(o_low) >= 2 and o_low in q_low) or (len(c_low) >= 3 and c_low in q_low):
        return True

    for zh_kw, en_syns in _SYNONYMS.items():
        if zh_kw in q_low:
            if any(syn in c_low or syn in o_low for syn in en_syns):
                return True
        if any(syn in q_low for syn in en_syns):
            if zh_kw in o_low or zh_kw in c_low:
                return True

    return False


def match_template_aggregation(query: str, schema: TableSchema) -> str | None:
    """Attempt fast zero-shot heuristic / rule-based SQL generation for standard aggregate queries.

    Handles common patterns like:
    - "求 [列] 的总和 / 汇总 / 总额" -> SELECT SUM(col) FROM table
    - "计算 [列] 的平均值 / 均值" -> SELECT AVG(col) FROM table
    - "最高 / 最大的 [列]" -> SELECT * FROM table ORDER BY col DESC LIMIT 1
    - "最低 / 最小的 [列]" -> SELECT * FROM table ORDER BY col ASC LIMIT 1
    - "共有多少行 / 记录总数" -> SELECT COUNT(*) FROM table
    """
    q = query.strip().lower()

    # Pattern: Count all
    if any(k in q for k in ("多少条", "多少行", "记录数", "总数", "总人数", "count", "how many rows", "total count")):
        if not any(k in q for k in ("按", "group by", "各个", "每个")):
            return f'SELECT COUNT(*) AS total_count FROM "{schema.table_name}"'

    # Detect aggregate function
    agg_func = None
    if any(k in q for k in ("总和", "总额", "合计", "求和", "汇总", "sum", "total")):
        agg_func = "SUM"
    elif any(k in q for k in ("平均", "均值", "avg", "average", "mean")):
        agg_func = "AVG"
    elif any(k in q for k in ("最大", "最高", "最多", "max", "highest", "maximum")):
        agg_func = "MAX"
    elif any(k in q for k in ("最小", "最低", "最少", "min", "lowest", "minimum")):
        agg_func = "MIN"

    if not agg_func:
        return None

    # Find which column is being asked about
    target_col = None
    for sql_col in schema.sql_columns:
        orig = schema.reverse_mapping.get(sql_col, sql_col)
        if _matches_col(q, sql_col, orig):
            # Only numeric columns for SUM / AVG
            if agg_func in ("SUM", "AVG") and schema.column_types.get(sql_col) not in ("INTEGER", "REAL"):
                continue
            target_col = sql_col
            break

    # If no specific column matched, try the first numeric column for SUM / AVG
    if not target_col and agg_func in ("SUM", "AVG"):
        for sql_col in schema.sql_columns:
            if schema.column_types.get(sql_col) in ("INTEGER", "REAL"):
                target_col = sql_col
                break

    if not target_col:
        return None

    # Check for Group By (e.g. "按部门统计总薪资" / "各个部门的平均工资")
    group_col = None
    for sql_col in schema.sql_columns:
        if sql_col == target_col:
            continue
        orig = schema.reverse_mapping.get(sql_col, sql_col)
        if _matches_col(q, sql_col, orig):
            group_col = sql_col
            break

    if group_col:
        return (
            f'SELECT "{group_col}", {agg_func}("{target_col}") AS "{agg_func.lower()}_{target_col}" '
            f'FROM "{schema.table_name}" '
            f'GROUP BY "{group_col}" '
            f'ORDER BY "{agg_func.lower()}_{target_col}" DESC'
        )

    return f'SELECT {agg_func}("{target_col}") AS "{agg_func.lower()}_{target_col}" FROM "{schema.table_name}"'


def extract_sql_from_markdown(llm_output: str) -> str:
    """Extract raw SQL statement from markdown code block or plain text."""
    m = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", llm_output, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return llm_output.strip()


def translate_nl_to_sql_with_guardrail(
    query: str,
    schema: TableSchema,
    sample_rows: list[list[Any]] | None = None,
    model: Any | None = None,
) -> tuple[str | None, str | None]:
    """Translate natural language query to safe read-only SQL with prompt injection defense.

    Returns:
        tuple[sql_query | None, error_message | None]
    """
    from app.services.security.injection_defense import SandboxedPromptBuilder, detect_prompt_injection

    # 1. Pre-check: Prompt injection detection on user's natural language input
    assessment = detect_prompt_injection(query)
    if assessment.is_blocked:
        logger.warning(
            "NL2SQL blocked prompt injection: threat=%s risk=%.2f",
            assessment.threat_type,
            assessment.risk_score,
        )
        return (
            None,
            f"Query blocked: prompt injection detected ({assessment.threat_type.value if assessment.threat_type else 'threat'})",
        )

    # 2. Fast deterministic template matching
    matched = match_template_aggregation(query, schema)
    if matched:
        return matched, None

    # 3. LLM-based translation if model is available
    if model is None:
        try:
            from app.services.models.runtime import get_chat_model

            model = get_chat_model(temperature=0)
        except Exception as e:
            logger.debug("Failed to obtain chat model for NL2SQL: %s", e)
            return None, "Model unavailable for SQL translation"

    schema_text = format_table_schema_for_prompt(schema, sample_rows)
    nonce = SandboxedPromptBuilder.generate_nonce()
    sandboxed_q = SandboxedPromptBuilder.sandbox_user_query(query, nonce)

    prompt = (
        f"{schema_text}\n\n"
        f"User Analytical Request (sandboxed):\n{sandboxed_q}\n\n"
        "Generate a read-only SQL query for this request."
    )

    try:
        res = model.invoke([("system", NL2SQL_SYSTEM_PROMPT), ("human", prompt)])
        raw_text = str(getattr(res, "content", "") or res)
        extracted_sql = extract_sql_from_markdown(raw_text)

        # Validate that the extracted SQL is safe
        from app.services.tables.engine import TableEngine

        temp_engine = TableEngine(prefer_duckdb=False)
        is_valid, err = temp_engine.validate_sql(extracted_sql)
        if not is_valid:
            return None, f"Generated SQL failed safety validation: {err}"

        return extracted_sql, None
    except Exception as exc:
        logger.warning("NL2SQL translation failed: %s", exc)
        return None, f"SQL translation error: {exc}"


__all__ = [
    "NL2SQL_SYSTEM_PROMPT",
    "format_table_schema_for_prompt",
    "match_template_aggregation",
    "extract_sql_from_markdown",
    "translate_nl_to_sql_with_guardrail",
]
