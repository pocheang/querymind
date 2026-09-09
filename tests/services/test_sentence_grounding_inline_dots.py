"""A dot inside an identifier is not a sentence boundary.

`apply_sentence_grounding` hedges sentences it judges unsupported, and it splices
the hedge in by OFFSET. So a wrong sentence boundary does not merely mis-score --
it corrupts the text. Observed in a real answer on 2026-09-09:

    ... (如 config.基于当前可用证据，py、settings.基于当前可用证据，yaml ...)

`config.py` and `settings.yaml` were each split at their dot, and the fragment
after it scored as unsupported.

CLAUDE.md records this defect class as fixed on 2026-09-05, and that fix was
right for what it covered: `_ABBREVIATION_RE` protects "Dr.", "pp.", "no.". It
could not cover this, because a filename is not an abbreviation and there is no
list of extensions to keep up with -- `config.py`, `settings.yaml`,
`app.services.models`, `v1.2.3`. So this states the property instead: an English
sentence ends with a dot followed by a space or by nothing, and a Chinese one
ends with "。", so a dot BETWEEN two alphanumerics is never a boundary in either.

The direction that matters most is the second set of assertions: a rule that
protected too much would stop splitting real sentences, and every paragraph
would then be scored as one claim.
"""

from __future__ import annotations

import pytest

from app.services.retrieval.citation_grounding import _sentence_spans


@pytest.mark.parametrize(
    "text",
    [
        "建议直接查看项目的配置文件（如 config.py、settings.yaml 或环境变量配置）以获取准确数值。",
        "See app.services.models.runtime for the loader.",
        "Upgrade to v1.2.3 before reindexing.",
    ],
)
def test_an_identifier_is_not_split(text: str):
    spans = _sentence_spans(text)

    assert len(spans) == 1, f"split into {[t for _, _, t in spans]}"
    # And the span is the text itself: protection must be length-preserving, or
    # the offsets the caller splices by are wrong -- which is the other half of
    # the 2026-09-05 bug.
    start, end, sentence = spans[0]
    assert text[start:end] == sentence


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Access is based. The retention window is ninety days.", 2),
        ("End of sentence. Next one. And a third.", 3),
        ("第一句话。第二句话。", 2),
    ],
)
def test_real_boundaries_still_split(text: str, expected: int):
    """The direction a too-eager protection breaks.

    If a dot followed by a space stopped ending a sentence, a whole paragraph
    would be judged and rewritten as a single claim -- which is worse than the
    defect this rule fixes, and silent.
    """

    assert len(_sentence_spans(text)) == expected


def test_a_url_is_still_protected():
    """The 2026-09-05 protection this sits beside, so neither is lost."""

    text = "The loader is documented at https://example.com/docs/a.b for reference."

    assert len(_sentence_spans(text)) == 1


def test_the_substitution_preserves_length():
    """Every protection has to be one character for one character.

    `_ABBR_DOT` is `chr(0xE000)` for exactly this reason; the original sentinel
    was `"<ABBR>"`, six characters replacing one, beside a comment asserting the
    substitution never shifted a position.
    """

    from app.services.retrieval.citation_grounding import _ABBR_DOT

    assert len(_ABBR_DOT) == 1

    text = "Read config.py, then app.services.models, then https://x.example/a.b ."
    spans = _sentence_spans(text)
    for start, end, sentence in spans:
        assert text[start:end] == sentence, "an offset moved, so a hedge would land inside a word"
