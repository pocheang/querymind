"""The sentence splitter and the spacing tidier scan in linear time, by construction.

Both used to be patterns of the shape ``[.!?]+\\s+`` -- a quantified run followed
by something that can fail. On a run of n dots the engine starts at dot 1,
swallows the run, fails on the whitespace, restarts at dot 2, and so on: O(n^2)
(python:S8786). The 2026-09-03 pass added possessive quantifiers, which stop
backtracking WITHIN one attempt and do nothing about the restart. The 2026-09-09
pass added a lookbehind forbidding a start inside the run -- linear, measured
0.15ms on 8000 dots against 139ms -- but linear only by argument, and SonarCloud
went on reporting both lines.

What ships now cannot fail once a match has started (``[.!?]+(\\s*)`` and
``[ \\t]+([,.;:!?]?)``); whether a match is a boundary is decided in Python
afterwards, from what the optional group captured. A scan whose every attempt
succeeds never restarts, so there is nothing left to argue.

**The timing is not asserted.** A clock is a bad thing to assert on in CI. What
is pinned is that property, on the compiled objects the modules actually use,
and equivalence with the previous implementation over generated inputs -- a
bound that changes the output is not a fix.

``PATTERN_HEADERS`` and ``PATTERN_LISTS`` (``app/agents/rag/config.py``) were
anchored and already linear. ``[ \\t]+[^\\n]+`` became ``[ \\t][^\\n]+``: the same
language, without two adjacent quantifiers competing for the same spaces. Their
equivalence is pinned here too, by span rather than by count.
"""

from __future__ import annotations

import inspect
import random
import re

import pytest

import app.agents.synthesizer.citations as citations
import app.ingestion.processing.coreference as coreference
from app.agents.rag.config import PATTERN_HEADERS, PATTERN_LISTS
from app.agents.synthesizer.citations import _tidy_spacing
from app.ingestion.processing.coreference import split_into_sentences

# --- the previous implementations, verbatim, as the reference -----------------


def _previous_split(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<![.!?])[.!?]++\s+", text) if s.strip()]


def _previous_tidy(text: str) -> str:
    tidied = re.sub(r"(?<![ \t])[ \t]++([,.;:!?])", r"\1", str(text or ""))
    tidied = re.sub(r"(?<!\n)[ \t]{2,}+", " ", tidied)
    return tidied.strip()


_PREVIOUS_HEADERS = re.compile(r"^#{1,8}[ \t]+[^\n]+$|^\d{1,9}\.[ \t]+[A-Z][^.\n]+$", re.MULTILINE)
_PREVIOUS_LISTS = re.compile(r"^[-*•][ \t]+[^\n]+$|^\d{1,9}\.[ \t]+[^\n]+$", re.MULTILINE)

# Every character class any of these patterns distinguishes, plus the Unicode
# whitespace `\s` matches and `[ \t]` does not, plus CJK punctuation.
_ALPHABET = ".!? \t\n\r　\xa0\x1c,;:#-*•1Aab。"


def _generated(count: int = 4000, seed: int = 20260910) -> list[str]:
    rng = random.Random(seed)
    return ["", *("".join(rng.choice(_ALPHABET) for _ in range(rng.randint(1, 24))) for _ in range(count))]


# --- equivalence ---------------------------------------------------------------


def test_the_splitter_matches_the_previous_implementation():
    differing = [text for text in _generated() if split_into_sentences(text) != _previous_split(text)]

    assert not differing, f"{len(differing)} inputs split differently, e.g. {differing[:3]!r}"


def test_the_tidier_matches_the_previous_implementation():
    differing = [text for text in _generated() if _tidy_spacing(text) != _previous_tidy(text)]

    assert not differing, f"{len(differing)} inputs tidied differently, e.g. {differing[:3]!r}"


@pytest.mark.parametrize(
    ("shipped", "previous"),
    [(PATTERN_HEADERS, _PREVIOUS_HEADERS), (PATTERN_LISTS, _PREVIOUS_LISTS)],
    ids=["headers", "lists"],
)
def test_the_structure_patterns_match_the_same_spans(shipped, previous):
    """Spans, not counts: the detectors use `search`/`findall`, and an equal
    count over a different span would still be a different pattern."""

    differing = [
        text
        for text in _generated()
        if [m.span() for m in shipped.finditer(text)] != [m.span() for m in previous.finditer(text)]
    ]

    assert not differing, f"{len(differing)} inputs matched differently, e.g. {differing[:3]!r}"


def test_the_sentence_splitter_still_splits():
    assert split_into_sentences("One. Two! Three? Four") == ["One", "Two", "Three", "Four"]
    assert split_into_sentences("Multiple dots... then more") == ["Multiple dots", "then more"]
    assert split_into_sentences("") == []


def test_the_splitter_handles_chinese_terminators_as_before():
    """The pattern is Latin-only and always was; this pins that it did not
    quietly change while being made linear."""

    assert split_into_sentences("第一章。第二章！第三章？") == ["第一章。第二章！第三章？"]


def test_tidy_spacing_still_closes_the_gap():
    assert _tidy_spacing("a marker was here , and here .") == "a marker was here, and here."
    assert _tidy_spacing("nothing to do") == "nothing to do"


# --- the property that makes the scan linear ------------------------------------

SPLIT = ("split", coreference._TERMINATOR_RE, ".")
TIDY = ("tidy", citations._SPACE_RUN_RE, " ")


def _every_start_inside_the_run_succeeds(compiled: re.Pattern[str], run: str) -> bool:
    # A tail that is neither whitespace nor punctuation: the input on which the
    # old shape failed at every offset and so restarted at every offset.
    text = "a" + run * 40 + "a"
    return all(compiled.match(text, offset) is not None for offset in range(1, 41))


@pytest.mark.parametrize(("name", "compiled", "run"), [SPLIT, TIDY], ids=lambda v: v if isinstance(v, str) else "")
def test_a_match_that_has_started_cannot_fail(name, compiled, run):
    """If no attempt fails, the scan never restarts inside a run -- linear."""

    assert _every_start_inside_the_run_succeeds(compiled, run)


@pytest.mark.parametrize(
    ("pattern", "run"),
    [(r"[.!?]++\s+", "."), (r"[ \t]++([,.;:!?])", " ")],
    ids=["old-split", "old-tidy"],
)
def test_the_property_rejects_the_shape_that_was_quadratic(pattern, run):
    """Proof the check above can fail: the old shapes do not satisfy it."""

    assert not _every_start_inside_the_run_succeeds(re.compile(pattern), run)


@pytest.mark.parametrize(
    ("function", "constant"),
    [(split_into_sentences, "_TERMINATOR_RE"), (_tidy_spacing, "_SPACE_RUN_RE")],
    ids=["split", "tidy"],
)
def test_the_functions_scan_with_the_patterns_the_property_is_about(function, constant):
    """Otherwise the property could hold for a constant nothing uses."""

    assert constant in inspect.getsource(function)


def test_a_long_run_that_matches_nothing_still_returns():
    """The shape that was slow, exercised end to end rather than timed."""

    assert split_into_sentences("." * 5000 + "x") == ["." * 5000 + "x"]
    assert _tidy_spacing(" " * 5000 + "x") == "x"
