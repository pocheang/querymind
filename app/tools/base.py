"""Abstract base class for extensible domain tool providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.tools.category import ToolCategory

if TYPE_CHECKING:
    from app.mcp.contracts import ToolDefinition
    from app.mcp.registry import ToolExecutor, ToolRegistry


class BaseToolProvider(ABC):
    """Base interface for all modular domain tool providers.

    Subclasses encapsulate tool schemas and executors for a specific domain
    (e.g. Cybersecurity, AI, Data Analysis). This architecture enables clean
    separation of concerns, automatic discovery, and effortless extension.
    """

    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """The tool category this provider serves."""
        ...

    @property
    @abstractmethod
    def tool_definitions(self) -> tuple[ToolDefinition, ...]:
        """All governed tool definitions provided by this module."""
        ...

    @abstractmethod
    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        """Return the async executor callable for a given tool_id, or None if unknown."""
        ...

    def register_into(self, registry: ToolRegistry) -> None:
        """Register all tools and executors from this provider into an MCP ToolRegistry."""
        for definition in self.tool_definitions:
            executor = self.get_executor(definition.tool_id)
            if executor is not None:
                registry.register(definition, executor)

    def describe(self) -> dict[str, Any]:
        """Provide diagnostic and schema summary of this tool provider."""
        return {
            "category": self.category.value,
            "tools_count": len(self.tool_definitions),
            "tool_ids": [d.tool_id for d in self.tool_definitions],
        }


def _arguments_to_dict(arguments: Any) -> dict[str, str]:
    if isinstance(arguments, dict):
        return {str(k): str(v) for k, v in arguments.items() if v is not None}
    if isinstance(arguments, tuple | list):
        result: dict[str, str] = {}
        for arg in arguments:
            name = getattr(arg, "name", None)
            val = getattr(arg, "value", None)
            if name is not None and val is not None:
                result[str(name)] = str(val)
        return result
    return {}


def extract_call_argument(call: Any, *names: str) -> str:
    """Extract argument value matching any of candidate parameter names."""
    arg_dict = _arguments_to_dict(getattr(call, "arguments", None))
    for name in names:
        val = arg_dict.get(name)
        if val and val.strip():
            return val.strip()
    return ""


__all__ = ["BaseToolProvider", "extract_call_argument"]
