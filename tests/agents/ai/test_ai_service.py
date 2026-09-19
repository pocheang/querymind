"""Unit tests for AIAgentService."""

import pytest

from app.agents.ai.service import (
    AI_SPECIALIST_SYSTEM_PROMPT,
    AIAgentService,
    extract_ai_specifications,
)
from app.domain.contracts import EvidenceItem, ToolResult
from app.domain.workflow import ContextBundle
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


@pytest.mark.asyncio
async def test_ai_agent_deterministic_synthesis() -> None:
    agent = AIAgentService()
    req = OrchestrationRequest(
        question="What is the compute required for a 7B model on 2T tokens?",
        actor=RequestActor(user_id="researcher", tenant_id="t1", role="user"),
    )
    context = ContextBundle(
        evidence=(
            EvidenceItem(
                item_id="ev_ai_1",
                document_id="doc_chinchilla",
                source="chinchilla_paper.pdf",
                content="Optimal compute allocation is 6 * P * D FLOPs.",
            ),
        )
    )
    tool_results = (
        ToolResult(
            tool_id="querymind_ai_math_eval",
            status="succeeded",
            summary="Evaluated '6 * 7e9 * 2e12' = 8.400000e+22",
        ),
    )

    candidate = await agent.synthesize_candidate(
        request=req,
        context=context,
        tool_results=tool_results,
        skill="ai_knowledge_assistant",
    )

    assert len(candidate.citations) == 1
    assert candidate.citations[0].document_id == "doc_chinchilla"
    assert "8.400000e+22" in candidate.text
    assert "[E1]" in candidate.text
    assert "算法计算与沙箱核验" in candidate.text
    assert "提取算法与架构参数" in candidate.text


@pytest.mark.asyncio
async def test_ai_agent_empty_evidence() -> None:
    agent = AIAgentService()
    req = OrchestrationRequest(
        question="How does MQA differ from GQA?",
        actor=RequestActor(user_id="user", tenant_id="t1", role="user"),
    )
    context = ContextBundle(evidence=())
    candidate = await agent.synthesize_candidate(req, context)
    assert len(candidate.citations) == 0
    assert "本地知识库未检索到专属文档" in candidate.text


@pytest.mark.asyncio
async def test_ai_agent_custom_invoker() -> None:
    async def mock_invoker(prompt: str) -> str:
        assert AI_SPECIALIST_SYSTEM_PROMPT in prompt
        assert "FlashAttention" in prompt
        return "Specialist Model: IO-aware attention reduces memory access [E1]."

    agent = AIAgentService(model_invoker=mock_invoker)
    req = OrchestrationRequest(
        question="How does FlashAttention work?",
        actor=RequestActor(user_id="user", tenant_id="t1", role="user"),
    )
    context = ContextBundle(
        evidence=(EvidenceItem(item_id="e1", document_id="d1", source="s1", content="FlashAttention paper"),)
    )
    candidate = await agent.synthesize_candidate(req, context)
    assert "Specialist Model: IO-aware attention reduces memory access [E1]." in candidate.text
