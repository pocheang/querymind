"""AI / Machine Learning Domain Tool Provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.tools.ai.code_sandbox import AI_MATH_TOOL_DEFINITION, execute_ai_math_eval
from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory

if TYPE_CHECKING:
    from app.mcp.contracts import ToolDefinition
    from app.mcp.registry import ToolExecutor


class AIToolProvider(BaseToolProvider):
    """Provider for AI scaling laws and sandboxed mathematical evaluation tools."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ARTIFICIAL_INTELLIGENCE

    @property
    def tool_definitions(self) -> tuple[ToolDefinition, ...]:
        return (AI_MATH_TOOL_DEFINITION,)

    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        if tool_id == AI_MATH_TOOL_DEFINITION.tool_id:
            return execute_ai_math_eval
        return None


__all__ = ["AIToolProvider"]
