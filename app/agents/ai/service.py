"""Specialized AI / Machine Learning Domain Agent Service.

Responsible for:
1. Deep Learning & Transformer architecture reasoning (Attention, KV cache, FLOPs)
2. Training dynamics, parameter scaling laws, fine-tuning (LoRA, QLoRA) analysis
3. Code and mathematical calculation verification using sandboxed evaluation
"""

from __future__ import annotations

import logging
import re

from app.agents.base import BaseSpecialistAgent
from app.agents.synthesizer.service import SynthesizerAgentService
from app.domain.contracts import ToolResult
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest
from app.services.observability.log_safety import question_ref
from app.tools.category import ToolCategory

logger = logging.getLogger(__name__)

AI_SPECIALIST_SYSTEM_PROMPT = """You are an AI & Machine Learning Research / Engineering Specialist Agent.
Your role is to analyze model architectures, training algorithms, compute budgets, and mathematical formulas.

Guidelines:
1. Provide precise technical insights into Transformer attention, optimization, and scaling laws.
2. Ground all claims in provided documentation or evidence using [E{k}] citation markers.
3. When mathematical or FLOPs calculations are present, explain the formula steps clearly.
4. Clearly contrast trade-offs (e.g. latency vs. throughput, dense vs. MoE, FP16 vs. INT4 quantization).
"""

_PARAM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*([bm])(?:\s*param(?:eter)?s?)?\b", re.IGNORECASE)
_PRECISION_RE = re.compile(r"\b(FP16|FP32|FP8|BF16|INT8|INT4|NF4)\b", re.IGNORECASE)
_CONTEXT_RE = re.compile(r"\b(\d+)\s*k\s*(?:tokens?|context|window)?\b", re.IGNORECASE)
_ARCH_RE = re.compile(
    r"\b(Transformer|MoE|Attention|GQA|MQA|MHA|RoPE|KV\s*Cache|LoRA|QLoRA|FlashAttention)\b", re.IGNORECASE
)


def extract_ai_specifications(text: str) -> dict[str, list[str]]:
    """Extract model parameters, precision formats, and architectural keywords."""
    params = [f"{m[0]}{m[1].upper()}" for m in _PARAM_RE.findall(text)]
    precisions = sorted({m.upper() for m in _PRECISION_RE.findall(text)})
    contexts = sorted({f"{m}k" for m in _CONTEXT_RE.findall(text)})
    archs = sorted(set(_ARCH_RE.findall(text)))
    return {
        "parameters": params,
        "precisions": precisions,
        "contexts": contexts,
        "architectures": archs,
    }


# None of this agent's skills names a shape `skills.py` describes, so they all
# map onto the general-purpose skill and the question stays the best signal --
# which is exactly what that module says to do for a skill that states no shape.
# An AI-specific answer template is a separate, authorable change; inventing one
# here would put a second answer shape in front of the model.
PIPELINE_SKILLS: dict[str, str] = {
    "compute_estimation": "ai_knowledge_assistant",
    "model_scaling_analysis": "ai_knowledge_assistant",
    "llm_architecture_reasoning": "ai_knowledge_assistant",
    "ai_deep_dive": "ai_knowledge_assistant",
}

SPECIFICATIONS_TOOL_ID = "querymind_ai_specification_extract"


def specification_tool_result(specs: dict[str, list[str]]) -> tuple[ToolResult, ...]:
    """Extracted model specifications, carried as a tool finding.

    Same reasoning as the cybersecurity agent's indicators: derived by regex from
    material the model can already read, so it must not arrive looking like a
    citable source.
    """

    lines = [f"{kind}: {', '.join(values)}" for kind, values in sorted(specs.items()) if values]
    if not lines:
        return ()
    return (
        ToolResult(
            tool_id=SPECIFICATIONS_TOOL_ID,
            status="succeeded",
            summary="Specifications extracted from the question and retrieved material -- " + "; ".join(lines),
        ),
    )


class AIAgentService(BaseSpecialistAgent):
    """Specialist agent for AI, Machine Learning, and LLM algorithms."""

    @property
    def agent_class(self) -> str:
        return "artificial_intelligence"

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return (
            "ai_deep_dive",
            "llm_architecture_reasoning",
            "model_scaling_analysis",
            "compute_estimation",
        )

    @property
    def default_tool_category(self) -> ToolCategory:
        return ToolCategory.ARTIFICIAL_INTELLIGENCE

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        return (
            "人工智能",
            "ai",
            "机器学习",
            "深度学习",
            "大模型",
            "llm",
            "神经网络",
            "rag",
            "提示词",
            "prompt",
            "transformer",
            "flops",
            "显存",
            "kv cache",
            "attention",
            "lora",
            "qlora",
        )

    @property
    def intent_patterns(self) -> tuple[str, ...]:
        return (
            r"\bflops\b",
            r"\bkv\s*cache\b",
            r"\btransformer\b",
            r"\bllm\b",
        )

    def pick_skill(self, question: str) -> str:
        text = (question or "").lower()
        if any(k in text for k in ["flops", "显存", "算力", "计算", "kv cache", "mb", "gb"]):
            return "compute_estimation"
        if any(k in text for k in ["架构", "attention", "transformer", "moe", "rope", "layer"]):
            return "llm_architecture_reasoning"
        if any(k in text for k in ["参数", "scaling", "缩放律", "chinchilla"]):
            return "model_scaling_analysis"
        return "ai_deep_dive"

    def __init__(self, synthesizer: SynthesizerAgentService | None = None) -> None:
        """Generation is delegated -- see `CybersecurityAgentService.__init__`.

        The same defect applied here: an optional `model_invoker` nothing ever
        supplied, so every AI-routed question was answered by a hardcoded
        template rather than by the configured chat model.
        """

        self._synthesizer = synthesizer or SynthesizerAgentService()

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: tuple[ToolResult, ...] = (),
        skill: str = "ai_deep_dive",
    ) -> CandidateAnswer:
        """Domain-shaped synthesis through the ordinary generation path."""

        logger.info(
            "AIAgent synthesizing candidate for query=%s skill=%s tools=%d",
            question_ref(request.question),
            skill,
            len(tool_results),
        )

        evidence_text = "\n".join(item.content for item in context.evidence)
        tool_text = "\n".join(result.summary for result in tool_results if result.summary)
        specs = extract_ai_specifications(
            f"{request.question}\n{context.rendered_context}\n{evidence_text}\n{tool_text}"
        )
        enriched = (*tool_results, *specification_tool_result(specs))
        pipeline_skill = PIPELINE_SKILLS.get(skill, "ai_knowledge_assistant")
        return await self._synthesizer.synthesize_candidate(request, context, enriched, pipeline_skill)


__all__ = ["AIAgentService", "AI_SPECIALIST_SYSTEM_PROMPT", "extract_ai_specifications"]
