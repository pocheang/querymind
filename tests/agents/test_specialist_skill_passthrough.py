"""A specialist keeps the answer shape the router chose.

`BaseSpecialistAgent.synthesize_candidate` looked the router's skill up in the
specialist's own four-entry table and replaced anything else with its fallback.
The router may choose any skill in `VALID_SKILLS`, so measured before the fix:
`incident_response_playbook` and `cyber_defense_hardening` both became
`cyber_attack_analysis`, and a comparison routed to the AI specialist lost
`COMPARISON_TEMPLATE` -- the path without a specialist kept it, so being routed
to a specialist made the answer worse.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.agents.ai.service import AIAgentService
from app.agents.base import BaseSpecialistAgent
from app.agents.cybersecurity.service import CybersecurityAgentService
from app.agents.shared.config import SKILL_DEFAULT, VALID_SKILLS
from app.agents.synthesizer.skills import GENERAL_SKILLS, SKILL_QUERY_TYPES, SKILL_TEMPLATES
from app.domain.workflow import ContextBundle
from app.orchestration.request import OrchestrationRequest

SHAPED_SKILLS = sorted(set(SKILL_TEMPLATES) | set(SKILL_QUERY_TYPES))


class _RecordingSynthesizer:
    """Stands in for `SynthesizerAgentService` and records the skill it was given."""

    def __init__(self) -> None:
        self.skills: list[str] = []

    async def synthesize_candidate(self, request: Any, context: Any, tool_results: Any, skill: str) -> str:
        del request, context, tool_results
        self.skills.append(skill)
        return "candidate"


def _specialists() -> list[BaseSpecialistAgent]:
    return [CybersecurityAgentService(_RecordingSynthesizer()), AIAgentService(_RecordingSynthesizer())]


SPECIALISTS = pytest.mark.parametrize("specialist", _specialists(), ids=lambda s: s.agent_class)


@SPECIALISTS
@pytest.mark.parametrize("skill", SHAPED_SKILLS)
def test_a_shaped_router_skill_passes_through(specialist: BaseSpecialistAgent, skill: str):
    if skill in specialist.pipeline_skills:
        pytest.skip("the specialist names this skill itself; covered by the translation test")
    assert specialist.pipeline_skill_for(skill) == skill


@SPECIALISTS
def test_the_specialists_own_skills_are_translated(specialist: BaseSpecialistAgent):
    for own, target in specialist.pipeline_skills.items():
        assert specialist.pipeline_skill_for(own) == target


@SPECIALISTS
@pytest.mark.parametrize("skill", [*sorted(GENERAL_SKILLS), "", "not_a_skill"])
def test_a_shapeless_skill_lands_on_the_fallback(specialist: BaseSpecialistAgent, skill: str):
    # The rule the fallback exists for: a security question must not fall
    # through to the general template.
    assert specialist.pipeline_skill_for(skill) == specialist.fallback_pipeline_skill


@SPECIALISTS
@pytest.mark.parametrize("skill", [*sorted(VALID_SKILLS), "", "not_a_skill"])
def test_every_answer_is_a_skill_the_synthesizer_knows(specialist: BaseSpecialistAgent, skill: str):
    assert specialist.pipeline_skill_for(skill) in VALID_SKILLS


@pytest.mark.parametrize(
    ("specialist", "router_skill"),
    [
        (CybersecurityAgentService, "incident_response_playbook"),
        (CybersecurityAgentService, "cyber_defense_hardening"),
        (AIAgentService, "compare_entities"),
        (AIAgentService, "timeline_builder"),
    ],
)
def test_the_synthesizer_receives_the_routers_skill(specialist: type[BaseSpecialistAgent], router_skill: str):
    """End to end through `synthesize_candidate`, the method the synthesizer node calls."""

    recorder = _RecordingSynthesizer()
    agent = specialist(recorder)
    request = OrchestrationRequest(question="question")

    asyncio.run(agent.synthesize_candidate(request, ContextBundle(), (), router_skill))

    assert recorder.skills == [router_skill]


def test_the_default_skill_is_still_general():
    # Guards the shapeless set above: if the default gained a shape, the
    # fallback tests would stop meaning "a security question stays specialised".
    assert SKILL_DEFAULT in GENERAL_SKILLS
    assert SKILL_DEFAULT not in SKILL_TEMPLATES
