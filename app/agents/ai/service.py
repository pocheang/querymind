"""Specialized AI / Machine Learning Domain Agent Service.

Responsible for:
1. Deep Learning & Transformer architecture reasoning (Attention, KV cache, FLOPs)
2. Training dynamics, parameter scaling laws, fine-tuning (LoRA, QLoRA) analysis
3. Code and mathematical calculation verification using sandboxed evaluation
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents.base import BaseSpecialistAgent
from app.domain.contracts import ToolResult
from app.domain.knowledge import EvidenceRef
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest
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

_PARAM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*([BbMm])(?:\s*params?|\s*parameters?)?\b", re.IGNORECASE)
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
    archs = sorted({m for m in _ARCH_RE.findall(text)})
    return {
        "parameters": params,
        "precisions": precisions,
        "contexts": contexts,
        "architectures": archs,
    }


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

    def __init__(self, model_invoker: Any | None = None) -> None:
        self._model_invoker = model_invoker

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: tuple[ToolResult, ...] = (),
        skill: str = "ai_knowledge_assistant",
    ) -> CandidateAnswer:
        """Synthesize a domain-specialized AI algorithm candidate answer."""
        logger.info(
            "AIAgent synthesizing candidate for query='%s' skill='%s' tools=%d",
            request.question,
            skill,
            len(tool_results),
        )

        references = tuple(
            EvidenceRef(
                document_id=item.document_id,
                version=item.version,
                page=item.page,
                chunk_id=item.chunk_id,
                image_id=item.image_id,
            )
            for item in context.evidence
        )

        tool_snippets = []
        for tr in tool_results:
            if tr.status == "succeeded" and tr.summary:
                tool_snippets.append(f"[计算沙箱核验 ({tr.tool_id})]: {tr.summary}")

        tools_context = "\n".join(tool_snippets)

        # Extract AI / ML specifications from question, context, and evidence chunks
        evidence_text = "\n".join(item.content for item in context.evidence)
        combined_text = f"{request.question}\n{context.rendered_context}\n{evidence_text}\n{tools_context}"
        ai_specs = extract_ai_specifications(combined_text)

        # 1. Try invoking model if custom invoker is provided
        if self._model_invoker is not None:
            try:
                prompt = (
                    f"{AI_SPECIALIST_SYSTEM_PROMPT}\n\n"
                    f"Specialist Skill: {skill}\n"
                    f"User AI Query: {request.question}\n\n"
                    f"Retrieved Technical Evidence:\n{context.rendered_context or evidence_text}\n\n"
                    f"Calculation / Sandbox Findings:\n{tools_context}\n\n"
                    f"Provide rigorous AI architecture/algorithm analysis citing [E1], [E2] markers:"
                )
                raw_response = await self._model_invoker(prompt)
                text = raw_response if isinstance(raw_response, str) else str(raw_response)
                return CandidateAnswer(text=text, citations=references)
            except Exception as e:
                logger.warning("AIAgent model synthesis failed, using deterministic fallback: %s", e)

        # 2. Deterministic structured fallback
        sections = []
        if tool_snippets:
            sections.append("### 算法计算与沙箱核验\n" + "\n".join(f"- {s}" for s in tool_snippets))

        if any(ai_specs.values()):
            spec_lines = []
            if ai_specs["parameters"]:
                spec_lines.append(f"- 模型规模/参数量: {', '.join(ai_specs['parameters'])}")
            if ai_specs["precisions"]:
                spec_lines.append(f"- 精度规格: {', '.join(ai_specs['precisions'])}")
            if ai_specs["contexts"]:
                spec_lines.append(f"- 上下文窗口: {', '.join(ai_specs['contexts'])}")
            if ai_specs["architectures"]:
                spec_lines.append(f"- 涉及架构机制: {', '.join(ai_specs['architectures'])}")
            if spec_lines:
                sections.append("### 提取算法与架构参数 (AI Specifications)\n" + "\n".join(spec_lines))

        if context.evidence:
            sections.append(
                f"### AI 架构与算法分析（基于材料证据 [E1]）\n"
                f"关于 '{request.question}'，核心技术点如下：\n"
                f"- 模型机制与原理：依据已有技术资料，该架构聚焦于提升注意力计算效率与表征能力 [E1]。\n"
                f"- 工程与落地考量：在训练与推理部署时，建议综合权衡显存带宽占用（Memory Bandwidth）与并行加速比 [E1]。"
            )
        else:
            sections.append(
                f"关于 AI 技术问题 '{request.question}'，本地知识库未检索到专属文档，建议参考标准学术论文或开源官方技术规范。"
            )

        final_text = "\n\n".join(sections)
        return CandidateAnswer(text=final_text, citations=references)


__all__ = ["AIAgentService", "AI_SPECIALIST_SYSTEM_PROMPT", "extract_ai_specifications"]
