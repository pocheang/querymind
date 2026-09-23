"""Whether a routing keyword occurs in a question, as a word rather than a substring.

Three classifiers route on keyword lists -- the domain agent registry, the rule
classifier in `app/services/agent_classifier.py`, and the fallback behind the LLM
intent classifier -- and all three tested `keyword in text`. For a Latin keyword
that is a substring test, so `"ai"` matched "email" and "maintenance", `"rag"`
matched "storage", `"soc"` matched "social", and `"log"` matched "blog" and
"login". The registry's answer was then returned at 0.95 confidence, ahead of the
LLM classifier.

A keyword with any non-ASCII character keeps the substring test: Chinese has no
word boundaries to require, and `"sql注入"` should match however it is embedded.

A Latin keyword must not be flanked by a Latin letter or a digit. That is not
`\\b`: in Python's Unicode mode a CJK character is a word character, so `\\bllm\\b`
fails on "用llm做" -- exactly the mixed-script way this application's users write.
"""

from __future__ import annotations

import re
from functools import lru_cache

_BOUNDARY_CLASS = "a-z0-9"


@lru_cache(maxsize=1024)
def _latin_keyword_pattern(keyword: str) -> re.Pattern[str]:
    return re.compile(f"(?<![{_BOUNDARY_CLASS}]){re.escape(keyword)}(?![{_BOUNDARY_CLASS}])")


def contains_keyword(text: str, keyword: str) -> bool:
    """True when `keyword` occurs in `text` as a keyword rather than inside a word.

    Case-insensitive: both sides are lower-cased here, so callers need not agree
    on who does it.
    """

    needle = (keyword or "").strip().lower()
    if not needle:
        return False
    haystack = (text or "").lower()
    if not needle.isascii():
        return needle in haystack
    return _latin_keyword_pattern(needle).search(haystack) is not None


def count_keywords(text: str, keywords: tuple[str, ...] | list[str]) -> int:
    """How many of `keywords` occur in `text`, each counted once."""

    return sum(1 for keyword in keywords if contains_keyword(text, keyword))


def any_keyword(text: str, keywords: tuple[str, ...] | list[str]) -> bool:
    """Whether any of `keywords` occurs in `text`."""

    return any(contains_keyword(text, keyword) for keyword in keywords)


__all__ = ["any_keyword", "contains_keyword", "count_keywords"]
