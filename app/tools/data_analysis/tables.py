"""The data-analysis specialist's two table tools: find a table, then query it.

`table_query` needs a `table_id`, and the tool selector may only fill arguments
from what the user said or what an earlier step reported -- nobody asking "各区域
第三季度的销售额" knows an id like ``table-3f9c...``. `table_list` is the step that
supplies it, which is what makes the specialist usable at all.

Two threat-model decisions, both about what reaches the *next* tool selection:

- `table_list` reports each table's id, the name of the file it came from, its
  size and whose it is -- never its headers or cells. Its summary is read back by
  the selector as an observation, and a public table's headers are written by
  whoever uploaded it. A file name is text too, so it is shown only for the
  caller's own tables and the shared corpus; another user's public table is
  listed by id and size alone.
- `table_query` is ``open_world``. Its result carries column names and cells,
  which reach the answer and never the selector (`ToolAgentService._observation`
  passes only the id and status of an ``open_world`` step), so a header cannot
  steer which tool runs next.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Sequence
from pathlib import PurePosixPath

from app.domain.contracts import ToolResult
from app.mcp.contracts import ToolCall, ToolDefinition, ToolParameter
from app.orchestration.request import RequestActor
from app.services.tables.store import TableSummary

TABLE_LIST_TOOL_ID = "querymind_table_list"
TABLE_QUERY_TOOL_ID = "querymind_table_query"

# How many tables the list names before it says "+N more".
_MAX_LISTED_TABLES = 20
_MAX_NAME_CHARS = 60
# A file name is reduced to these characters before it is shown: letters, digits,
# CJK, and the punctuation file names carry. Anything else becomes "_".
_NAME_UNSAFE = re.compile(r"[^0-9A-Za-z._\-一-鿿]+")


def _shown_name(summary: TableSummary) -> str:
    if not (summary.owned or summary.shared_corpus):
        return ""
    name = PurePosixPath(summary.source.replace("\\", "/")).name
    return _NAME_UNSAFE.sub("_", name)[:_MAX_NAME_CHARS]


def _origin(summary: TableSummary) -> str:
    if summary.owned:
        return "yours"
    if summary.shared_corpus:
        return "shared corpus"
    return "another user's public table"


def _describe(summary: TableSummary) -> str:
    name = _shown_name(summary)
    parts = [name] if name else []
    parts.append(f"{summary.rows} rows x {summary.columns} columns")
    parts.append(_origin(summary))
    return f"{summary.table_id} ({', '.join(parts)})"


def table_list_summary(summaries: Sequence[TableSummary]) -> str:
    """The tables a reader may query, by id, file, size and owner -- no contents."""

    if not summaries:
        return "no tables you can query; upload a spreadsheet or a document with tables first"
    # The caller's own tables first: "我上传的表" is the common question.
    ordered = sorted(summaries, key=lambda item: (not item.owned, not item.shared_corpus, item.table_id))
    shown = ordered[:_MAX_LISTED_TABLES]
    listed = "; ".join(_describe(summary) for summary in shown)
    remaining = len(ordered) - len(shown)
    suffix = f"; +{remaining} more" if remaining > 0 else ""
    return f"{len(ordered)} tables you can query: {listed}{suffix}"


def _argument(call: ToolCall, name: str) -> str:
    return next((argument.value for argument in call.arguments if argument.name == name), "")


async def execute_table_list(call: ToolCall, actor: RequestActor) -> ToolResult:
    from app.services.tables.store import get_table_store

    if not actor.user_id:
        return ToolResult(tool_id=call.tool_id, status="failed", summary="a signed-in user is required")
    # Synchronous SQLite and engine builds, so off the event loop.
    summaries = await asyncio.to_thread(get_table_store().summaries, actor.tenant_id or "", user_id=actor.user_id)
    # An empty list is a successful read: `_run_steps` stops on anything else.
    return ToolResult(tool_id=call.tool_id, status="succeeded", summary=table_list_summary(summaries))


async def execute_table_query(call: ToolCall, actor: RequestActor) -> ToolResult:
    from app.services.tables.nl2sql import translate_nl_to_sql_with_guardrail
    from app.services.tables.store import get_table_store

    table_id = _argument(call, "table_id")
    sql = _argument(call, "sql")
    query_text = _argument(call, "query")

    if not table_id:
        return ToolResult(tool_id=call.tool_id, status="failed", summary="table_id is required")

    tenant_id = actor.tenant_id or ""
    table_store = get_table_store()
    schema = await asyncio.to_thread(table_store.get_schema, tenant_id, table_id, user_id=actor.user_id)
    if not schema:
        return ToolResult(tool_id=call.tool_id, status="failed", summary=f"table '{table_id}' not found")

    target_sql = sql
    if not target_sql and query_text:
        # The rows let the translation see how values are written ("Q3", not
        # "第三季度"). The reader may already read this table, so the model is
        # shown nothing they could not.
        content = await asyncio.to_thread(table_store.get_table, tenant_id, table_id, user_id=actor.user_id)
        rows = list(content.rows) if content is not None else None
        target_sql, err = await asyncio.to_thread(translate_nl_to_sql_with_guardrail, query_text, schema, rows)
        if err and not target_sql and "blocked" in err.lower():
            return ToolResult(tool_id=call.tool_id, status="failed", summary=err)

    if not target_sql:
        target_sql = f'SELECT * FROM "{schema.table_name}" LIMIT 20'

    res = await asyncio.to_thread(table_store.query_table, tenant_id, table_id, target_sql, user_id=actor.user_id)
    if res.error:
        return ToolResult(tool_id=call.tool_id, status="failed", summary=f"SQL error: {res.error}")

    # The SQL is part of the result so the answer can state how the number was
    # obtained -- the data-analysis template's "口径".
    return ToolResult(
        tool_id=call.tool_id,
        status="succeeded",
        summary=(f"Table '{table_id}' query returned {res.row_count} rows.\nSQL: {target_sql}\n\n{res.markdown_table}"),
    )


TABLE_LIST_TOOL_DEFINITION = ToolDefinition(
    tool_id=TABLE_LIST_TOOL_ID,
    operation="read",
    risk="read_only",
    category="data_analysis",
    description=(
        "List the tables the user can query -- from their uploaded spreadsheets and documents -- with each "
        "table_id, source file, and size. Use it first to find the table_id for querymind_table_query. "
        "Takes no arguments."
    ),
)

TABLE_QUERY_TOOL_DEFINITION = ToolDefinition(
    tool_id=TABLE_QUERY_TOOL_ID,
    operation="read",
    # Its result carries headers and cells someone else may have written; see the
    # module docstring.
    risk="open_world",
    category="data_analysis",
    description=(
        "Query one table by table_id: a read-only SQL SELECT, or a natural-language aggregation (sum, average, "
        "count, max, min, filter, group by). Get the table_id from querymind_table_list."
    ),
    parameters=(
        ToolParameter(
            name="table_id",
            description="The table_id reported by querymind_table_list.",
            required=True,
            max_length=128,
        ),
        ToolParameter(
            name="sql",
            description="Read-only SQL SELECT statement to execute.",
            required=False,
            max_length=1000,
        ),
        ToolParameter(
            name="query",
            description="Natural language question for table aggregation or calculation.",
            required=False,
            max_length=500,
        ),
    ),
)


__all__ = [
    "TABLE_LIST_TOOL_DEFINITION",
    "TABLE_LIST_TOOL_ID",
    "TABLE_QUERY_TOOL_DEFINITION",
    "TABLE_QUERY_TOOL_ID",
    "execute_table_list",
    "execute_table_query",
    "table_list_summary",
]
