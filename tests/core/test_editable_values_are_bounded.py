"""An editable field's own bounds, and the rules that relate two of them.

`config_schema.EDITABLE` is what console access can reach, and `validate_values`
is the only thing standing between a form field and the running configuration.
It did two things too loosely.

**Fourteen editable numeric fields carried no `ge`/`le` at all**, so the only
check was the Python type. Measured on the shipped code, all of these were
accepted: `TOP_K=-5`, `RERANKER_TOP_N=-1`, `MAX_CONTEXT_CHUNKS=0`,
`WEB_MIN_SOURCE_SCORE=9.5` (a trust threshold no source can meet),
`SELF_RAG_QUALITY_THRESHOLD=42`, `RETRIEVAL_CACHE_TTL_SECONDS=-100`. The stage
ceilings beside them have carried bounds all along, so this was an omission
rather than a policy.

**And a per-field-legal save could take the whole system down.**
`TimeoutConfig.validate()` requires one pass of every stage to fit inside
`STAGE_TIMEOUT_TOTAL_MS`, and it runs from `TimeoutConfig.from_settings`, which
`get_timeout_config` calls *per request*. Seven stage ceilings are editable and
each is satisfiable while their sum is not, so raising
`STAGE_TIMEOUT_SYNTHESIS_MS` to 60s -- inside its own `le=120_000` -- was
accepted, saved, reloaded, and then raised out of the engine on every query:

    ValueError: Stage timeouts sum (123000ms) exceeds total timeout (120000ms)

That rule now lives on `Settings`, so it is a refused write and a loud startup
rather than an outage, and `validate_values` merges the edit onto the *running*
configuration instead of onto the defaults -- without which any cross-field rule
would be checked against operands nobody is running.

The bounds test discovers its fields from `EDITABLE` rather than listing them, so
a numeric field added to the allowlist later is covered the day it is added.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.config_schema import EDITABLE, current_values_by_alias, validate_values

NUMERIC = (int, float)


def _field_for(alias: str):
    for name, field in Settings.model_fields.items():
        if (field.alias or name) == alias:
            return name, field
    raise AssertionError(f"{alias} is editable but Settings has no such field")


def _bounds(field) -> tuple[bool, bool]:
    kinds = {type(item).__name__ for item in field.metadata}
    return ({"Ge", "Gt"} & kinds != set(), {"Le", "Lt"} & kinds != set())


def _editable_numeric_aliases() -> list[str]:
    found = []
    for editable in EDITABLE:
        _, field = _field_for(editable.alias)
        if field.annotation in NUMERIC:
            found.append(editable.alias)
    return found


def test_the_discovery_finds_something():
    """A guard that quietly matches nothing reports PASS just as readily."""

    assert len(_editable_numeric_aliases()) >= 14


@pytest.mark.parametrize("alias", _editable_numeric_aliases())
def test_every_editable_numeric_field_has_a_floor_and_a_ceiling(alias):
    """Parametrized per field so a failure names the one that is missing them."""

    _, field = _field_for(alias)
    has_floor, has_ceiling = _bounds(field)

    assert has_floor, f"{alias} is editable from the console with no lower bound"
    assert has_ceiling, f"{alias} is editable from the console with no upper bound"


@pytest.mark.parametrize(
    ("alias", "value"),
    [
        ("TOP_K", "-5"),
        ("TOP_K", "0"),
        ("RERANKER_TOP_N", "-1"),
        ("MAX_CONTEXT_CHUNKS", "0"),
        ("VECTOR_TOP_K", "0"),
        ("BM25_TOP_K", "-2"),
        ("RETRIEVAL_CACHE_TTL_SECONDS", "-100"),
        ("NLI_MAX_SENTENCES", "-3"),
        ("CASCADE_NLI_TIMEOUT_MS", "-1"),
        ("CASCADE_DEEP_TIMEOUT_MS", "0"),
        ("WEB_SEARCH_TIMEOUT_SECONDS", "0"),
        ("WEB_SEARCH_MAX_RETRIES", "-1"),
        ("WEB_MIN_SOURCE_SCORE", "9.5"),
        ("SELF_RAG_QUALITY_THRESHOLD", "42"),
        ("SELF_RAG_RELEVANCE_THRESHOLD", "-0.5"),
    ],
)
def test_a_value_outside_the_bounds_is_refused(alias, value):
    """Every one of these was accepted before."""

    with pytest.raises(ValueError, match=alias):
        validate_values({alias: value})


def test_an_ordinary_change_is_still_accepted():
    """Bounds that reject everything would pass every test above."""

    assert validate_values({"TOP_K": "8", "WEB_MIN_SOURCE_SCORE": "0.4"}) == {
        "TOP_K": "8",
        "WEB_MIN_SOURCE_SCORE": "0.4",
    }


# --- the rules that relate two fields ------------------------------------


def test_stage_ceilings_that_do_not_fit_the_total_are_refused():
    """Inside its own le=120_000, and fatal to every request that followed."""

    with pytest.raises(ValueError, match="does not fit inside STAGE_TIMEOUT_TOTAL_MS"):
        validate_values({"STAGE_TIMEOUT_SYNTHESIS_MS": "60000"})


def test_a_per_source_bound_above_its_stage_is_refused():
    """A bound that can never fire is the state this repository already fixed once."""

    with pytest.raises(ValueError, match="can never fire"):
        validate_values({"KNOWLEDGE_SOURCE_TIMEOUT_MS": "60000"})


def test_raising_the_total_alongside_the_stage_is_accepted():
    """The rule is about the pair, not about either value."""

    assert validate_values({"STAGE_TIMEOUT_SYNTHESIS_MS": "60000", "STAGE_TIMEOUT_TOTAL_MS": "200000"})


def test_settings_refuses_the_same_shape_at_construction():
    """So a rendered runtime file or a centre document fails loudly at startup.

    Without this the process starts, answers `/health`, and raises on the first
    real question -- which reads as a retrieval fault rather than a configuration
    one.
    """

    with pytest.raises(ValidationError, match="does not fit inside"):
        Settings(STAGE_TIMEOUT_SYNTHESIS_MS="60000")


# --- validated against what is running, not against the defaults ---------


def test_the_change_is_checked_against_the_running_configuration():
    """The blind spot: `Settings(**values)` let every untouched field fall to its default.

    Here the live total is 20s. The edit is legal against the *default* 120s total
    and illegal against the one this deployment is running, and the second answer
    is the only one that means anything.
    """

    live = Settings(
        STAGE_TIMEOUT_TOTAL_MS="20000",
        STAGE_TIMEOUT_ROUTE_MS="2000",
        STAGE_TIMEOUT_PLAN_MS="1000",
        STAGE_TIMEOUT_RETRIEVAL_MS="6000",
        STAGE_TIMEOUT_TOOL_MS="3000",
        STAGE_TIMEOUT_SYNTHESIS_MS="5000",
        STAGE_TIMEOUT_FINALIZATION_MS="2000",
        STAGE_TIMEOUT_OVERHEAD_MS="1000",
        KNOWLEDGE_SOURCE_TIMEOUT_MS="5000",
    )

    # Legal against the defaults ...
    assert validate_values({"STAGE_TIMEOUT_RETRIEVAL_MS": "15000"})
    # ... and not against what this deployment is running.
    with pytest.raises(ValueError, match="does not fit inside"):
        validate_values({"STAGE_TIMEOUT_RETRIEVAL_MS": "15000"}, current=live)


def test_the_merged_candidate_is_keyed_by_alias():
    """`{"top_k": 4}` is dropped in silence -- `extra="ignore"` and validation by alias.

    So a merge keyed by field name would hand `Settings` nothing at all, every
    untouched field would fall back to its default, and the fix would look exactly
    like the defect it replaced while passing every test that only edits one field.
    """

    by_alias = current_values_by_alias(Settings(TOP_K="9"))

    assert by_alias["TOP_K"] == 9
    assert "top_k" not in by_alias
    assert Settings(**by_alias).top_k == 9
