"""Abstract base class for domain-specific specialist agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.services.observability.log_safety import question_ref

if TYPE_CHECKING:
    from app.agents.synthesizer.service import SynthesizerAgentService
    from app.domain.contracts import ToolResult
    from app.domain.workflow import CandidateAnswer, ContextBundle
    from app.orchestration.request import OrchestrationRequest
    from app.tools.category import ToolCategory

logger = logging.getLogger(__name__)


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

    # --- generation -------------------------------------------------------
    #
    # Written once here rather than twice in the two specialists. After
    # generation was delegated to `SynthesizerAgentService` the two bodies were
    # near-identical -- 31 shared substantive lines -- differing only in which
    # extractor ran, which tool id it reported under, and which skill it fell
    # back to. That is one shape repeated, and this repository twice records
    # "one definition is the better end state and was not made here" as a
    # regret; this is the place not to repeat it.

    #: Domain skill -> a skill `app/agents/synthesizer/skills.py` describes.
    #: Mapping rather than authoring a parallel template set is the rule that
    #: module states for itself.
    pipeline_skills: dict[str, str] = {}

    #: Where an unmapped skill lands. A security specialist must not fall
    #: through to the general template, which is why this is per-agent.
    fallback_pipeline_skill: str = "answer_with_citations"

    def __init__(self, synthesizer: SynthesizerAgentService | None = None) -> None:
        """Generation is delegated, never reimplemented.

        Both specialists used to hold an optional `model_invoker` and fall back
        to a hardcoded template when it was absent -- and the one construction
        site, `app/agents/registry.py`, passed nothing, so the fallback was the
        ONLY path that ever ran in production. Measured, "我们被 Log4Shell 打了
        吗？应该怎么处置？" came back as boilerplate answering neither question,
        with `[E1] [E2]` stapled to content-free sentences.

        Delegating inherits what the hand-rolled path had dropped: the
        configured chat model, `asyncio.to_thread` so the forward pass is off
        the event loop, streaming into `AnswerStreamStore` (the specialist path
        emitted no `answer_fragment` events at all), `[E{k}]` allow-listing, the
        documented no-evidence answer, and language forcing.
        """

        if synthesizer is None:
            from app.agents.synthesizer.service import SynthesizerAgentService as _Synth

            synthesizer = _Synth()
        self._synthesizer = synthesizer

    def domain_findings(self, text: str) -> ToolResult | None:
        """What this specialist extracts from the material, as a tool finding.

        Deliberately a `ToolResult` and not evidence: these are derived by regex
        from material the model can already read, so arriving as evidence would
        invite a citation pointing at a derivation rather than at a source.
        Returns None when there is nothing to report.
        """

        del text
        return None

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: Sequence[ToolResult] | tuple[ToolResult, ...] = (),
        skill: str = "",
    ) -> CandidateAnswer:
        """Domain-shaped synthesis through the ordinary generation path."""

        results = tuple(tool_results)
        logger.info(
            "%s synthesizing candidate for query=%s skill=%s tools=%d",
            self.__class__.__name__,
            # Never the question itself. Both specialists interpolated
            # `request.question` straight into a log line, and the guard that
            # exists for exactly that matched only the bare name.
            question_ref(request.question),
            skill,
            len(results),
        )

        evidence_text = "\n".join(item.content for item in context.evidence)
        tool_text = "\n".join(result.summary for result in results if result.summary)
        finding = self.domain_findings(f"{request.question}\n{context.rendered_context}\n{evidence_text}\n{tool_text}")
        enriched = (*results, finding) if finding is not None else results
        pipeline_skill = self.pipeline_skills.get(skill, self.fallback_pipeline_skill)
        return await self._synthesizer.synthesize_candidate(request, context, enriched, pipeline_skill)

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
