"""The AI math tool's description is the only thing the model reads about its helpers.

It named none of their arguments, and `param_gb` takes BITS per parameter while
`kv_cache_mb` takes BYTES per element. Asked for 70B weights at "2 bytes per
parameter", a real model wrote `param_gb(70e9, 2)` and the tool reported 16.3
GiB for roughly 130 -- under `succeeded`, which the answer then repeats. The
description now states every signature, and these tests hold it to the code.
"""

from __future__ import annotations

import inspect
import re

import pytest

from app.tools.ai.code_sandbox import _SAFE_MATH_FUNCS, AI_MATH_TOOL_DEFINITION, evaluate_safe_math

_HELPERS = ("param_gb", "kv_cache_mb", "flops_train", "flops_infer")
_DESCRIPTION = AI_MATH_TOOL_DEFINITION.description


def _described_signature(name: str) -> list[str]:
    match = re.search(rf"{name}\(([^)]*)\)", _DESCRIPTION)
    assert match, f"the description does not give {name}'s signature"
    return [part.split("=")[0].strip() for part in match.group(1).split(",")]


@pytest.mark.parametrize("name", _HELPERS)
def test_every_helper_signature_is_described_as_it_is(name: str) -> None:
    actual = list(inspect.signature(_SAFE_MATH_FUNCS[name]).parameters)
    described = _described_signature(name)
    assert len(described) == len(actual), f"{name}: described {described}, takes {actual}"


@pytest.mark.parametrize(("name", "unit"), [("param_gb", "BITS"), ("kv_cache_mb", "BYTES")])
def test_the_opposite_units_are_named(name: str, unit: str) -> None:
    """The two memory helpers disagree on units; the description must say which is which."""

    sentence = _DESCRIPTION[_DESCRIPTION.index(f"{name}(") :].split(". ")[0]
    assert unit in sentence


def test_the_described_reading_gives_the_right_number() -> None:
    """70B at FP16, written the way the description now teaches, is ~130 GiB."""

    assert evaluate_safe_math("param_gb(70e9, 16)") == pytest.approx(130.385, rel=1e-3)
    # The misreading the old description invited, kept so the gap stays visible.
    assert evaluate_safe_math("param_gb(70e9, 2)") == pytest.approx(16.298, rel=1e-3)
