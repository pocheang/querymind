"""The AI specialist's typed estimates: hand-checked numbers, every assumption named, nothing invented.

The free-form calculator left the formula to the model, and a model once passed
"2 bytes per parameter" to a helper whose argument is bits (16.3 GiB for ~130).
These tools take what the user stated and do the arithmetic; the values below
were computed by hand, not copied from the implementation.
"""

from __future__ import annotations

import asyncio

import pytest

from app.mcp.contracts import ToolArgument, ToolCall
from app.orchestration.request import RequestActor
from app.tools.ai.estimates import (
    COMPUTE_ESTIMATE_TOOL_DEFINITION,
    MEMORY_ESTIMATE_TOOL_DEFINITION,
    EstimateInputError,
    compute_estimate,
    execute_compute_estimate,
    execute_memory_estimate,
    memory_estimate,
    parse_count,
)

ACTOR = RequestActor(user_id="u", tenant_id="t", role="viewer")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("70B", 70e9), ("7e9", 7e9), ("13 billion", 13e9), ("1.5T", 1.5e12), ("500M", 5e8), ("70", 70e9)],
)
def test_a_parameter_count_is_read_as_people_write_it(text, expected):
    assert parse_count(text, bare_unit=1e9) == pytest.approx(expected)


def test_a_context_length_in_k_is_binary():
    """A "32k context" is 32,768 tokens."""

    assert parse_count("32k", binary_k=True) == 32768
    assert parse_count("32k") == 32000


@pytest.mark.parametrize("text", ["seventy", "70 gigaparams", ""])
def test_an_unreadable_quantity_is_refused_with_how_to_write_it(text):
    with pytest.raises(EstimateInputError, match="70B"):
        parse_count(text, what="parameter count")


# --- memory ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("precision", "gib"),
    [("fp32", "260.8"), ("bf16", "130.4"), ("fp16", "130.4"), ("int8", "65.2"), ("int4", "32.6")],
)
def test_weights_at_each_precision(precision, gib):
    # 70e9 x bytes / 1024^3: fp16 = 140e9 / 1073741824 = 130.385...
    summary = memory_estimate("70B", precision).summary("")

    assert f"= {gib} GiB" in summary


def test_the_kv_cache_is_computed_only_from_a_given_architecture():
    # 2 x 80 x 8 x 128 x 32768 x 4 x 2 bytes = 42,949,672,960 = 40.0 GiB
    summary = memory_estimate("70B", "fp16", "inference", "32k", "4", "80", "8", "128").summary("")

    assert "= 40.0 GiB" in summary
    assert "Total counted: 170.4 GiB" in summary


def test_a_missing_architecture_is_named_not_invented():
    """Layers, KV heads and head size differ by model; a default for them is a confident wrong number."""

    summary = memory_estimate("70B", "fp16", "", "32k", "4").summary("")

    assert "KV cache for 32,768 tokens: needs layers, kv_heads, head_dim" in summary
    assert "not assumed" in summary
    assert "Total counted: 130.4 GiB" in summary


def test_what_was_not_given_is_listed_as_assumed():
    summary = memory_estimate("70B", "", "", "4k", "", "80", "8", "128").summary("")

    assert "Assumed (not given): inference; FP16 weights; batch 1." in summary


def test_training_counts_sixteen_bytes_per_parameter_and_excludes_activations():
    summary = memory_estimate("7B", "", "training").summary("")

    assert "= 104.3 GiB" in summary  # 7e9 x 16 / 1024^3
    assert "activations" in summary
    assert "FP16 weights" not in summary, "mixed-precision Adam's 16 bytes do not depend on it"


def test_lora_counts_the_base_weights_and_names_what_it_leaves_out():
    summary = memory_estimate("7B", "int4", "lora").summary("")

    assert "= 3.3 GiB" in summary
    assert "LoRA adapter weights and their optimizer state" in summary


@pytest.mark.parametrize(
    ("kwargs", "message"), [({"precision": "fp12"}, "unknown precision"), ({"mode": "serving"}, "mode must be")]
)
def test_an_unknown_option_is_refused(kwargs, message):
    with pytest.raises(EstimateInputError, match=message):
        memory_estimate("7B", **kwargs)


# --- compute ----------------------------------------------------------------------------------


def test_training_flops_are_six_n_d_with_the_chinchilla_reference():
    summary = compute_estimate("7B", "1T").summary("")

    assert "= 4.200e+22" in summary  # 6 x 7e9 x 1e12
    assert "140B tokens" in summary and "7.14x" in summary


def test_inference_flops_are_two_n_per_token():
    assert "= 1.400e+13" in compute_estimate("7B", "1000", "inference").summary("")  # 2 x 7e9 x 1e3


def test_gpu_time_states_the_utilisation_it_assumed():
    # 6.3e24 / (989e12 x 1024 x 0.4) = 1.555e7 s = 4,320.0 h
    summary = compute_estimate("70B", "15T", "training", "989", "1024").summary("")

    assert "4,320.0 hours" in summary
    assert "40% model FLOPs utilisation" in summary


# --- tools ------------------------------------------------------------------------------------


def _run(executor, tool_id, **arguments):
    call = ToolCall(tool_id=tool_id, arguments=tuple(ToolArgument(name=k, value=v) for k, v in arguments.items()))
    return asyncio.run(executor(call, ACTOR))


def test_the_memory_tool_answers_with_its_working():
    result = _run(execute_memory_estimate, "querymind_ai_memory_estimate", params="70B", precision="fp16")

    assert result.status == "succeeded"
    assert result.summary.startswith("Memory estimate for a 70B-parameter model:")
    assert "70B x 2 (fp16) = 130.4 GiB" in result.summary


def test_a_bad_input_is_a_failed_result_not_an_exception():
    result = _run(execute_compute_estimate, "querymind_ai_compute_estimate", params="seventy", tokens="1T")

    assert result.status == "failed" and "Cannot estimate compute" in result.summary


@pytest.mark.parametrize("definition", [MEMORY_ESTIMATE_TOOL_DEFINITION, COMPUTE_ESTIMATE_TOOL_DEFINITION])
def test_the_tools_are_read_only_and_ask_only_for_what_the_user_stated(definition):
    assert (definition.operation, definition.risk, definition.category) == (
        "read",
        "read_only",
        "artificial_intelligence",
    )
    assert "ONLY values the user stated" in definition.description


def test_the_summary_restates_the_inputs_it_was_given():
    """So an answer echoing "32k context, batch 4" cites something that contains 32k and 4."""

    summary = memory_estimate("70B", "fp16", "", "32k", "4").summary("")

    assert "Inputs: params 70B, precision fp16, context 32k, batch 4." in summary
    assert "Inputs:" not in memory_estimate("7B").summary("").split("Weights")[1]
