"""Data Analysis Domain Tool Provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory
from app.tools.data_analysis.tables import (
    TABLE_LIST_TOOL_DEFINITION,
    TABLE_QUERY_TOOL_DEFINITION,
    execute_table_list,
    execute_table_query,
)

if TYPE_CHECKING:
    from app.mcp.contracts import ToolDefinition
    from app.mcp.registry import ToolExecutor


class DataAnalysisToolProvider(BaseToolProvider):
    """Structured tables from the user's own documents: list them, then query one."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS

    @property
    def tool_definitions(self) -> tuple[ToolDefinition, ...]:
        return (TABLE_LIST_TOOL_DEFINITION, TABLE_QUERY_TOOL_DEFINITION)

    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        if tool_id == TABLE_LIST_TOOL_DEFINITION.tool_id:
            return execute_table_list
        if tool_id == TABLE_QUERY_TOOL_DEFINITION.tool_id:
            return execute_table_query
        return None


__all__ = ["DataAnalysisToolProvider"]
