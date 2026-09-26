"""Centralized Registry and Discovery for Domain Specialist Agents."""

from __future__ import annotations

import logging
import re
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from app.agents.catalog import AgentClass
from app.services.query.keyword_match import count_keywords

if TYPE_CHECKING:
    from app.agents.base import BaseSpecialistAgent

logger = logging.getLogger(__name__)

#: What one matching intent pattern is worth, in keyword hits.
PATTERN_WEIGHT = 3


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
        # Built-in agents not yet registered, by agent class. An entry leaves
        # only when its agent is registered or its class is already taken, so a
        # default that failed to build is retried rather than forgotten.
        self._pending_defaults: dict[str, Callable[[], BaseSpecialistAgent]] = dict(_BUILTIN_AGENT_FACTORIES)
        self._default_failures: dict[str, str] = {}

    def register_agent(self, agent: BaseSpecialistAgent) -> None:
        """Register a domain specialist agent, replacing any with the same class.

        A registered agent always outranks a built-in default of the same class,
        whichever happens first. Registering used to leave the defaults pending,
        so the first lookup afterwards built the built-in and wrote it over the
        extension's agent -- the one thing the registry exists to allow.
        """
        with self._lock:
            self._register_locked(agent)
            logger.debug(
                "Registered specialist agent '%s' (class=%s, skills=%s)",
                agent.__class__.__name__,
                agent.agent_class.strip().lower(),
                agent.supported_skills,
            )

    def _register_locked(self, agent: BaseSpecialistAgent) -> None:
        key = agent.agent_class.strip().lower()
        self._agents[key] = agent
        self._pending_defaults.pop(key, None)
        self._default_failures.pop(key, None)
        for skill in agent.supported_skills:
            self._skill_map[skill.strip().lower()] = agent

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
            # One score per agent: each keyword it finds, as a word rather than
            # a substring (see keyword_match), plus PATTERN_WEIGHT for each of its
            # patterns. A pattern hit used to return on the spot, ahead of every
            # keyword, so one generic word decided the whole question.
            best_agent: str | None = None
            best_score = 0
            for agent in self._agents.values():
                score = count_keywords(text, agent.intent_keywords)
                score += PATTERN_WEIGHT * sum(1 for pat in agent.intent_patterns if re.search(pat, text, re.IGNORECASE))
                if score > best_score:
                    best_score = score
                    best_agent = agent.agent_class
            return best_agent

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

    def list_skills(self) -> tuple[str, ...]:
        """Every skill any registered specialist declares.

        Added because `routing._is_valid_skill` already called it: the call sat
        inside `except Exception: return False`, so the AttributeError was
        swallowed and an extension-declared skill could never validate -- the
        branch read as working and rejected everything.
        """

        self._ensure_defaults()
        with self._lock:
            return tuple(sorted(self._skill_map.keys()))

    def describe(self) -> dict[str, Any]:
        """Provide diagnostic metadata of all registered specialist agents."""
        self._ensure_defaults()
        with self._lock:
            return {
                "total_agents": len(self._agents),
                "agent_classes": sorted(self._agents.keys()),
                "agents": {k: a.describe() for k, a in self._agents.items()},
                # A built-in that could not be built is reported, not hidden:
                # without this an unavailable specialist reads exactly like one
                # that was never shipped.
                "unavailable_defaults": dict(sorted(self._default_failures.items())),
            }

    def _ensure_defaults(self) -> None:
        """Build any built-in specialist not yet registered, one at a time.

        Each default is built on its own. They were built together inside one
        `try`, so one failure registered neither; the registry was then marked
        initialized anyway, never retried, and every domain route became
        `general` for the life of the process behind a single warning. Now a
        failed default stays pending and is retried on the next lookup, its
        first failure is logged with the traceback, and `describe` names it.
        """

        if not self._pending_defaults:
            return
        with self._lock:
            # Built first, registered after: registering removes the entry from
            # `_pending_defaults`, so doing it inside the loop would change the
            # dict being iterated.
            built: list[BaseSpecialistAgent] = []
            for agent_class, factory in self._pending_defaults.items():
                try:
                    built.append(factory())
                except Exception as err:  # an agent module may raise anything on import
                    first = agent_class not in self._default_failures
                    self._default_failures[agent_class] = f"{type(err).__name__}: {err}"
                    if first:
                        logger.exception("Built-in specialist '%s' could not be built", agent_class)
                    else:
                        logger.debug("Built-in specialist '%s' still unavailable: %s", agent_class, err)
            for agent in built:
                self._register_locked(agent)


def _build_cybersecurity_agent() -> BaseSpecialistAgent:
    from app.agents.cybersecurity.service import CybersecurityAgentService

    return CybersecurityAgentService()


def _build_ai_agent() -> BaseSpecialistAgent:
    from app.agents.ai.service import AIAgentService

    return AIAgentService()


#: Keyed by the agent class each factory builds, so a class an extension has
#: already registered is skipped without building the built-in at all.
_BUILTIN_AGENT_FACTORIES: dict[str, Callable[[], BaseSpecialistAgent]] = {
    AgentClass.CYBERSECURITY: _build_cybersecurity_agent,
    AgentClass.ARTIFICIAL_INTELLIGENCE: _build_ai_agent,
}

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
