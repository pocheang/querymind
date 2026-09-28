"""A number's unit is a whole word, never the first letter of the next one.

Found in plan acceptance A1 (2026-09-27): a faithful answer quoting a tool result
-- "CVE-2021-45105: CVSS 5.9 MEDIUM" -- was degraded with "Number 5.9 not found
in sources", because the source's "5.9 MEDIUM" had been read as 5.9 million.
The unit alternative matched case-insensitively with no boundary, so any word
starting with m, b or k after a number multiplied it.
"""

from __future__ import annotations

import pytest

from app.agents.verifier.validation.rules import extract_numbers


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("CVSS 5.9 MEDIUM", [5.9]),
        ("wait 10 minutes", [10.0]),
        ("3 known issues", [3.0]),
        ("2 before the patch", [2.0]),
        ("12 bytes", [12.0]),
    ],
)
def test_a_following_word_is_not_a_unit(text, expected):
    assert extract_numbers(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5.9 million", [5_900_000.0]),
        ("3 billion", [3e9]),
        ("$70B budget", [7e10]),
        ("a 70B model", [7e10]),
        ("12K tokens", [12_000.0]),
        ("4 thousand", [4_000.0]),
    ],
)
def test_a_real_unit_still_scales(text, expected):
    assert extract_numbers(text) == expected
