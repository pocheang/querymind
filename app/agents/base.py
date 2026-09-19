"""Abstract base class for domain-specific specialist agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.contracts import ToolResult
    from app.domain.workflow import CandidateAnswer, ContextBundle
    from app.orchestration.request import OrchestrationRequest
    from app.tools.category import ToolCategory


class BaseSpecialistAgent(ABC):
    """Contract for all domain specialist agents.

    A specialist agent encapsulates domain prompts, indicator/entity extraction,
    and grounded synthesis with citations for queries belonging to its domain
    (e.g., Cybersecurity, Artificial Intelligence, Data Analysis).
    """

    @property
    @abstractmethod
    def agent_class(self) -> str:
        """Canonical identifier for the domain agent (e.g. 'cybersecurity', 'ai')."""
        ...

    @property
    def supported_skills(self) -> tuple[str, ...]:
        """Skill identifiers that this specialist agent is prepared to handle."""
        return ()

    @property
    def default_tool_category(self) -> ToolCategory | None:
        """Tool category canonically associated with this domain specialist, if any."""
        return None

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        """Domain keywords used by router to identify user requests for this agent."""
        return ()

    @property
    def intent_patterns(self) -> tuple[str, ...]:
        """Regex pattern strings used by router for intent matching."""
        return ()

    def pick_skill(self, question: str) -> str:
        """Propose the most appropriate skill for a given user question."""
        skills = self.supported_skills
        return skills[0] if skills else "answer_with_citations"

    @abstractmethod
    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: Sequence[ToolResult] | tuple[ToolResult, ...],
        skill: str,
    ) -> CandidateAnswer:
        """Synthesize a domain-grounded candidate answer using context and tool results."""
        ...

    def describe(self) -> dict[str, Any]:
        """Provide diagnostic metadata about this specialist agent."""
        cat = self.default_tool_category
        return {
            "agent_class": self.agent_class,
            "supported_skills": list(self.supported_skills),
            "tool_category": cat.value if cat is not None else None,
            "intent_keywords": list(self.intent_keywords),
            "service_class": self.__class__.__name__,
        }


__all__ = ["BaseSpecialistAgent"]
