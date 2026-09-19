"""Centralized Registry and Discovery for Domain Specialist Agents."""

from __future__ import annotations

import logging
import re
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.base import BaseSpecialistAgent

logger = logging.getLogger(__name__)


class DomainAgentRegistry:
    """Manages domain specialist agents and enables dynamic polymorphism in orchestration.

    Acts as the single source of truth for specialist agents. New vertical domains
    (e.g., Code Review, Finance, Compliance) can register their agent implementations
    without modifying core LangGraph orchestration nodes.
    """

    def __init__(self) -> None:
        self._agents: dict[str, BaseSpecialistAgent] = {}
        self._skill_map: dict[str, BaseSpecialistAgent] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def register_agent(self, agent: BaseSpecialistAgent) -> None:
        """Register a new domain specialist agent."""
        with self._lock:
            key = agent.agent_class.strip().lower()
            self._agents[key] = agent
            for skill in agent.supported_skills:
                self._skill_map[skill.strip().lower()] = agent
            logger.debug(
                "Registered specialist agent '%s' (class=%s, skills=%s)",
                agent.__class__.__name__,
                key,
                agent.supported_skills,
            )

    def get_agent(self, agent_class: str) -> BaseSpecialistAgent | None:
        """Retrieve a specialist agent by its canonical agent_class."""
        self._ensure_defaults()
        with self._lock:
            return self._agents.get(agent_class.strip().lower())

    def get_agent_for_skill(self, skill: str) -> BaseSpecialistAgent | None:
        """Retrieve a specialist agent that declares support for a specific skill."""
        self._ensure_defaults()
        with self._lock:
            return self._skill_map.get(skill.strip().lower())

    def match_agent_class(self, question: str) -> str | None:
        """Dynamically match a question to a registered agent class based on intent metadata."""
        text = (question or "").strip().lower()
        if not text:
            return None

        self._ensure_defaults()
        with self._lock:
            # 1. Regex pattern check (highest precedence)
            for agent in self._agents.values():
                for pat in agent.intent_patterns:
                    if re.search(pat, text, re.IGNORECASE):
                        return agent.agent_class

            # 2. Keyword frequency match
            best_agent: str | None = None
            best_score = 0
            for agent in self._agents.values():
                score = sum(1 for kw in agent.intent_keywords if kw.lower() in text)
                if score > best_score:
                    best_score = score
                    best_agent = agent.agent_class

            if best_score > 0 and best_agent is not None:
                return best_agent
            return None

    def pick_skill_for_agent(self, agent_class: str, question: str) -> str | None:
        """Ask the corresponding specialist agent to pick the most appropriate skill."""
        agent = self.get_agent(agent_class)
        if agent is not None:
            return agent.pick_skill(question)
        return None

    def list_agents(self) -> tuple[BaseSpecialistAgent, ...]:
        """Retrieve all registered specialist agents."""
        self._ensure_defaults()
        with self._lock:
            return tuple(self._agents.values())

    def list_agent_classes(self) -> tuple[str, ...]:
        """Retrieve all registered agent class identifiers."""
        self._ensure_defaults()
        with self._lock:
            return tuple(sorted(self._agents.keys()))

    def describe(self) -> dict[str, Any]:
        """Provide diagnostic metadata of all registered specialist agents."""
        self._ensure_defaults()
        with self._lock:
            return {
                "total_agents": len(self._agents),
                "agent_classes": sorted(self._agents.keys()),
                "agents": {k: a.describe() for k, a in self._agents.items()},
            }

    def _ensure_defaults(self) -> None:
        """Lazily initialize core built-in specialist agents if registry is empty."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            try:
                from app.agents.ai.service import AIAgentService
                from app.agents.cybersecurity.service import CybersecurityAgentService

                cyber_agent = CybersecurityAgentService()
                ai_agent = AIAgentService()

                self._agents[cyber_agent.agent_class.strip().lower()] = cyber_agent
                for s in cyber_agent.supported_skills:
                    self._skill_map[s.strip().lower()] = cyber_agent

                self._agents[ai_agent.agent_class.strip().lower()] = ai_agent
                for s in ai_agent.supported_skills:
                    self._skill_map[s.strip().lower()] = ai_agent

                self._initialized = True
            except Exception as err:
                logger.warning("Failed to auto-register built-in domain agents: %s", err)
                self._initialized = True


_REGISTRY_LOCK = threading.Lock()
_GLOBAL_AGENT_REGISTRY: DomainAgentRegistry | None = None


def get_domain_agent_registry() -> DomainAgentRegistry:
    """Retrieve or create the global singleton DomainAgentRegistry."""
    global _GLOBAL_AGENT_REGISTRY
    if _GLOBAL_AGENT_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _GLOBAL_AGENT_REGISTRY is None:
                _GLOBAL_AGENT_REGISTRY = DomainAgentRegistry()
    return _GLOBAL_AGENT_REGISTRY


def reset_domain_agent_registry() -> None:
    """Reset the global singleton registry (intended for test isolation)."""
    global _GLOBAL_AGENT_REGISTRY
    with _REGISTRY_LOCK:
        _GLOBAL_AGENT_REGISTRY = None


__all__ = [
    "DomainAgentRegistry",
    "get_domain_agent_registry",
    "reset_domain_agent_registry",
]
