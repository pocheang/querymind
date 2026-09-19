"""Unit tests for AST mathematical sandbox and AI scaling evaluation tool."""

import pytest

from app.mcp.contracts import ToolArgument, ToolCall
from app.orchestration.request import RequestActor
from app.tools.ai.code_sandbox import (
    AI_MATH_TOOL_DEFINITION,
    evaluate_safe_math,
    execute_ai_math_eval,
)


@pytest.fixture
def actor() -> RequestActor:
    return RequestActor(user_id="ai_engineer", tenant_id="tenant_beta", role="researcher")


def test_evaluate_basic_arithmetic() -> None:
    assert evaluate_safe_math("2 + 3 * 4") == 14
    assert evaluate_safe_math("(100 - 20) / 4") == 20.0
    assert evaluate_safe_math("2 ** 10") == 1024


def test_evaluate_scaling_laws() -> None:
    # 6 * P * D: 7B params * 2T tokens
    flops = evaluate_safe_math("6 * 7e9 * 2e12")
    assert flops == 8.4e22

    # Helper function flops_train
    assert evaluate_safe_math("flops_train(7e9, 2e12)") == 8.4e22
    assert evaluate_safe_math("flops_infer(7e9, 1000)") == 1.4e13


def test_evaluate_special_math_functions() -> None:
    assert evaluate_safe_math("log2(4096)") == 12.0
    assert evaluate_safe_math("sqrt(65536)") == 256.0
    assert evaluate_safe_math("abs(-42)") == 42
    assert evaluate_safe_math("sigmoid(0)") == 0.5
    assert evaluate_safe_math("gelu(0)") == 0.0


def test_evaluate_memory_helpers() -> None:
    # 7B model in FP16 (16 bits) in GB
    gb = evaluate_safe_math("param_gb(7e9, 16)")
    assert 13.0 < gb < 14.0

    # KV Cache in MB: 32 layers, 8 kv heads, 128 head_dim, 4096 seq_len, batch 1, fp16 (2 bytes)
    kv_mb = evaluate_safe_math("kv_cache_mb(32, 8, 128, 4096, 1, 2)")
    assert kv_mb == 512.0


def test_safety_rejections() -> None:
    with pytest.raises(ValueError):
        evaluate_safe_math("__import__('os').system('ls')")

    with pytest.raises(ValueError):
        evaluate_safe_math("open('/etc/passwd')")

    with pytest.raises(ValueError):
        evaluate_safe_math("eval('1 + 1')")

    with pytest.raises(ValueError):
        evaluate_safe_math("exec('print(1)')")

    with pytest.raises(ValueError):
        evaluate_safe_math("lambda x: x")

    with pytest.raises(ValueError):
        evaluate_safe_math("10 ** 1000")  # Exceeds power bounds


@pytest.mark.asyncio
async def test_execute_ai_math_eval_success(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=AI_MATH_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="expression", value="log2(1024 * 1024)"),),
    )
    result = await execute_ai_math_eval(call, actor)
    assert result.status == "succeeded"
    assert "20.0" in result.summary


@pytest.mark.asyncio
async def test_execute_ai_math_eval_alias_arg(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=AI_MATH_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="query", value="flops_train(14e9, 3e12)"),),
    )
    result = await execute_ai_math_eval(call, actor)
    assert result.status == "succeeded"
    assert "2.520000e+23" in result.summary


@pytest.mark.asyncio
async def test_execute_ai_math_eval_error_handled(actor: RequestActor) -> None:
    call = ToolCall(
        tool_id=AI_MATH_TOOL_DEFINITION.tool_id,
        arguments=(ToolArgument(name="expression", value="bad_func()"),),
    )
    result = await execute_ai_math_eval(call, actor)
    assert result.status == "failed"
    assert "Evaluation error" in result.summary
