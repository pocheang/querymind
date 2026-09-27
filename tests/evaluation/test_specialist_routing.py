"""The offline routing rules, measured question by question against a labelled set.

This is the first measurement behind "Router accuracy" in the quality table,
which had none. Measured 2026-09-27 over 59 questions: the keyword rules pick
the right specialist for 51 -- 51 of the 57 whose class has a specialist today.
Every miss is in `KNOWN_MISROUTES` with the exact wrong answer.

Pinned per question, not as an aggregate, so a failure names the question, and
exactly, so an improvement fails too -- the entry should then be deleted. The
labels are what a correct router should answer; see the file's `_readme`.
"""

from __future__ import annotations

import re
from collections import Counter

import pytest

from app.agents.catalog import BUILTIN_AGENT_CLASSES
from app.agents.registry import get_domain_agent_registry
from app.agents.shared.config import VALID_SKILLS
from app.evaluation.specialist_routing import KNOWN_MISROUTES, evaluate, load_cases

CASES = load_cases()
REPORT = evaluate(CASES)
OUTCOMES = {outcome.case.id: outcome for outcome in REPORT.outcomes}

# Classes a label may name before a specialist answers them, each with the plan
# PR that adds it. Anything else must already be a known class.
PENDING_CLASSES = {"policy": "plan PR 10 (compliance)"}

_CJK = re.compile(r"[㐀-鿿]")


@pytest.mark.parametrize("case_id", sorted(OUTCOMES))
def test_each_question_routes_as_labelled_or_as_recorded(case_id: str) -> None:
    outcome = OUTCOMES[case_id]
    got = (outcome.agent_class, outcome.skill)
    expected = (outcome.case.agent_class, outcome.case.skill)
    if case_id in KNOWN_MISROUTES:
        recorded, why = KNOWN_MISROUTES[case_id]
        assert got != expected, f"{case_id} now routes as labelled: delete its KNOWN_MISROUTES entry ({why})"
        assert got == recorded, f"{case_id} misroutes differently than recorded: got {got}, recorded {recorded}"
    else:
        assert got == expected, f"{case_id} {outcome.case.question!r}: got {got}, labelled {expected}"


def test_every_recorded_misroute_names_a_question_in_the_set() -> None:
    assert set(KNOWN_MISROUTES) <= set(OUTCOMES)


def test_a_pending_class_is_only_ever_a_recorded_misroute() -> None:
    """A label naming a class with no specialist cannot pass; it has to be on the record."""

    pending = {case.id for case in CASES if case.agent_class in PENDING_CLASSES}
    assert pending
    assert pending <= set(KNOWN_MISROUTES)


def test_every_label_names_a_class_and_skill_that_exist() -> None:
    """A mistyped label scores as a miss forever and reads as a broken router."""

    registry = get_domain_agent_registry()
    for case in CASES:
        assert case.agent_class in BUILTIN_AGENT_CLASSES | set(PENDING_CLASSES), case.id
        specialist = registry.get_agent(case.agent_class)
        own_skills = set(specialist.supported_skills) if specialist else set()
        assert case.skill in own_skills | VALID_SKILLS, f"{case.id}: {case.skill} is not a skill anything offers"


def test_ids_are_unique() -> None:
    assert not [item for item, count in Counter(case.id for case in CASES).items() if count > 1]


def test_every_class_is_asked_in_both_languages() -> None:
    languages: dict[str, set[str]] = {}
    for case in CASES:
        languages.setdefault(case.agent_class, set()).add("zh" if _CJK.search(case.question) else "en")
    for agent_class in BUILTIN_AGENT_CLASSES:
        assert languages.get(agent_class) == {"zh", "en"}, f"{agent_class}: {languages.get(agent_class)}"


def test_every_boundary_question_says_which_edge() -> None:
    for case in CASES:
        if case.boundary:
            assert case.why, case.id


def test_the_known_boundaries_hold() -> None:
    """The edges the plan names, spelled out so a keyword change that breaks one fails by name."""

    assert OUTCOMES["edge-01"].agent_class == "cybersecurity", "prompt injection is a security question"
    assert OUTCOMES["edge-03"].agent_class == "general", "dependency injection is not an attack"
    assert OUTCOMES["edge-07"].agent_class == "general", "'ai' must not match inside 'email'"


def test_the_metric_can_fail() -> None:
    """A router that always answers 'general' must score badly, or the numbers above prove nothing."""

    everything_general = evaluate(CASES, route=lambda question: ("general", "answer_with_citations"))

    general_share = sum(case.agent_class == "general" for case in CASES) / len(CASES)
    assert everything_general.class_accuracy == pytest.approx(general_share)
    assert everything_general.class_accuracy < 0.5
    assert ("cybersecurity", "general") in everything_general.confusion


def test_the_measured_accuracy() -> None:
    """The headline numbers, derived from the per-question pins above; they move only when a pin does."""

    assert REPORT.class_accuracy == pytest.approx(51 / 59)
    assert REPORT.per_class["general"] == (12, 12)
    assert REPORT.per_class["pdf_text"] == (6, 6)
