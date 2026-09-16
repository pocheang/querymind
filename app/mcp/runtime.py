"""The process-wide governed tool stack.

Two callers need to meet on the *same* objects and previously did not: the API
layer (``app/api/deps/runtime.py``) built its own registry, approvals and
gateway, and the RAG pipeline had none at all. Sharing them is not a
performance question, it is a correctness one -- ``ToolRegistry`` hands out an
approval token from one ``ApprovalStore`` and ``POST
/api/v1/connectors/approvals/{token}`` looks it up in another, so a token minted
on one path could never be redeemed on the other.

Mirrors ``app/orchestration/execution_events.get_default_execution_event_store``:
the pipeline has no access to ``app.state``, so a process-wide instance is the
only place the two sides can meet.

Built lazily. Construction needs ``API_SETTINGS_ENCRYPTION_KEY``, and
``CoreCapabilities()`` is constructed in tests and scripts that have no reason
to hold connector credentials; deferring to first tool use keeps that working.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256

from app.domain.contracts import ToolResult
from app.mcp.approvals import ApprovalStore
from app.mcp.authorization import AuthorizationPolicy
from app.mcp.contracts import ToolCall, ToolDefinition, ToolParameter
from app.mcp.gateway import MCPGateway
from app.mcp.registry import ToolRegistry
from app.orchestration.execution_events import get_default_execution_event_store
from app.orchestration.request import RequestActor
from app.services.connectors.contracts import ConnectorView
from app.services.connectors.management import ConnectorManagementService, probe_http_connector
from app.services.connectors.metadata_repository import ConnectorMetadataRepository
from app.services.connectors.repository import CredentialRepository
from app.services.connectors.service import ConnectorCredentialService

DISABLE_CONNECTOR_TOOL_ID = "querymind_connector_disable_owned"
LIST_CONNECTORS_TOOL_ID = "querymind_connector_list_owned"
QUERY_TABLE_TOOL_ID = "querymind_table_query"

# How many connectors the list tool names before it says "+N more". Each entry is
# at most a 64-char id plus a status word, and `AuditRecord.summary` caps at 1000.
_MAX_LISTED_CONNECTORS = 10


@dataclass(frozen=True, slots=True)
class ToolStack:
    """Everything a governed tool call needs, built once per process."""

    approvals: ApprovalStore
    registry: ToolRegistry
    gateway: MCPGateway
    connectors: ConnectorManagementService


_stack: ToolStack | None = None
_lock = threading.Lock()


def get_tool_stack() -> ToolStack:
    """Return the process-wide stack, building it on first use.

    Thread-safe: the pipeline reaches this from the retriever thread pool while
    the API layer reaches it from the event loop.
    """

    global _stack
    if _stack is not None:
        return _stack
    with _lock:
        if _stack is None:
            _stack = _build_tool_stack()
    return _stack


def reset_tool_stack() -> None:
    """Drop the cached stack. For tests that install their own connectors."""

    global _stack
    with _lock:
        _stack = None


def _build_tool_stack() -> ToolStack:
    from app.core.config import get_settings

    seed = str(get_settings().api_settings_encryption_key or "").strip()
    if not seed:
        raise RuntimeError("API_SETTINGS_ENCRYPTION_KEY is required for connector credentials")

    approvals = ApprovalStore()
    registry = ToolRegistry(
        authorization=AuthorizationPolicy(),
        approvals=approvals,
        # The same store the pipeline publishes into, so an approval request
        # raised mid-run reaches the SSE trace the client is already watching.
        execution_events=get_default_execution_event_store(),
    )
    credentials = ConnectorCredentialService(
        CredentialRepository(),
        encryption_key=sha256(seed.encode("utf-8")).digest(),
    )
    connectors = ConnectorManagementService(
        ConnectorMetadataRepository(),
        credentials,
        probe=probe_http_connector,
    )
    _register_connector_tools(registry, connectors)
    _register_table_tools(registry)
    return ToolStack(
        approvals=approvals,
        registry=registry,
        gateway=MCPGateway(registry),
        connectors=connectors,
    )


def _connector_summary(views: Sequence[ConnectorView]) -> str:
    """Name the caller's connectors using only ids and statuses.

    A ``read_only`` tool's summary is fed back into the next selection step as a
    ``ToolObservation`` -- ``ToolAgentService._observation`` suppresses only
    ``open_world`` text. ``ConnectorView.name`` is free text the user typed, up to
    120 characters, so composing the summary from it would put user-authored prose
    where the model reads its own working notes.

    These two fields cannot: ``connector_id`` matches ``^[a-z][a-z0-9_-]{0,63}$``
    and ``status`` is a two-value ``Literal``. A summary built from them is
    *structurally* incapable of carrying an instruction, which is what makes the
    read-then-write composition ("list my integrations, then disable the stale
    one") safe rather than merely untested.
    """

    if not views:
        return "no connected integrations"
    listed = ", ".join(f"{view.connector_id}({view.status})" for view in views[:_MAX_LISTED_CONNECTORS])
    remaining = len(views) - len(views[:_MAX_LISTED_CONNECTORS])
    suffix = f", +{remaining} more" if remaining > 0 else ""
    return f"{len(views)} connected integrations: {listed}{suffix}"


def _register_connector_tools(registry: ToolRegistry, connectors: ConnectorManagementService) -> None:
    async def list_owned_connectors(call: ToolCall, actor: RequestActor) -> ToolResult:
        if not actor.user_id:
            return ToolResult(tool_id=call.tool_id, status="failed", summary="connector owner is required")
        # `list_for_owner` is synchronous and opens its own SQLite connection, so
        # it cannot run on the event loop.
        views = await asyncio.to_thread(connectors.list_for_owner, actor.user_id)
        # An owner with no connectors succeeded at reading an empty list.
        # `ToolAgentService._run_steps` breaks the loop on anything other than
        # "succeeded", so reporting emptiness as a non-success would end a
        # multi-step plan that still had somewhere to go.
        return ToolResult(tool_id=call.tool_id, status="succeeded", summary=_connector_summary(views))

    registry.register(
        ToolDefinition(
            tool_id=LIST_CONNECTORS_TOOL_ID,
            operation="read",
            risk="read_only",
            description=(
                "List the user's own connected integrations with their ids and enabled/disabled status. "
                "Use this when the user asks what integrations they have, or to find the id of one "
                "before acting on it. Takes no arguments."
            ),
        ),
        list_owned_connectors,
    )

    async def disable_owned_connector(call: ToolCall, actor: RequestActor) -> ToolResult:
        connector_id = next(
            (argument.value for argument in call.arguments if argument.name == "connector_id"),
            "",
        )
        if not actor.user_id or not connector_id:
            return ToolResult(tool_id=call.tool_id, status="failed", summary="connector owner is required")
        try:
            # Synchronous SQLite, like `list_for_owner` above, so off the loop.
            await asyncio.to_thread(connectors.disable, connector_id, actor.user_id)
        except KeyError:
            return ToolResult(tool_id=call.tool_id, status="failed", summary="owned connector not found")
        return ToolResult(tool_id=call.tool_id, status="succeeded", summary="connector disabled")

    registry.register(
        ToolDefinition(
            tool_id=DISABLE_CONNECTOR_TOOL_ID,
            operation="write",
            risk="idempotent",
            description="Disable one of the user's own connected integrations by id. Reversible.",
            parameters=(
                ToolParameter(
                    name="connector_id",
                    description="The id of the connector to disable, as the user named it.",
                    required=True,
                    max_length=64,
                    pattern=r"[a-z][a-z0-9_-]{0,63}",
                ),
            ),
        ),
        disable_owned_connector,
    )


async def _query_table_data(call: ToolCall, actor: RequestActor) -> ToolResult:
    from app.services.tables.nl2sql import translate_nl_to_sql_with_guardrail
    from app.services.tables.store import get_table_store

    table_id = next((arg.value for arg in call.arguments if arg.name == "table_id"), "")
    sql = next((arg.value for arg in call.arguments if arg.name == "sql"), "")
    query_text = next((arg.value for arg in call.arguments if arg.name == "query"), "")

    if not table_id:
        return ToolResult(tool_id=call.tool_id, status="failed", summary="table_id is required")

    tenant_id = actor.tenant_id or ""
    table_store = get_table_store()
    schema = table_store.get_schema(tenant_id, table_id, user_id=actor.user_id)
    if not schema:
        return ToolResult(tool_id=call.tool_id, status="failed", summary=f"table '{table_id}' not found")

    target_sql = sql
    if not target_sql and query_text:
        target_sql, err = await asyncio.to_thread(translate_nl_to_sql_with_guardrail, query_text, schema)
        if err and not target_sql and "blocked" in err.lower():
            return ToolResult(tool_id=call.tool_id, status="failed", summary=err)

    if not target_sql:
        target_sql = f'SELECT * FROM "{schema.table_name}" LIMIT 20'

    res = await asyncio.to_thread(table_store.query_table, tenant_id, table_id, target_sql, user_id=actor.user_id)
    if res.error:
        return ToolResult(tool_id=call.tool_id, status="failed", summary=f"SQL error: {res.error}")

    return ToolResult(
        tool_id=call.tool_id,
        status="succeeded",
        summary=f"Table '{table_id}' query returned {res.row_count} rows:\n\n{res.markdown_table}",
    )


def _register_table_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            tool_id=QUERY_TABLE_TOOL_ID,
            operation="read",
            risk="read_only",
            description=(
                "Query structured table data using SQL or natural language aggregation (sum, average, count, max, min, filter, group by). "
                "Requires table_id, and either a SQL query or a natural language query."
            ),
            parameters=(
                ToolParameter(
                    name="table_id",
                    description="The table_id of the table to query.",
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
        ),
        _query_table_data,
    )


__all__ = [
    "DISABLE_CONNECTOR_TOOL_ID",
    "LIST_CONNECTORS_TOOL_ID",
    "QUERY_TABLE_TOOL_ID",
    "ToolStack",
    "get_tool_stack",
    "reset_tool_stack",
]
