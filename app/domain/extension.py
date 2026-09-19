"""Unified domain extension bundle combining specialist agent and tool provider."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.base import BaseSpecialistAgent
    from app.agents.registry import DomainAgentRegistry
    from app.tools.base import BaseToolProvider
    from app.tools.registry import DomainToolRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DomainExtensionBundle:
    """Encapsulates a unified vertical domain capability.

    Combines a domain specialist agent and its corresponding governed tool provider
    into a single cohesive unit. Allows 3rd-party developers or future modules
    to register both capabilities in one seamless call.
    """

    domain_id: str
    display_name: str
    agent: BaseSpecialistAgent
    tool_provider: BaseToolProvider | None = None

    def register(
        self,
        agent_registry: DomainAgentRegistry | None = None,
        tool_registry: DomainToolRegistry | None = None,
    ) -> None:
        """Register both agent and tool provider into their respective domain registries."""
        from app.agents.registry import get_domain_agent_registry
        from app.tools.registry import get_domain_tool_registry

        target_agent_reg = agent_registry or get_domain_agent_registry()
        target_agent_reg.register_agent(self.agent)

        if self.tool_provider is not None:
            target_tool_reg = tool_registry or get_domain_tool_registry()
            target_tool_reg.register_provider(self.tool_provider)

        logger.info(
            "Registered domain bundle '%s' (%s): agent=%s, tool_provider=%s",
            self.domain_id,
            self.display_name,
            self.agent.agent_class,
            self.tool_provider.__class__.__name__ if self.tool_provider else "None",
        )

    def describe(self) -> dict[str, Any]:
        """Provide diagnostic metadata about this domain extension bundle."""
        return {
            "domain_id": self.domain_id,
            "display_name": self.display_name,
            "agent": self.agent.describe(),
            "tool_provider": self.tool_provider.describe() if self.tool_provider else None,
        }


__all__ = ["DomainExtensionBundle"]
