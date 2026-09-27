"""Typed AI engineering estimates: memory and compute, with the formula and every assumption written out.

The free-form calculator (`querymind_ai_math_eval`) leaves the model to write
the formula, and a model once passed "2 bytes per parameter" to a helper whose
second argument is bits. These tools take the quantities a question actually
states and do the arithmetic themselves. Two rules follow from the plan (3):

- **The selector supplies only what the user said.** Everything else is either
  a named default the summary calls an assumption ("batch 1, assumed: not
  given"), or left out and said to be left out. Architecture details -- layers,
  KV heads, head size -- have no honest default, so KV cache is computed only
  when all three are given; guessing them is how a confident wrong number is made.
- **The summary shows its work**: formula, substitution, result, and what the
  number excludes. A reader who disagrees with an assumption can redo it.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from app.domain.contracts import ToolResult
from app.mcp.contracts import ToolCall, ToolDefinition, ToolParameter
from app.orchestration.request import RequestActor
from app.tools.base import extract_call_argument

__all__ = [
    "COMPUTE_ESTIMATE_TOOL_DEFINITION",
    "MEMORY_ESTIMATE_TOOL_DEFINITION",
    "Estimate",
    "compute_estimate",
    "execute_compute_estimate",
    "execute_memory_estimate",
    "memory_estimate",
    "parse_count",
]

GIB = 1024**3
# Bytes per parameter for each weight precision a question is likely to name.
PRECISION_BYTES: dict[str, float] = {
    "fp32": 4.0,
    "float32": 4.0,
    "tf32": 4.0,
    "fp16": 2.0,
    "float16": 2.0,
    "half": 2.0,
    "bf16": 2.0,
    "bfloat16": 2.0,
    "fp8": 1.0,
    "int8": 1.0,
    "8bit": 1.0,
    "int4": 0.5,
    "4bit": 0.5,
    "nf4": 0.5,
    "q4": 0.5,
}
# Mixed-precision Adam: 2 (weights) + 2 (gradients) + 4 (FP32 master copy) + 8 (Adam m and v).
TRAINING_BYTES_PER_PARAM = 16.0
DEFAULT_MFU = 0.40
CHINCHILLA_TOKENS_PER_PARAM = 20.0

_SUFFIX = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "billion": 1e9, "t": 1e12, "trillion": 1e12}
_COUNT = re.compile(r"\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]{1,3})?)\s*([a-z]{0,8})\s*", re.IGNORECASE)


class EstimateInputError(ValueError):
    """A quantity that cannot be read as stated. The message says how to state it."""


@dataclass
class Estimate:
    inputs: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    def summary(self, title: str) -> str:
        # The inputs are restated so the answer's echo of the question -- "32k
        # context, batch 4" -- has a source: without it the number check found
        # 32 and 4 in the answer and nowhere in the evidence.
        given = [f"Inputs: {', '.join(self.inputs)}."] if self.inputs else []
        parts = [title, *given, *self.lines]
        if self.assumptions:
            parts.append("Assumed (not given): " + "; ".join(self.assumptions) + ".")
        if self.excluded:
            parts.append("Not included: " + "; ".join(self.excluded) + ".")
        return " ".join(parts)


def parse_count(text: str, *, bare_unit: float | None = None, what: str = "value", binary_k: bool = False) -> float:
    """'70B', '7e9', '1.5 trillion', '32k' -> a number.

    A bare number is multiplied by `bare_unit` when one is given (a parameter
    count of '70' is 70 billion); otherwise it is taken as written. With
    `binary_k`, 'k' means 1024: a "32k context" is 32,768 tokens.
    """

    match = _COUNT.fullmatch(str(text or ""))
    if match is None:
        raise EstimateInputError(f"cannot read {what} '{text}'; write it like '70B', '7e9' or '32k'")
    value = float(match.group(1))
    suffix = match.group(2).lower()
    if suffix:
        if suffix not in _SUFFIX:
            raise EstimateInputError(f"unknown unit '{suffix}' in {what} '{text}'; use K, M, B or T")
        if binary_k and suffix == "k":
            return value * 1024
        return value * _SUFFIX[suffix]
    return value * bare_unit if bare_unit and value < 1e5 else value


def _given(**values: str) -> list[str]:
    """The values the caller supplied, as supplied, in a fixed order."""

    return [f"{name} {str(value).strip()}" for name, value in values.items() if str(value or "").strip()]


def _gib(value_bytes: float) -> str:
    return f"{value_bytes / GIB:,.1f} GiB"


def _count_text(value: float) -> str:
    for size, name in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if value >= size:
            return f"{value / size:g}{name}"
    return f"{value:g}"


# --- memory ------------------------------------------------------------------------------------


def memory_estimate(
    params: str,
    precision: str = "",
    mode: str = "",
    context_len: str = "",
    batch: str = "",
    layers: str = "",
    kv_heads: str = "",
    head_dim: str = "",
) -> Estimate:
    count = parse_count(params, bare_unit=1e9, what="parameter count")
    if count <= 0:
        raise EstimateInputError("the parameter count must be positive")
    estimate = Estimate(
        inputs=_given(
            params=params,
            precision=precision,
            mode=mode,
            context=context_len,
            batch=batch,
            layers=layers,
            kv_heads=kv_heads,
            head_dim=head_dim,
        )
    )
    mode_key = (mode or "").strip().lower() or "inference"
    if not mode or not mode.strip():
        estimate.assumptions.append("inference")
    if mode_key not in ("inference", "training", "lora"):
        raise EstimateInputError("mode must be inference, training or lora")
    precision_key = (precision or "").strip().lower().replace("-", "").replace(" ", "")
    if not precision_key:
        precision_key = "fp16"
        if mode_key != "training":  # the 16 bytes/param of mixed-precision Adam do not depend on it
            estimate.assumptions.append("FP16 weights")
    if precision_key not in PRECISION_BYTES:
        raise EstimateInputError(f"unknown precision '{precision}'; use one of fp32, bf16, fp16, fp8, int8, int4")

    if mode_key == "training":
        total = count * TRAINING_BYTES_PER_PARAM
        estimate.lines.append(
            f"Full training with mixed-precision Adam = params x 16 bytes (2 weights + 2 gradients + 4 FP32 master "
            f"+ 8 Adam m and v) = {_count_text(count)} x 16 = {_gib(total)}."
        )
        estimate.excluded += ["activations (depend on batch, sequence length and checkpointing)", "framework overhead"]
        return estimate

    weight_bytes = PRECISION_BYTES[precision_key]
    weights = count * weight_bytes
    estimate.lines.append(
        f"Weights = params x bytes per parameter = {_count_text(count)} x {weight_bytes:g} ({precision_key}) "
        f"= {_gib(weights)}."
    )
    total = weights
    if mode_key == "lora":
        estimate.excluded.append("LoRA adapter weights and their optimizer state (depend on rank and target modules)")
        estimate.excluded.append("activations")
    else:
        total += _kv_cache(estimate, context_len, batch, layers, kv_heads, head_dim, precision_key)
    estimate.lines.append(f"Total counted: {_gib(total)}.")
    estimate.excluded += ["framework overhead and memory fragmentation"]
    return estimate


def _kv_cache(
    estimate: Estimate, context_len: str, batch: str, layers: str, kv_heads: str, head_dim: str, precision: str
) -> float:
    if not context_len:
        estimate.excluded.append("KV cache (no context length given)")
        return 0.0
    tokens = parse_count(context_len, what="context length", binary_k=True)
    missing = [
        name for name, value in (("layers", layers), ("kv_heads", kv_heads), ("head_dim", head_dim)) if not value
    ]
    if missing:
        estimate.excluded.append(
            f"KV cache for {tokens:,.0f} tokens: needs {', '.join(missing)}, which differ by architecture and "
            "are not assumed; KV cache = 2 x layers x kv_heads x head_dim x context x batch x bytes"
        )
        return 0.0
    batch_size = parse_count(batch, what="batch size") if batch else 1.0
    if not batch:
        estimate.assumptions.append("batch 1")
    kv_bytes = 4.0 if precision in ("fp32", "float32", "tf32") else 2.0
    if precision not in ("fp32", "float32", "tf32", "fp16", "float16", "half", "bf16", "bfloat16"):
        estimate.assumptions.append("KV cache kept in FP16 (2 bytes) whatever the weight precision")
    layer_count = parse_count(layers, what="layers")
    heads = parse_count(kv_heads, what="kv_heads")
    dim = parse_count(head_dim, what="head_dim")
    cache = 2.0 * layer_count * heads * dim * tokens * batch_size * kv_bytes
    estimate.lines.append(
        f"KV cache = 2 x layers x kv_heads x head_dim x context x batch x bytes = 2 x {layer_count:g} x {heads:g} x "
        f"{dim:g} x {tokens:g} x {batch_size:g} x {kv_bytes:g} = {_gib(cache)}."
    )
    return cache


# --- compute -------------------------------------------------------------------------------------


def compute_estimate(params: str, tokens: str, mode: str = "", gpu_tflops: str = "", gpu_count: str = "") -> Estimate:
    count = parse_count(params, bare_unit=1e9, what="parameter count")
    token_count = parse_count(tokens, what="token count")
    if count <= 0 or token_count <= 0:
        raise EstimateInputError("the parameter and token counts must be positive")
    estimate = Estimate(inputs=_given(params=params, tokens=tokens, mode=mode, gpu_tflops=gpu_tflops, gpus=gpu_count))
    mode_key = (mode or "").strip().lower() or "training"
    if not mode or not mode.strip():
        estimate.assumptions.append("training")
    if mode_key not in ("training", "inference"):
        raise EstimateInputError("mode must be training or inference")
    factor = 6.0 if mode_key == "training" else 2.0
    flops = factor * count * token_count
    label = "Training FLOPs = 6 x N x D" if mode_key == "training" else "Inference FLOPs = 2 x N x tokens"
    estimate.lines.append(f"{label} = {factor:g} x {_count_text(count)} x {_count_text(token_count)} = {flops:.3e}.")
    if mode_key == "training":
        optimal = CHINCHILLA_TOKENS_PER_PARAM * count
        estimate.lines.append(
            f"Chinchilla-optimal data for this size is about 20 tokens per parameter = {_count_text(optimal)} tokens; "
            f"this run uses {token_count / optimal:.2f}x that."
        )
    if gpu_tflops:
        peak = parse_count(gpu_tflops, what="GPU TFLOPS") * 1e12
        gpus = parse_count(gpu_count, what="GPU count") if gpu_count else 1.0
        if not gpu_count:
            estimate.assumptions.append("1 GPU")
        estimate.assumptions.append(f"{DEFAULT_MFU:.0%} model FLOPs utilisation")
        seconds = flops / (peak * gpus * DEFAULT_MFU)
        estimate.lines.append(
            f"Time = FLOPs / (peak x GPUs x utilisation) = {flops:.3e} / ({peak:.3e} x {gpus:g} x {DEFAULT_MFU:g}) "
            f"= {seconds / 3600:,.1f} hours ({seconds / 86400:,.1f} days)."
        )
    estimate.excluded.append("attention FLOPs beyond the 2N-per-token approximation (grow with context length)")
    return estimate


# --- tools ---------------------------------------------------------------------------------------

_PARAMS = ToolParameter(
    name="params",
    description="Parameter count as the user gave it: '70B', '7e9', '13 billion', or '70' (read as billions).",
    required=True,
    max_length=40,
)

MEMORY_ESTIMATE_TOOL_DEFINITION = ToolDefinition(
    tool_id="querymind_ai_memory_estimate",
    operation="read",
    risk="read_only",
    category="artificial_intelligence",
    description=(
        "GPU memory for a model: weights, KV cache (only when layers, kv_heads and head_dim are all given), or "
        "full training with mixed-precision Adam. Pass ONLY values the user stated; leave the rest empty -- the "
        "result states every assumption and what it does not include."
    ),
    parameters=(
        _PARAMS,
        ToolParameter(
            name="precision", description="fp32, bf16, fp16, fp8, int8 or int4.", required=False, max_length=16
        ),
        ToolParameter(name="mode", description="inference, training or lora.", required=False, max_length=16),
        ToolParameter(
            name="context_len", description="Context length in tokens, e.g. '32k'.", required=False, max_length=16
        ),
        ToolParameter(name="batch", description="Batch size.", required=False, max_length=16),
        ToolParameter(name="layers", description="Number of transformer layers.", required=False, max_length=16),
        ToolParameter(name="kv_heads", description="Number of key/value heads.", required=False, max_length=16),
        ToolParameter(name="head_dim", description="Dimension of each attention head.", required=False, max_length=16),
    ),
)

COMPUTE_ESTIMATE_TOOL_DEFINITION = ToolDefinition(
    tool_id="querymind_ai_compute_estimate",
    operation="read",
    risk="read_only",
    category="artificial_intelligence",
    description=(
        "Compute for a model: training FLOPs (6ND, with the Chinchilla 20-tokens-per-parameter reference) or "
        "inference FLOPs (2N per token), and time on GPUs when their peak TFLOPS is given. Pass ONLY values the "
        "user stated; the result states every assumption."
    ),
    parameters=(
        _PARAMS,
        ToolParameter(
            name="tokens", description="Tokens trained on or generated: '1T', '2e12'.", required=True, max_length=40
        ),
        ToolParameter(name="mode", description="training or inference.", required=False, max_length=16),
        ToolParameter(
            name="gpu_tflops", description="Peak dense TFLOPS of one GPU, e.g. '989'.", required=False, max_length=16
        ),
        ToolParameter(name="gpu_count", description="Number of GPUs.", required=False, max_length=16),
    ),
)


def _arg(call: ToolCall, name: str) -> str:
    return extract_call_argument(call, name)


async def execute_memory_estimate(call: ToolCall, actor: RequestActor) -> ToolResult:
    del actor
    await asyncio.sleep(0)
    try:
        estimate = memory_estimate(*(_arg(call, name) for name in (
            "params", "precision", "mode", "context_len", "batch", "layers", "kv_heads", "head_dim"
        )))  # fmt: skip
    except EstimateInputError as error:
        return ToolResult(tool_id=call.tool_id, status="failed", summary=f"Cannot estimate memory: {error}.")
    title = f"Memory estimate for a {_count_text(parse_count(_arg(call, 'params'), bare_unit=1e9))}-parameter model:"
    return ToolResult(tool_id=call.tool_id, status="succeeded", summary=estimate.summary(title))


async def execute_compute_estimate(call: ToolCall, actor: RequestActor) -> ToolResult:
    del actor
    await asyncio.sleep(0)
    try:
        estimate = compute_estimate(
            *(_arg(call, name) for name in ("params", "tokens", "mode", "gpu_tflops", "gpu_count"))
        )
    except EstimateInputError as error:
        return ToolResult(tool_id=call.tool_id, status="failed", summary=f"Cannot estimate compute: {error}.")
    title = f"Compute estimate for a {_count_text(parse_count(_arg(call, 'params'), bare_unit=1e9))}-parameter model:"
    return ToolResult(tool_id=call.tool_id, status="succeeded", summary=estimate.summary(title))
