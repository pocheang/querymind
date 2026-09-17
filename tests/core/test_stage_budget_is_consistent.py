"""Two statements of one rule, checked against each other rather than described.

"One pass of every stage fits inside the total" is enforced in two places now:
`TimeoutConfig.validate()`, which has always had it, and a `model_validator` on
`Settings`, which is what turns a fatal per-request failure into a refused write.

The duplication is deliberate and constrained: `app/core` must not import
`app/orchestration`, so the arithmetic is written twice. This repository's rule
for a thing written twice is to compare the two rather than assert that somebody
remembered -- the same treatment `test_table_separator_regex.py` gives a pattern
copied into four modules, and `test_admin_audit_filtering.py` gives the two
identical timestamp parsers.

Drift here is silent in the expensive direction: if `Settings` grew more
permissive than `TimeoutConfig`, the console would accept a configuration that
raises on every query -- exactly the defect the validator was added to close.
"""

from __future__ import annotations

import random

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.orchestration.timeout_control import TimeoutConfig

STAGE_ALIASES = (
    "STAGE_TIMEOUT_ROUTE_MS",
    "STAGE_TIMEOUT_PLAN_MS",
    "STAGE_TIMEOUT_RETRIEVAL_MS",
    "STAGE_TIMEOUT_TOOL_MS",
    "STAGE_TIMEOUT_SYNTHESIS_MS",
    "STAGE_TIMEOUT_FINALIZATION_MS",
    "STAGE_TIMEOUT_OVERHEAD_MS",
)


def _cases(count: int = 200) -> list[dict[str, str]]:
    """Budgets spread across the per-field bounds, so both verdicts occur."""

    rng = random.Random(20260917)
    cases: list[dict[str, str]] = []
    for _ in range(count):
        case = {
            "STAGE_TIMEOUT_TOTAL_MS": str(rng.randrange(5_000, 600_001, 1_000)),
            "STAGE_TIMEOUT_ROUTE_MS": str(rng.randrange(500, 120_001, 500)),
            "STAGE_TIMEOUT_PLAN_MS": str(rng.randrange(500, 120_001, 500)),
            "STAGE_TIMEOUT_RETRIEVAL_MS": str(rng.randrange(500, 120_001, 500)),
            "STAGE_TIMEOUT_TOOL_MS": str(rng.randrange(500, 120_001, 500)),
            "STAGE_TIMEOUT_SYNTHESIS_MS": str(rng.randrange(500, 120_001, 500)),
            "STAGE_TIMEOUT_FINALIZATION_MS": str(rng.randrange(500, 120_001, 500)),
            "STAGE_TIMEOUT_OVERHEAD_MS": str(rng.randrange(0, 60_001, 500)),
        }
        # The per-source bound is a separate rule; hold it out of the way so this
        # file measures the budget rule alone.
        case["KNOWLEDGE_SOURCE_TIMEOUT_MS"] = str(min(int(case["STAGE_TIMEOUT_RETRIEVAL_MS"]), 10_000))
        cases.append(case)
    return cases


CASES = _cases()


def _settings_accepts(case: dict[str, str]) -> bool:
    try:
        Settings(**case)
    except ValidationError:
        return False
    return True


def _dataclass_accepts(case: dict[str, str]) -> bool:
    config = TimeoutConfig(
        total_timeout_ms=int(case["STAGE_TIMEOUT_TOTAL_MS"]),
        route_timeout_ms=int(case["STAGE_TIMEOUT_ROUTE_MS"]),
        plan_timeout_ms=int(case["STAGE_TIMEOUT_PLAN_MS"]),
        retrieval_timeout_ms=int(case["STAGE_TIMEOUT_RETRIEVAL_MS"]),
        tool_timeout_ms=int(case["STAGE_TIMEOUT_TOOL_MS"]),
        synthesis_timeout_ms=int(case["STAGE_TIMEOUT_SYNTHESIS_MS"]),
        finalization_timeout_ms=int(case["STAGE_TIMEOUT_FINALIZATION_MS"]),
        overhead_buffer_ms=int(case["STAGE_TIMEOUT_OVERHEAD_MS"]),
    )
    try:
        config.validate()
    except ValueError:
        return False
    return True


def test_the_generated_budgets_cover_both_verdicts():
    """Otherwise agreement is vacuous: two functions that always say yes agree."""

    verdicts = {_dataclass_accepts(case) for case in CASES}

    assert verdicts == {True, False}


def test_the_two_statements_of_the_rule_agree():
    disagreements = [case for case in CASES if _settings_accepts(case) != _dataclass_accepts(case)]

    assert disagreements == [], f"{len(disagreements)} budgets are judged differently, e.g. {disagreements[:1]}"


def test_a_settings_that_validated_can_always_build_its_timeout_config():
    """The property that matters on the request path.

    `get_timeout_config` runs per request and calls `from_settings`, which calls
    `validate()`. If `Settings` can hold a budget the dataclass refuses, that
    refusal is an exception in the middle of answering a question.
    """

    for case in CASES:
        try:
            settings = Settings(**case)
        except ValidationError:
            continue
        TimeoutConfig.from_settings(settings)


def test_the_agreement_check_can_fail():
    """Prove the comparison would notice drift, rather than trusting that it would.

    A budget the dataclass refuses and a hand-loosened `Settings` accepts is
    exactly the shape of the regression, so it is constructed here instead of
    being left to a future reader to imagine.
    """

    over_budget = {alias: "120000" for alias in STAGE_ALIASES}
    over_budget["STAGE_TIMEOUT_TOTAL_MS"] = "120000"
    over_budget["KNOWLEDGE_SOURCE_TIMEOUT_MS"] = "10000"

    assert _dataclass_accepts(over_budget) is False
    with pytest.raises(ValidationError):
        Settings(**over_budget)
