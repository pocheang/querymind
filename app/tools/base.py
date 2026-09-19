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


__all__ = ["BaseToolProvider"]
