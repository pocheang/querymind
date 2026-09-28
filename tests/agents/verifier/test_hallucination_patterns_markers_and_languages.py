"""Two false positives in the hallucination patterns, found by verifying a tool-cited answer.

Measured with the real validator on a Chinese answer that cites the CVE
lookup's English summary with `[T1]`:

- "Number 1.0 not found in sources", three times. The number pattern has no
  word boundary, so every citation marker -- `[E1]`, `[T1]`, `[1]` alike --
  read as the number 1. It had always done this; evidence usually contains a
  "1" somewhere, which is what hid it.
- "Entities not in source: 之前, 修复方式, 评分为, ...". Every two-to-four
  character Chinese run is an entity candidate, and none can be found in an
  English source, so a Chinese answer over English material always "invented"
  its own wording.

Half of these tests are negative on purpose: loosening a hallucination check
fails in the silent direction, and a check that stops firing looks exactly
like a passing suite.
"""

from __future__ import annotations

import pytest

from app.agents.verifier.validation.hallucination_patterns import (
    detect_all_patterns,
    detect_entity_hallucinations,
    detect_number_hallucinations,
)

_ENGLISH_SOURCE = (
    "[CVE-2022-22965] Spring4Shell (CVSS 9.8 CRITICAL): Affects Spring Framework before 5.2.20, "
    "5.3.0 to before 5.3.18. Upgrade to 5.3.18 or 5.2.20."
)


def _numbers(issues) -> list[str]:
    return [issue.content for issue in issues if issue.pattern_type == "number_mismatch"]


def _entities(issues) -> list[str]:
    return [issue.content for issue in issues if issue.pattern_type == "entity_mismatch"]


@pytest.mark.parametrize("marker", ["[E1]", "[T1]", "[1]", "[E12]", "[T3]"])
def test_a_citation_marker_is_not_a_number(marker: str) -> None:
    answer = f"The CVSS score is 9.8 {marker}."
    assert _numbers(detect_all_patterns(answer, _ENGLISH_SOURCE)) == []


def test_a_number_the_source_lacks_is_still_caught_beside_a_marker() -> None:
    issues = detect_all_patterns("The CVSS score is 7.1 [T1].", _ENGLISH_SOURCE)
    assert _numbers(issues) == ["Number 7.1 not found in sources (within 15% tolerance)"]


def test_the_detector_alone_still_reads_markers_as_numbers() -> None:
    """Stripping happens in `detect_all_patterns`, once, for every detector.

    Pinned so the stripping is not quietly moved into one detector and lost
    from the others: the number detector itself has no notion of a marker.
    """

    assert _numbers(detect_number_hallucinations("Score 9.8 [T1].", "Score 9.8.")) != []


def test_chinese_wording_is_not_checked_against_an_english_source() -> None:
    answer = "CVE-2022-22965 的评分为 9.8，受影响的版本包括 5.3.18 之前，修复方式是升级。"
    assert _entities(detect_all_patterns(answer, _ENGLISH_SOURCE)) == []


def test_a_chinese_entity_is_still_checked_against_a_chinese_source() -> None:
    issues = detect_entity_hallucinations("张伟负责该项目。", "李娜负责该项目的安全评估。")
    assert _entities(issues) != []


def test_a_latin_name_is_still_checked_against_a_latin_source() -> None:
    issues = detect_entity_hallucinations("Maintained by Acme Security Labs.", _ENGLISH_SOURCE)
    assert _entities(issues) != []


def test_a_latin_name_is_still_checked_when_the_answer_is_chinese() -> None:
    """Only the Chinese candidates are set aside; a Latin name in a Chinese
    answer is comparable with an English source and stays checked."""

    issues = detect_entity_hallucinations("该漏洞由 Acme Security Labs 发现。", _ENGLISH_SOURCE)
    assert _entities(issues) != []
