"""Entailment scores each claim against short passages of the sources, not all of them joined.

Measured on 2026-09-27 against the configured cross-encoder
(`cross-encoder/nli-MiniLM2-L6-H768`, 512 tokens):

- With read web pages the joined premise reached 3,810 tokens. Everything past
  the first 512 was cut off, so a claim citing the third source was scored
  against text that did not contain it.
- Even a single 400-token source, well inside the limit, made the model answer
  "neutral": "Kubernetes ... is an open-source platform that automates the
  deployment, scaling, and management of containerized applications", copied
  word for word from its source, scored 0.08. The answer was rejected with
  "5 sentences not entailed".

Scored against its two lexically closest ~300-character windows instead, the
same answer had 2 of 5 claims unsupported (both opening with "It", which no
sentence-level NLI model resolves), at 0.15-0.76 s against the 1.2 s budget.

The fake model below reproduces what was measured -- it entails a claim only
when the claim is inside a SHORT premise -- so these tests fail on the joined
premise for the same reason the real model did.
"""

from __future__ import annotations

import asyncio
from typing import Any

import numpy as np
import pytest

from app.agents.verifier.validation import nli
from app.agents.verifier.validation.models import ValidationRequest
from app.agents.verifier.validation.nli import NLIValidator, premise_windows

_SHORT_PREMISE = 2 * nli._PREMISE_CHARS + 1


class _SentenceLengthNLI:
    """Entailed only when the claim's words are all in a premise short enough to judge."""

    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []
        self.model = type(
            "M", (), {"config": type("C", (), {"id2label": {0: "contradiction", 1: "entailment", 2: "neutral"}})()}
        )()

    def predict(self, pairs: list[tuple[str, str]]) -> Any:
        self.pairs.extend(pairs)
        rows = []
        for premise, claim in pairs:
            words = set(nli.tokenize(claim))
            entailed = len(premise) <= _SHORT_PREMISE and words <= set(nli.tokenize(premise))
            rows.append([0.0, 9.0, 0.0] if entailed else [0.0, 0.0, 9.0])
        return np.array(rows)


def _filler(topic: str, count: int) -> str:
    return " ".join(
        f"The {topic} paragraph number {index} talks about unrelated maintenance chores." for index in range(count)
    )


def _validate(model: _SentenceLengthNLI, answer: str, documents: list[str], max_sentences: int = 5):
    request = ValidationRequest.from_compatibility(
        query="q",
        answer=answer,
        source_docs=[{"id": str(i), "content": d} for i, d in enumerate(documents)],
        citations=[],
    )
    return asyncio.run(NLIValidator(max_sentences=max_sentences).validate(request))


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> _SentenceLengthNLI:
    fake = _SentenceLengthNLI()
    monkeypatch.setattr(nli, "load_nli_cross_encoder", lambda: fake)
    return fake


def test_a_claim_from_the_last_of_five_long_sources_is_entailed(model):
    """Joined, this source sits thousands of characters past where the model stops reading."""

    documents = [_filler(f"topic{index}", 20) for index in range(4)]
    documents.append(_filler("backup", 20) + " Backups are encrypted with AES-256 and kept for ninety days.")

    result = _validate(model, "Backups are encrypted with AES-256 and kept for ninety days.", documents)

    assert result.issues == [], result.issues
    assert result.backend == "cross_encoder"


def test_a_claim_copied_from_one_long_source_is_entailed(model):
    """The Kubernetes case: one source, within the token limit, still too long to judge."""

    source = _filler("cluster", 12) + " Kubernetes automates the deployment and scaling of containerized applications."

    result = _validate(
        model, "Kubernetes automates the deployment and scaling of containerized applications.", [source]
    )

    assert result.issues == []


def test_a_claim_the_sources_do_not_contain_is_still_not_entailed(model):
    """Windowing must find support where it is, not invent it where it is not."""

    documents = [_filler("backup", 20)]
    answer = "Backups are replicated to three regions every hour. Restores are tested weekly by the operations team."

    result = _validate(model, answer, documents)

    assert result.issues and "not entailed" in result.issues[0].content


def test_every_premise_handed_to_the_model_is_short(model):
    documents = [_filler(f"topic{index}", 30) for index in range(5)]

    _validate(model, "The topic3 paragraph number 7 talks about unrelated maintenance chores.", documents)

    assert model.pairs
    assert max(len(premise) for premise, _ in model.pairs) <= _SHORT_PREMISE


def test_the_batch_is_bounded_by_claims_not_by_sources(model):
    """Five long sources must not multiply the batch: each claim meets its closest windows only."""

    documents = [_filler(f"topic{index}", 40) for index in range(5)]
    answer = " ".join(
        f"The topic{index} paragraph number 3 talks about unrelated maintenance chores." for index in range(4)
    )

    _validate(model, answer, documents, max_sentences=4)

    assert len(model.pairs) <= 4 * nli._PREMISES_PER_CLAIM
    assert len(premise_windows(documents)) > 4 * nli._PREMISES_PER_CLAIM, (
        "the sources must offer more windows than are used"
    )


def test_a_claim_meets_the_window_that_shares_its_words(model):
    documents = [_filler("noise", 15), "Access keys rotate every thirty days under the credential policy."]

    _validate(model, "Access keys rotate every thirty days under the credential policy.", documents)

    assert any("Access keys rotate" in premise for premise, _ in model.pairs)


def test_a_page_line_is_a_boundary():
    """A read web page arrives one paragraph or table row per line."""

    windows = premise_windows(["First row | alpha\nSecond row | beta"])

    assert windows[0] == "First row | alpha Second row | beta"
    assert all("\n" not in window for window in windows)


def test_a_claim_spanning_two_windows_can_meet_both_halves():
    units = [f"Sentence {index} carries about sixty characters of padding text here." for index in range(12)]

    windows = premise_windows([" ".join(units)])

    packed = [window for window in windows if len(window) <= nli._PREMISE_CHARS]
    assert len(packed) >= 2
    assert f"{packed[0]} {packed[1]}" in windows
