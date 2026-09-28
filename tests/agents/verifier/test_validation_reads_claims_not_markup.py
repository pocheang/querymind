"""Validation reads the answer's claims, not its Markdown.

Replayed over thirty real answers on 2026-09-27, the checks raised 54 "Number
... not found" and 16 "Entities not in source" issues, most of them about
markup: list and heading ordinals read as numbers, Title Case headings read as
names, capitalised runs that crossed a paragraph break, and the NLI stage
splitting "CVSS v3.1 score of 9.8" at every dot. Sentence grounding had the
same blind spot and put its hedge inside headings.

Several tests here are negative on purpose -- a real claim must still be
checked -- because loosening a check fails in the silent direction.
"""

from __future__ import annotations

import pytest

from app.agents.verifier.validation.claims_text import claims_text
from app.agents.verifier.validation.hallucination_patterns import (
    detect_all_patterns,
    detect_entity_hallucinations,
)
from app.services.retrieval.citation_grounding import apply_sentence_grounding, split_sentences

_SOURCE = "Spring Framework before 5.2.20 is affected. The CVSS score is 9.8."


def _kinds(issues) -> list[str]:
    return [issue.pattern_type for issue in issues]


# --- the view ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("markup", "claims"),
    [
        ("#### 2. **最小权限授予**\n零信任架构遵循最小权限。", "零信任架构遵循最小权限。"),
        ("### Affected Spring Framework Versions\nVersions before 5.2.20.", "Versions before 5.2.20."),
        ("1. First point.\n2) Second point.", "First point.\nSecond point."),
        ("- **Application Isolation**: run it in a container", "run it in a container"),
        ("CVSS 为 9.8 [T1]，先隔离主机 [E1]。", "CVSS 为 9.8  ，先隔离主机  。"),
        ("---\nBody.", "Body."),
    ],
)
def test_markup_is_removed(markup: str, claims: str) -> None:
    assert claims_text(markup) == claims


@pytest.mark.parametrize(
    "kept",
    [
        "See https://spring.io/security/cve-2022-22965 for details.",
        "The job ran at 12:00 and finished at 12:40.",
        "根据 NVD 在 2026 年 9 月 23 日核对过的 CPE 配置数据以及官方安全公告的描述：受影响版本为 5.3.0 至 5.3.18 之前",
        "Upgrade to 5.3.18 or later.",
    ],
)
def test_claims_are_kept(kept: str) -> None:
    assert claims_text(kept) == kept


# --- the checks read the view ------------------------------------------------------


def test_list_and_heading_ordinals_are_not_numbers() -> None:
    answer = "#### 2. Scope\nThe CVSS score is 9.8.\n\n3. Spring Framework before 5.2.20 is affected."
    assert "number_mismatch" not in _kinds(detect_all_patterns(answer, _SOURCE))


def test_a_number_the_sources_lack_is_still_caught() -> None:
    assert "number_mismatch" in _kinds(detect_all_patterns("1. The CVSS score is 7.1.", _SOURCE))


def test_a_heading_is_not_a_name() -> None:
    answer = "### Affected Spring Framework Versions\nSpring Framework before 5.2.20 is affected."
    assert "entity_mismatch" not in _kinds(detect_all_patterns(answer, _SOURCE))


def test_a_capitalised_run_stops_at_the_end_of_its_line() -> None:
    """With `\\s` it crossed the paragraph break: "Versions\\n\\nThe" was a name."""

    # `Meanwhile` is not in the source, so a run that crossed the break would
    # be flagged; on its own line a single capitalised word is not a name.
    issues = detect_entity_hallucinations("Spring Framework\n\nMeanwhile the score is high.", _SOURCE)
    assert issues == []


def test_a_name_the_sources_lack_is_still_caught() -> None:
    issues = detect_all_patterns("The flaw was found by Acme Security Labs.", _SOURCE)
    assert "entity_mismatch" in _kinds(issues)


def test_the_numeric_absence_rule_ignores_ordinals() -> None:
    import asyncio

    from app.agents.verifier.validation.models import ValidationRequest
    from app.agents.verifier.validation.rules import RuleValidator

    request = ValidationRequest.from_compatibility(
        query="q",
        answer="1. Isolate the host.\n2. Upgrade the library.",
        source_docs=[{"id": "d", "content": "Isolate the host and upgrade the library."}],
        citations=[],
    )
    result = asyncio.run(RuleValidator().validate(request))
    assert not any("Numeric claims are absent" in issue.content for issue in result.issues)


# --- sentences ---------------------------------------------------------------------


def test_a_decimal_or_a_version_does_not_end_a_sentence() -> None:
    text = "CVE-2022-22965 has a CVSS v3.1 score of 9.8. It affects Spring before 5.3.18."
    assert split_sentences(text) == [
        "CVE-2022-22965 has a CVSS v3.1 score of 9.8.",
        "It affects Spring before 5.3.18.",
    ]


def test_the_nli_stage_scores_whole_sentences(monkeypatch: pytest.MonkeyPatch) -> None:
    """It split at every dot: three sentences became seven fragments."""

    import asyncio

    from app.agents.verifier.validation import nli
    from app.agents.verifier.validation.models import ValidationRequest

    seen: list[list[str]] = []

    def score(_model, _source, sentences):
        seen.append(list(sentences))
        return [0.9] * len(sentences)

    monkeypatch.setattr(nli, "load_nli_cross_encoder", lambda: object())
    monkeypatch.setattr(nli, "_score_sentences", score)
    request = ValidationRequest.from_compatibility(
        query="q",
        answer="CVE-2022-22965 has a CVSS v3.1 score of 9.8 [T1]. It affects Spring Framework before 5.3.18 [T1].",
        source_docs=[{"id": "d", "content": _SOURCE}],
        citations=[],
    )

    asyncio.run(nli.NLIValidator().validate(request))

    assert seen == [["CVE-2022-22965 has a CVSS v3.1 score of 9.8  .", "It affects Spring Framework before 5.3.18  ."]]


# --- the hedge stays out of headings --------------------------------------------------


@pytest.mark.parametrize("heading", ["#### 受影响版本范围", "#### 2. **最小权限授予**", "### Affected Versions"])
def test_the_hedge_never_lands_in_a_heading(heading: str) -> None:
    answer = f"{heading}\n该系统在周二凌晨完成了全部备份的异地复制。"
    grounded, report = apply_sentence_grounding(answer, ["与此无关的一段证据文本，讲的是别的事情。"])

    assert grounded.splitlines()[0] == heading
    assert report["rewritten_sentences"] == 1
    assert grounded.splitlines()[1].startswith("基于当前可用证据")
