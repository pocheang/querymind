"""A possessive quantifier does not bound the scan, and two patterns proved it.

`python:S8786` still flagged these after the 2026-09-03 pass had "fixed" them
with possessive quantifiers, and the pass was wrong rather than the rule.
Possessive stops the engine backtracking WITHIN one attempt; it does nothing
about that attempt being restarted at the next offset. Given ``[.!?]++\\s+`` and
a run of n dots, the engine starts at dot 1, swallows the whole run, fails on
the whitespace, starts at dot 2, and so on -- O(n^2), with no backtracking
anywhere.

Measured before the fix, on one adversarial string:

    n=2000    n=4000    n=8000
    11.2ms    30.0ms   138.9ms     split, x12.4 for a x4 input
     6.8ms    27.2ms   100.6ms     tidy,  x14.8 for a x4 input

and afterwards 0.04 / 0.08 / 0.15ms, which is linear.

**The timing is not asserted here.** A clock is a bad thing to assert on in CI,
so what is pinned is the property that removed the cost -- a match may not begin
immediately after a character of its own leading class -- plus the equivalence
that makes the change safe at all. Both were verified against the previous
implementation over 4012 generated inputs before landing.

**The first version of this file could not fail**, which is worth more than the
fix. Its property test compiled a copy of the pattern written out as a constant
here, so removing the lookbehind from the shipped code left it green: it was
asserting that the test's own string contains a lookbehind. The pattern is
extracted from the module source and compiled now, so the property is about what
ships. Verified by deleting both lookbehinds: four tests redden, not two.

The other two findings in this rule are **false positives and were left alone**:
`PATTERN_HEADERS` and `PATTERN_LISTS` in `app/agents/rag/config.py` are anchored
with `^`/`$` under MULTILINE, so the scan only ever restarts at a line start.
Measured, they are linear (x2.0 and x3.3 for a x4 input).
"""

from __future__ import annotations

import re

import pytest

import app.agents.synthesizer.citations as citations
import app.ingestion.processing.coreference as coreference
from app.agents.synthesizer.citations import _tidy_spacing
from app.ingestion.processing.coreference import split_into_sentences

# Pull the raw-string literal out of the shipped call, so what is compiled below
# is the pattern the application uses rather than a copy that can drift.
_LITERAL_RE = re.compile(r'r"((?:[^"\\]|\\.)*)"')


def _shipped_pattern(module, needle: str) -> str:
    source = open(module.__file__, encoding="utf-8").read()
    line = next(one for one in source.splitlines() if needle in one)
    found = _LITERAL_RE.search(line)
    assert found is not None, f"no raw-string pattern on the line holding {needle!r}"
    return found.group(1)


SPLIT = ("split", coreference, "sentences = re.split(", ".", " x")
TIDY = ("tidy", citations, "tidied = re.sub(", " ", ",")


def test_the_sentence_splitter_still_splits():
    """Equivalence first: a bound that changes the output is not a fix."""

    assert split_into_sentences("One. Two! Three? Four") == ["One", "Two", "Three", "Four"]
    assert split_into_sentences("Multiple dots... then more") == ["Multiple dots", "then more"]
    assert split_into_sentences("") == []


def test_the_splitter_handles_chinese_terminators_as_before():
    """The pattern is Latin-only and always was; this pins that it did not
    quietly change while being made linear."""

    # No ASCII terminator, so this is one sentence -- the same answer as before.
    assert split_into_sentences("第一章。第二章！第三章？") == ["第一章。第二章！第三章？"]


def test_tidy_spacing_still_closes_the_gap():
    assert _tidy_spacing("a marker was here , and here .") == "a marker was here, and here."
    assert _tidy_spacing("nothing to do") == "nothing to do"


@pytest.mark.parametrize(
    ("name", "module", "needle", "run", "tail"), [SPLIT, TIDY], ids=lambda v: getattr(v, "__name__", v)
)
def test_a_match_never_begins_inside_a_run_of_its_own_leading_class(name, module, needle, run, tail):
    """The property that removed the quadratic scan, asserted on what ships.

    Every start offset inside a run used to be a fresh O(n) attempt. Forbidding
    a start there costs nothing, because the leftmost scan would have taken the
    match at the front of the run anyway.
    """

    compiled = re.compile(_shipped_pattern(module, needle))
    text = "a" + run * 40 + tail

    match = compiled.search(text)
    assert match is not None, "the pattern stopped matching, which is worse than the cost it fixed"

    # Now the property: no start position inside the run may produce a match
    # that begins there. `search` from offset 2 must skip to the run's end
    # rather than matching at 2.
    inside = compiled.search(text, 2)
    assert inside is None or text[inside.start() - 1] not in run, (
        "a match began inside the run, so the scan restarts at every offset again"
    )


@pytest.mark.parametrize(
    ("name", "module", "needle", "run", "tail"), [SPLIT, TIDY], ids=lambda v: getattr(v, "__name__", v)
)
def test_the_shipped_pattern_carries_a_lookbehind(name, module, needle, run, tail):
    """Deleting the bound fails here rather than only showing up as a slow
    request under a document nobody has uploaded yet."""

    assert _shipped_pattern(module, needle).startswith("(?<!"), (
        "the shipped pattern no longer refuses to start inside its own run"
    )


def test_a_long_run_that_matches_nothing_still_returns():
    """The shape that was slow, exercised end to end rather than timed."""

    assert split_into_sentences("." * 5000 + "x") == ["." * 5000 + "x"]
    assert _tidy_spacing(" " * 5000 + "x") == "x"
