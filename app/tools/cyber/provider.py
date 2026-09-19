"""Cybersecurity Domain Tool Provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory
from app.tools.cyber.cve_tools import (
    ATTACK_TOOL_DEFINITION,
    CVE_TOOL_DEFINITION,
    execute_cve_lookup,
    execute_mitre_attack_lookup,
)

if TYPE_CHECKING:
    from app.mcp.contracts import ToolDefinition
    from app.mcp.registry import ToolExecutor


class CybersecurityToolProvider(BaseToolProvider):
    """Provider for CVE intelligence and MITRE ATT&CK taxonomy tools."""

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CYBERSECURITY

    @property
    def tool_definitions(self) -> tuple[ToolDefinition, ...]:
        return (CVE_TOOL_DEFINITION, ATTACK_TOOL_DEFINITION)

    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        if tool_id == CVE_TOOL_DEFINITION.tool_id:
            return execute_cve_lookup
        if tool_id == ATTACK_TOOL_DEFINITION.tool_id:
            return execute_mitre_attack_lookup
        return None


__all__ = ["CybersecurityToolProvider"]
