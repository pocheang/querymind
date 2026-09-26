"""Three patterns that backtracked exponentially, rewritten (CodeQL #21, #22, #23).

Each rewrite is checked the way this repository checks every regex change: by
equivalence with the previous pattern over generated inputs, on the compiled
object the module actually uses. The "does not hang" tests use inputs the old
patterns needed minutes for; against the old code they run into pytest's
timeout, so they fail without asserting a duration.
"""

from __future__ import annotations

import random
import re

import pytest

from app.agents.rag.config import PATTERN_CAMEL_CASE
from app.ingestion.extraction.formulas import EQUATION_PATTERN, detect_formula
from app.retrievers.query_expansion import TECHNICAL_TERM_PATTERN

OLD_CAMEL_CASE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][A-Za-z0-9]+)+\b")
OLD_TECHNICAL_TERM = re.compile(r"\b(?:[a-z]+[A-Z][a-z]*)+\b")
OLD_EQUATION = re.compile(r"\b([A-Z])\s*=\s*([^\s,;.]+(?:\s*[+\-*/^]\s*[^\s,;.]+)*)\b")


def _spans(pattern, text):
    return [(m.span(), m.groups()) for m in pattern.finditer(text)]


def _generated(alphabet, count, seed, max_len=24):
    rng = random.Random(seed)
    for _ in range(count):
        yield "".join(rng.choice(alphabet) for _ in range(rng.randint(0, max_len)))


def test_camel_case_matches_what_it_used_to():
    for text in _generated("AbBaZz09_ -中.", 20_000, seed=21):
        assert _spans(PATTERN_CAMEL_CASE, text) == _spans(OLD_CAMEL_CASE, text), text


def test_technical_terms_match_what_they_used_to():
    for text in _generated("abAB_ 0中-", 20_000, seed=23):
        assert _spans(TECHNICAL_TERM_PATTERN, text) == _spans(OLD_TECHNICAL_TERM, text), text


def test_detect_formula_uses_the_rewritten_pattern():
    """So the tests below test what ingestion runs, not a copy of it."""

    found = [f["formula"] for f in detect_formula("F = - 0") if f["type"] == "equation"]
    assert found == ["F = - 0"]


def test_equations_never_lose_a_match_the_old_pattern_made():
    for text in _generated("EFab01 =+-*/^!,;._中", 40_000, seed=22, max_len=28):
        old_spans = [m.span() for m in OLD_EQUATION.finditer(text)]
        new_spans = [m.span() for m in EQUATION_PATTERN.finditer(text)]
        for start, end in old_spans:
            assert any(s <= start and e >= end for s, e in new_spans), text


def test_the_one_intended_difference_reads_a_unary_minus():
    assert [m.group(0) for m in EQUATION_PATTERN.finditer("F = - 0")] == ["F = - 0"]
    assert OLD_EQUATION.search("F = - 0") is None


@pytest.mark.parametrize(
    ("name", "pattern", "text"),
    [
        ("camelCase", PATTERN_CAMEL_CASE, "Ab" + "A" * 60 + "_"),
        ("technical term", TECHNICAL_TERM_PATTERN, "aaA" * 30 + "_"),
    ],
)
def test_the_inputs_that_backtracked_finish(name, pattern, text):
    list(pattern.finditer(text))


def test_a_crafted_formula_line_does_not_stall_ingestion():
    detect_formula("E=!" + "*!" * 30)
