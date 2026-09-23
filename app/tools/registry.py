"""Centralized Registry and Discovery for Extensible Domain Tool Providers."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory

if TYPE_CHECKING:
    from app.mcp.contracts import ToolDefinition
    from app.mcp.registry import ToolRegistry

logger = logging.getLogger(__name__)


class DomainToolRegistry:
    """Manages categorized tool providers and enables seamless future extensibility.

    Acts as the single source of truth for high-level tool domains. External modules,
    plugins, or new specialist agents can register additional tool providers without
    altering core MCP runtime or LangGraph orchestration logic.
    """

    def __init__(self) -> None:
        self._providers: dict[ToolCategory, list[BaseToolProvider]] = {cat: [] for cat in ToolCategory}
        # Registration order across categories, built-ins first. It decides which
        # provider owns a tool id two of them declare -- see `register_all_into`.
        self._ordered: list[BaseToolProvider] = []
        self._lock = threading.Lock()
        self._initialized = False
        self._exported = False

    def register_provider(self, provider: BaseToolProvider) -> None:
        """Register a domain tool provider; a later one overrides a tool id an earlier one declared.

        Registration only reaches the MCP registry through `register_all_into`,
        which runs once, when the governed tool stack is first built. A provider
        registered after that is logged rather than silently absent: it reaches
        the running stack only if the stack is rebuilt.
        """
        with self._lock:
            cat_list = self._providers.setdefault(provider.category, [])
            if any(p.__class__ == provider.__class__ for p in cat_list):
                return
            cat_list.append(provider)
            self._ordered.append(provider)
            if self._exported:
                logger.warning(
                    "Tool provider '%s' registered after the tool stack was built; it is not in the running stack",
                    provider.__class__.__name__,
                )
            logger.debug(
                "Registered tool provider '%s' under category '%s' (%d tools)",
                provider.__class__.__name__,
                provider.category.value,
                len(provider.tool_definitions),
            )

    def get_providers(self, category: ToolCategory | str | None = None) -> tuple[BaseToolProvider, ...]:
        """Retrieve all providers, optionally filtered by ToolCategory."""
        self._ensure_defaults()
        with self._lock:
            if category is None:
                all_p = []
                for prov_list in self._providers.values():
                    all_p.extend(prov_list)
                return tuple(all_p)

            cat_enum = ToolCategory(category) if isinstance(category, str) else category
            return tuple(self._providers.get(cat_enum, []))

    def get_tools_by_category(self, category: ToolCategory | str) -> tuple[ToolDefinition, ...]:
        """Retrieve all tool definitions under a given category."""
        providers = self.get_providers(category)
        tools = []
        for p in providers:
            tools.extend(p.tool_definitions)
        return tuple(tools)

    def list_all_tools(self) -> tuple[ToolDefinition, ...]:
        """Retrieve all governed tool definitions across all categories."""
        providers = self.get_providers()
        tools = []
        for p in providers:
            tools.extend(p.tool_definitions)
        return tuple(tools)

    def register_all_into(self, mcp_registry: ToolRegistry) -> None:
        """Register every tool into an MCP ToolRegistry, each tool id exactly once.

        When two providers declare one tool id, the later-registered provider
        owns it -- which is what lets an extension replace a built-in, say the
        curated offline CVE table with a live feed. The MCP registry refuses a
        duplicate id with `ValueError`, and this used to hand it both: building
        the governed tool stack then raised on every call, taking the connector
        and approval tools down with the one that collided.
        """
        self._ensure_defaults()
        with self._lock:
            ordered = list(self._ordered)
            self._exported = True
        owners: dict[str, tuple[ToolDefinition, BaseToolProvider]] = {}
        for provider in ordered:
            for definition in provider.tool_definitions:
                previous = owners.get(definition.tool_id)
                if previous is not None:
                    logger.warning(
                        "Tool '%s' from '%s' is overridden by '%s'",
                        definition.tool_id,
                        previous[1].__class__.__name__,
                        provider.__class__.__name__,
                    )
                owners[definition.tool_id] = (definition, provider)
        count = 0
        for tool_id, (definition, provider) in owners.items():
            executor = provider.get_executor(tool_id)
            if executor is not None:
                mcp_registry.register(definition, executor)
                count += 1
        logger.info("Registered %d domain specialist tools into MCP ToolRegistry", count)

    def describe(self) -> dict[str, Any]:
        """Provide detailed diagnostic metadata about all registered providers."""
        self._ensure_defaults()
        summary = {}
        for cat, prov_list in self._providers.items():
            if prov_list:
                summary[cat.value] = [p.describe() for p in prov_list]
        return summary

    def _ensure_defaults(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            # Register built-in domain providers. They go FIRST in registration
            # order whenever they are added, so a provider an extension
            # registered earlier still overrides them, and one of the same class
            # is not added twice.
            from app.tools.ai.provider import AIToolProvider
            from app.tools.cyber.provider import CybersecurityToolProvider

            defaults: list[BaseToolProvider] = []
            for provider in (CybersecurityToolProvider(), AIToolProvider()):
                cat_list = self._providers.setdefault(provider.category, [])
                if not any(p.__class__ == provider.__class__ for p in cat_list):
                    cat_list.insert(0, provider)
                    defaults.append(provider)
            self._ordered[:0] = defaults
            self._initialized = True


_GLOBAL_REGISTRY: DomainToolRegistry | None = None
_REGISTRY_LOCK = threading.Lock()


def get_domain_tool_registry() -> DomainToolRegistry:
    """Return the process-wide DomainToolRegistry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is not None:
        return _GLOBAL_REGISTRY
    with _REGISTRY_LOCK:
        if _GLOBAL_REGISTRY is None:
            registry = DomainToolRegistry()
            registry._ensure_defaults()
            _GLOBAL_REGISTRY = registry
        return _GLOBAL_REGISTRY


def reset_domain_tool_registry() -> None:
    """Reset the global registry singleton (primarily for tests)."""
    global _GLOBAL_REGISTRY
    with _REGISTRY_LOCK:
        _GLOBAL_REGISTRY = None


__all__ = [
    "DomainToolRegistry",
    "get_domain_tool_registry",
    "reset_domain_tool_registry",
]
