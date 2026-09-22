"""A public identifier is not a phone number, and redacting one destroys the answer.

`_PHONE_RE` is `\\d[\\d()\\-\\s]{7,}\\d`, which treats a dash and a space as free
filler -- so it claimed any digit run of the right length that happened to
contain one. Measured through the live `filter_output` before the fix:

    Log4Shell 是 CVE-2021-44228           -> Log4Shell 是 CVE-<PHONE_1>
    备份保留窗口为 2026-01-01 至 2026-12-31   -> 备份保留窗口为 <PHONE_1> 至 <PHONE_2>

This is the failure `test_chinese_pii_redaction.py` records -- the generic rule
owning a specific one's span -- reached from the other side: the span is not
sensitive at all, so the redaction removes text the reader and the model both
need.

Two things make it worse than cosmetic. `privacy_permission` REPLACES
`request.question` with the inspected text, so a question about a CVE reached
the router, the retrievers and `querymind_cyber_cve_lookup` with the identifier
already gone. And tokenization is stable by value, so two different timestamps
in one answer collapsed into ONE token.

Half of this file asserts what must STILL be redacted, because a fix to an
over-broad privacy rule fails in the silent direction: a phone number that
stops being caught looks exactly like a test suite that is passing.
"""

from __future__ import annotations

import pytest

from app.domain.knowledge import AccessScope
from app.privacy.service import PrivacyService
from app.privacy.text import INPUT_KINDS, OUTPUT_KINDS, inspect_text
from app.services.security.outbound_redaction import _PHONE_RE


def _kinds(text: str, *, kinds: frozenset[str] = OUTPUT_KINDS) -> dict[str, int]:
    return {finding.kind: finding.count for finding in inspect_text(text, kinds=kinds).findings}


def _scope() -> AccessScope:
    return AccessScope(tenant_id="t1", user_id="u1", role="user", allowed_fields=frozenset({"content"}))


# --- what must survive ----------------------------------------------------


@pytest.mark.parametrize(
    "sample",
    [
        "CVE-2021-44228",
        "CVE-2024-3094",
        "CVE-1999-0001",
        "cve-2021-44228",
        "Log4Shell 是 CVE-2021-44228，CVSS 10.0。",
        "See CVE-2024-3094 and CVE-2021-44228 for details.",
    ],
)
@pytest.mark.parametrize("kinds", [INPUT_KINDS, OUTPUT_KINDS], ids=["input", "output"])
def test_a_cve_identifier_is_not_redacted(sample: str, kinds: frozenset[str]) -> None:
    """Both directions, because the inbound one is what broke the cyber tools."""
    assert inspect_text(sample, kinds=kinds).text == sample
    assert _kinds(sample, kinds=kinds) == {}


@pytest.mark.parametrize(
    "sample",
    [
        "2026-09-21",
        "2026-1-5",
        "于 2026-09-21 发布",
        "备份保留窗口为 2026-01-01 至 2026-12-31。",
        "2026-09-21 12:00",
        "2026-09-21 12:00:00",
        # Two dates with nothing but whitespace between them. This is the case
        # the first attempt at the fix got WRONG: refusing to start a match at
        # the year only moves the start inside the date, because the scan
        # restarts at the next offset and `-` is not `\\w`.
        "2026-01-01 2026-12-31",
        "2013-9-1 1997-11-14",
        "窗口\n2026-09-21\n2026-12-31",
    ],
)
def test_a_calendar_date_is_not_a_phone_number(sample: str) -> None:
    assert inspect_text(sample, kinds=OUTPUT_KINDS).text == sample


def test_an_incident_timeline_keeps_its_two_timestamps_apart() -> None:
    """The sharpest form of the defect, and not merely a redaction artefact.

    Tokens are stable by value, so both timestamps used to redact to the SAME
    `<PHONE_1>` -- an answer reporting two events at one moment, which is a
    factual corruption rather than a missing detail.
    """

    answer = "事件时间线：2026-09-21 12:00 首次告警，2026-09-21 12:40 隔离。"

    assert PrivacyService().filter_output(answer, [], _scope()).answer == answer


def test_the_question_reaches_retrieval_with_its_cve_intact() -> None:
    """`privacy_permission` hands `inspect_input`'s text on as the question, so
    this is what the router, the retrievers and the CVE tool actually see."""

    question = "CVE-2021-44228 影响哪些版本？"

    assert PrivacyService().inspect_input(question).text == question


# --- what must still be redacted ------------------------------------------


@pytest.mark.parametrize(
    "sample",
    [
        "call +1 415 555 0132",
        "tel (415) 555-2671",
        "021-12345678",
        "010-87654321",
        "联系 138 0013 8000",
        "+44 20 7123 4567",
        "0755 8888 6666",
        "+86-138-0013-8000",
    ],
)
def test_a_real_phone_number_is_still_redacted(sample: str) -> None:
    result = inspect_text(sample, kinds=OUTPUT_KINDS)
    assert result.text != sample, f"{sample} stopped being redacted"
    assert "PHONE" in {finding.kind for finding in result.findings}


def test_a_phone_number_next_to_a_date_is_still_redacted() -> None:
    """The date exclusions must not shelter whatever follows a date."""
    result = inspect_text("2026-09-21 起请拨 021-12345678", kinds=OUTPUT_KINDS)
    assert "2026-09-21" in result.text
    assert "021-12345678" not in result.text


@pytest.mark.parametrize(
    "sample",
    ["2026-09-211234567", "2026-09-2113800138000", "拨 2026-09-21123456"],
)
def test_a_digit_run_that_merely_opens_like_a_date_is_still_redacted(sample: str) -> None:
    """The date exclusion's right boundary, which is the half that fails open.

    Drop the trailing `(?!\\d)` and the lookahead is satisfied by the first ten
    characters of a much longer run, so the whole number escapes -- the same
    boundary defect this repository already records for `BANK_CARD`, where
    `(?!\\d)` was satisfied by a letter. A date ends; a number that keeps going
    was never one.
    """

    assert inspect_text(sample, kinds=OUTPUT_KINDS).text != sample


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        # The stated boundary: shape alone cannot separate these from a
        # national number, so they are matched on purpose rather than missed.
        ("编号 2021-44228", {"PHONE": 1}),
        ("端口 8000-9000", {"PHONE": 1}),
        ("订单 1234567890", {"PHONE": 1}),
        # And the specific rules that must keep beating the generic one.
        ("手机 13912345678", {"MOBILE_CN": 1}),
        ("110101199003072316", {"ID_CARD_CN": 1}),
        ("6222021234567890123", {"BANK_CARD": 1}),
    ],
)
def test_the_boundary_is_stated_not_discovered(sample: str, expected: dict[str, int]) -> None:
    assert _kinds(sample) == expected


# --- the property, on the object the code uses ----------------------------


def test_no_match_begins_inside_a_dashed_digit_group() -> None:
    """Asserted on the compiled pattern rather than on a transcription of it:
    a test that compiles its own copy stays green when the shipped one loses a
    lookaround.  This is the rule that makes two adjacent dates survive, and it
    is invisible in any single-date example.
    """

    for text in ("2026-01-01 2026-12-31", "2013-9-1 1997-11-14", "1-2 3456-7890-1234"):
        for match in _PHONE_RE.finditer(text):
            assert not text[max(0, match.start() - 2) : match.start()].endswith(
                tuple(f"{digit}-" for digit in "0123456789")
            ), f"{text!r} matched {match.group(0)!r} starting inside a dashed group"
