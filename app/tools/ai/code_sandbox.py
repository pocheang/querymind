"""Safe AI Algorithm, FLOPs & Parameter Math Evaluation Tool.

Uses an isolated Abstract Syntax Tree (AST) evaluator without invoking eval() or exec().
Enables rigorous estimation of:
- Transformer FLOPs scaling laws (e.g. 6 * P * D)
- KV cache memory footprint (2 * b * s * l * h * d)
- Learning rate decay and schedule computations
"""

from __future__ import annotations

import ast
import logging
import math
import operator
from typing import Any

from app.domain.contracts import ToolResult
from app.mcp.contracts import ToolArgument, ToolCall, ToolDefinition, ToolParameter
from app.orchestration.request import RequestActor

logger = logging.getLogger(__name__)

_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x)) if x >= -50 else 0.0


def _gelu(x: float) -> float:
    if abs(x) > 100:
        return x if x > 0 else 0.0
    return 0.5 * x * (1.0 + math.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * math.pow(x, 3))))


def _param_gb(params: float, bits: float = 16.0) -> float:
    """Calculate raw model weights size in gigabytes (GB)."""
    return (params * bits) / (8.0 * (1024.0**3))


def _kv_cache_mb(
    layers: float,
    kv_heads: float,
    head_dim: float,
    seq_len: float,
    batch_size: float = 1.0,
    bytes_per_elem: float = 2.0,
) -> float:
    """Calculate Transformer KV cache memory in Megabytes (MB).

    Formula: 2 (K and V) * layers * kv_heads * head_dim * seq_len * batch_size * bytes_per_elem / (1024^2)
    """
    total_bytes = 2.0 * layers * kv_heads * head_dim * seq_len * batch_size * bytes_per_elem
    return total_bytes / (1024.0**2)


def _flops_train(params: float, tokens: float) -> float:
    """Compute standard Chinchilla training FLOPs: 6 * P * D."""
    return 6.0 * params * tokens


def _flops_infer(params: float, tokens: float) -> float:
    """Compute standard inference FLOPs: 2 * P * D."""
    return 2.0 * params * tokens


_SAFE_MATH_FUNCS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "ceil": math.ceil,
    "floor": math.floor,
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
    "tanh": math.tanh,
    "sigmoid": _sigmoid,
    "gelu": _gelu,
    "param_gb": _param_gb,
    "kv_cache_mb": _kv_cache_mb,
    "flops_train": _flops_train,
    "flops_infer": _flops_infer,
}

_SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int | float | bool):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable or constant: {node.id}")
    if isinstance(node, ast.UnaryOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        operand = _safe_eval_node(node.operand)
        return op_func(operand)
    if isinstance(node, ast.BinOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op)}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e15):
            raise ValueError("Power operation values exceed safety bounds")
        return op_func(left, right)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _SAFE_MATH_FUNCS:
            func = _SAFE_MATH_FUNCS[node.func.id]
            args = [_safe_eval_node(arg) for arg in node.args]
            return func(*args)
        raise ValueError(f"Unsupported function call: {ast.dump(node)}")

    raise ValueError(f"Unsupported syntax expression: {type(node).__name__}")


def evaluate_safe_math(expression: str) -> float | int:
    """Safely evaluate an arithmetic or mathematical formula without eval()."""
    clean_expr = str(expression or "").strip()
    if not clean_expr:
        raise ValueError("Expression is empty")
    if len(clean_expr) > 500:
        raise ValueError("Expression exceeds maximum allowed length of 500 characters")

    parsed = ast.parse(clean_expr, mode="eval")
    result = _safe_eval_node(parsed)
    if not isinstance(result, int | float):
        raise ValueError(f"Result is not numerical: {result}")
    return result


AI_MATH_TOOL_DEFINITION = ToolDefinition(
    tool_id="querymind_ai_math_eval",
    operation="read",
    risk="read_only",
    category="artificial_intelligence",
    description="Safely compute mathematical formulas, FLOPs estimates (e.g. 6 * 7e9 * 1e12), memory footprints, or algorithm complexities via AST sandboxed execution.",
    parameters=(
        ToolParameter(
            name="expression",
            description="Mathematical expression to evaluate (e.g. '6 * 7e9 * 2e12' or 'log2(4096)').",
            required=True,
            max_length=500,
        ),
    ),
)


def _get_call_arg(call: ToolCall, *names: str) -> str:
    """Extract argument matching any candidate parameter name."""
    if hasattr(call, "arguments"):
        if isinstance(call.arguments, tuple | list):
            for name in names:
                for arg in call.arguments:
                    if isinstance(arg, ToolArgument) and arg.name == name:
                        return str(arg.value)
                    if hasattr(arg, "name") and arg.name == name:
                        return str(getattr(arg, "value", ""))
        elif isinstance(call.arguments, dict):
            for name in names:
                val = call.arguments.get(name)
                if val is not None and str(val).strip():
                    return str(val)
    return ""


async def execute_ai_math_eval(call: ToolCall, actor: RequestActor) -> ToolResult:
    """Execute mathematical computation safely."""
    del actor
    expr = _get_call_arg(call, "expression", "code", "math", "query").strip()
    try:
        val = evaluate_safe_math(expr)
        formatted = f"{val:.6e}" if isinstance(val, float) and (abs(val) >= 1e6 or 0 < abs(val) < 1e-4) else str(val)
        return ToolResult(
            tool_id=call.tool_id,
            status="succeeded",
            summary=f"Evaluated '{expr}' = {formatted}",
        )
    except Exception as exc:
        return ToolResult(
            tool_id=call.tool_id,
            status="failed",
            summary=f"Evaluation error for expression '{expr}': {exc}",
        )


__all__ = [
    "AI_MATH_TOOL_DEFINITION",
    "evaluate_safe_math",
    "execute_ai_math_eval",
]
