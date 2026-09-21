"""What the AI specialist contributes, and what it delegates.

Rewritten for the same reason as the cybersecurity suite next door: the
previous assertions pinned a hardcoded fallback template that was the only path
production ever ran, because the one construction site passed no
`model_invoker`.
"""

import pytest

from app.agents.ai.service import (
    PIPELINE_SKILLS,
    SPECIFICATIONS_TOOL_ID,
    AIAgentService,
    extract_ai_specifications,
    specification_tool_result,
)
from app.agents.shared.config import VALID_SKILLS
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest, RequestActor


def test_extract_ai_specifications() -> None:
    text = (
        "Fine-tuning 70B and 8B LLaMA-3 models using FP16 precision, "
        "128k context window, FlashAttention, and LoRA adapters."
    )
    specs = extract_ai_specifications(text)
    assert "70B" in specs["parameters"]
    assert "8B" in specs["parameters"]
    assert "FP16" in specs["precisions"]
    assert "128k" in specs["contexts"]
    assert any("FlashAttention" in a for a in specs["architectures"])
    assert any("LoRA" in a for a in specs["architectures"])


class _Recording:
    """Stands in for `SynthesizerAgentService` and records what it was handed."""

    def __init__(self) -> None:
        self.seen: dict[str, object] = {}

    async def synthesize_candidate(self, request, context, tool_results, skill):  # noqa: ANN001
        self.seen.update(request=request, context=context, tool_results=tool_results, skill=skill)
        return CandidateAnswer(text="generated [E1]")


@pytest.mark.asyncio
async def test_it_delegates_generation_rather_than_writing_the_answer_itself() -> None:
    recorder = _Recording()
    agent = AIAgentService(synthesizer=recorder)
    req = OrchestrationRequest(
        question="训练一个 7B 模型需要多少 FLOPs?",
        actor=RequestActor(user_id="u", tenant_id="t", role="user"),
    )
    context = ContextBundle(evidence=())

    candidate = await agent.synthesize_candidate(req, context, (), "compute_estimation")

    assert candidate.text == "generated [E1]"
    assert recorder.seen["request"] is req


@pytest.mark.parametrize(("domain_skill", "pipeline_skill"), sorted(PIPELINE_SKILLS.items()))
def test_every_domain_skill_maps_onto_a_skill_the_pipeline_knows(domain_skill: str, pipeline_skill: str) -> None:
    assert pipeline_skill in VALID_SKILLS


@pytest.mark.asyncio
async def test_extracted_specifications_arrive_as_a_tool_finding() -> None:
    recorder = _Recording()
    agent = AIAgentService(synthesizer=recorder)
    req = OrchestrationRequest(
        question="7B 模型 fp16 精度下 32k 上下文的显存占用",
        actor=RequestActor(user_id="u", tenant_id="t", role="user"),
    )

    await agent.synthesize_candidate(req, ContextBundle(evidence=()), ())

    results = recorder.seen["tool_results"]
    assert any(r.tool_id == SPECIFICATIONS_TOOL_ID for r in results)


def test_no_specification_result_is_produced_when_nothing_was_extracted() -> None:
    assert specification_tool_result({"parameters": [], "precisions": []}) is None
