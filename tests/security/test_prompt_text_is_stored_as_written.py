"""A prompt template is stored and checked as written (CodeQL #19, #20, #24-#27).

`_normalize_prompt_fields` and `prompt_checker._sanitize_output` ran an HTML
blacklist over the text: strip `<...>`, `javascript:`, `on\\w+=` and
`<script>...</script>`. It was not an XSS defence -- `<img src=x onerror=...>`
kept its tag -- and prompts are rendered as React text, which is where escaping
happens. It did damage ordinary prompts, and its patterns backtracked
quadratically on the 50,000 characters these endpoints accept, so one request
from any signed-in user could hold a worker for seconds.

These tests pin the text surviving intact. That is also the property that
removes the denial of service: nothing runs a pattern over the content any more.
"""

from __future__ import annotations

import pytest

from app.api.dependencies import _normalize_prompt_fields
from app.services.security.prompt_checker import _sanitize_output

ORDINARY_PROMPTS = [
    ("Compare <A> and <B>", "Explain the difference between <A> and <B> for a new engineer."),
    ("JS URLs", "Why do browsers block javascript: URLs in links? Give two examples."),
    ("Form fields", "Name the field button=submit and explain what onclick= does in HTML."),
    ("Script tags", "Explain what <script>alert(1)</script> does when it is rendered as HTML."),
]


@pytest.mark.parametrize(("title", "content"), ORDINARY_PROMPTS)
def test_a_prompt_is_stored_as_written(title, content):
    assert _normalize_prompt_fields(title, content) == (title, content)


@pytest.mark.parametrize(("title", "content"), ORDINARY_PROMPTS)
def test_a_checked_prompt_comes_back_as_written(title, content):
    assert _sanitize_output(title) == title
    assert _sanitize_output(content) == content


@pytest.mark.parametrize(
    "content",
    ["on" * 24_000, "<script>" * 6_000, "<" + "a" * 49_000],
    ids=["on-run", "script-run", "unclosed-tag"],
)
def test_the_inputs_that_used_to_backtrack_pass_through(content):
    """The shapes CodeQL named. Against the old patterns the first took ~15 s."""

    assert _normalize_prompt_fields("t", content) == ("t", content)
    assert _sanitize_output(content) == content


def test_the_length_limits_still_hold():
    with pytest.raises(Exception, match="200"):
        _normalize_prompt_fields("x" * 201, "content")
    with pytest.raises(Exception, match="50000"):
        _normalize_prompt_fields("title", "x" * 50_001)


@pytest.mark.parametrize(("title", "content"), [("", "c"), ("t", "   ")])
def test_blank_fields_are_still_refused(title, content):
    with pytest.raises(Exception, match="required"):
        _normalize_prompt_fields(title, content)
