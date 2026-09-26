"""Specialized AI / Machine Learning Domain Agent Service.

Responsible for:
1. Deep Learning & Transformer architecture reasoning (Attention, KV cache, FLOPs)
2. Training dynamics, parameter scaling laws, fine-tuning (LoRA, QLoRA) analysis
3. Code and mathematical calculation verification using sandboxed evaluation
"""

from __future__ import annotations

import re

from app.agents.base import BaseSpecialistAgent
from app.agents.catalog import AgentClass
from app.domain.contracts import ToolResult
from app.tools.category import ToolCategory

# There is no domain system prompt here. One was written and exported and nothing
# ever read it -- generation goes through `SynthesizerAgentService`, whose skill
# templates are where answer guidance lives -- so it was deleted rather than
# wired in: a second instruction block would compete with the template.

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


# One skill, because there is one answer shape. There used to be four --
# compute_estimation, model_scaling_analysis, llm_architecture_reasoning,
# ai_deep_dive -- chosen by substring tests (`"layer"` matched "multiplayer",
# `"mb"` matched almost anything), and all four mapped onto the same
# `ai_knowledge_assistant`, so the choice changed a label and nothing else.
# An AI-specific answer template would be a separate, authorable change; until
# one exists a second skill name is a distinction the answer does not make.
PIPELINE_SKILLS: dict[str, str] = {
    "ai_deep_dive": "ai_knowledge_assistant",
}

SPECIFICATIONS_TOOL_ID = "querymind_ai_specification_extract"


def specification_tool_result(specs: dict[str, list[str]]) -> ToolResult | None:
    """Extracted model specifications, carried as a tool finding.

    Same reasoning as the cybersecurity agent's indicators: derived by regex from
    material the model can already read, so it must not arrive looking like a
    citable source.
    """

    lines = [f"{kind}: {', '.join(values)}" for kind, values in sorted(specs.items()) if values]
    if not lines:
        # `ToolResult | None` rather than a 0-or-1 tuple (`python:S3800`):
        # "the finding, or nothing" is what this means, and the caller splices.
        return None
    return ToolResult(
        tool_id=SPECIFICATIONS_TOOL_ID,
        status="succeeded",
        derived=True,
        summary="Specifications extracted from the question and retrieved material -- " + "; ".join(lines),
    )


class AIAgentService(BaseSpecialistAgent):
    """Specialist agent for AI, Machine Learning, and LLM algorithms."""

    @property
    def agent_class(self) -> str:
        return AgentClass.ARTIFICIAL_INTELLIGENCE

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("ai_deep_dive",)

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

    # No `intent_patterns`. There were four -- `\bflops\b`, `\bkv\s*cache\b`,
    # `\btransformer\b`, `\bllm\b` -- each the same word as a keyword above,
    # there only to add the word boundary keyword matching lacked. Keywords are
    # matched as words now, and a pattern is worth PATTERN_WEIGHT keyword hits,
    # so each of these made one word count four times: "LLM 遭遇 prompt 注入攻击怎么
    # 防护" scored 5 here against 2 for the security specialist.

    # The three things that are actually this specialist's. Everything else --
    # delegation, logging, the extraction-as-tool-finding splice, the skill
    # fallback -- lives once in `BaseSpecialistAgent`.
    pipeline_skills = PIPELINE_SKILLS
    fallback_pipeline_skill = "ai_knowledge_assistant"

    def domain_findings(self, text: str) -> ToolResult | None:
        return specification_tool_result(extract_ai_specifications(text))


__all__ = ["PIPELINE_SKILLS", "AIAgentService", "extract_ai_specifications"]
