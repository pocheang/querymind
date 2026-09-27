"""The answer as the validation checks should read it: claims, not markup.

Every check in the cascade used to read the raw answer, and a model writes
Markdown. Replayed over thirty real answers on 2026-09-27, 25 were rejected
and none approved, and most of what rejected them was the markup:

- "Number 2.0 ... 7.0 not found in sources" -- the ordinals of a numbered
  list and of numbered headings (`#### 2. **最小权限授予**`), 26 of 95 flagged
  numbers from list ordinals alone and most of the rest from headings;
- "Entities not in source: Affected Spring Framework Versions" -- a heading
  in Title Case read as a proper noun;
- `[E1]`, `[T1]`, `[1]` read as the number 1.

This is one view, used by every check that compares answer text with the
sources, so they cannot disagree about what the answer claims. It never feeds
anything a reader sees: the answer itself is untouched.

Line by line and without regular expressions that could backtrack: the input
is model output, and a validation check must not be the slow part of a request.
"""

from __future__ import annotations

import re

_CITATION_MARKER_RE = re.compile(r"\[[ET]?\d+\]")
"""An internal ``[E1]`` / ``[T1]`` or reader-facing ``[1]`` citation marker."""

_EMPHASIS = ("**", "__")
_BULLETS = ("- ", "* ", "+ ", "• ")
_MAX_LABEL_WORDS = 6
_MAX_LABEL_CHARS = 40


def claims_text(answer: str) -> str:
    """The answer's claims, with headings, list markup and citation markers removed."""

    lines = []
    for raw_line in _CITATION_MARKER_RE.sub(" ", answer or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or _is_rule(line):
            # Headings are section labels, not claims; a rule is decoration.
            continue
        line = _strip_list_marker(line)
        for mark in _EMPHASIS:
            line = line.replace(mark, "")
        line = _strip_label(line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def _is_rule(line: str) -> bool:
    return len(line) >= 3 and set(line) <= {"-", "*", "_", " "}


def _strip_list_marker(line: str) -> str:
    """`- item`, `* item`, `1. item`, `2) item` -> `item`."""

    for bullet in _BULLETS:
        if line.startswith(bullet):
            return line[len(bullet) :].lstrip()
    digits = 0
    while digits < len(line) and digits < 3 and line[digits].isdigit():
        digits += 1
    if 0 < digits < len(line) - 1 and line[digits] in ".)" and line[digits + 1] in " \t":
        return line[digits + 2 :].lstrip()
    return line


def _strip_label(line: str) -> str:
    """`Application Isolation: implement ...` -> `implement ...`.

    A short run of words ending in a colon at the start of a line is a label
    the model gave the item -- usually in Title Case, which the entity check
    reads as a name. Long runs are kept: past a few words it is a sentence.
    """

    for colon in (":", "："):
        head, sep, tail = line.partition(colon)
        if not sep or not tail.strip() or tail.startswith("//"):
            # No label, nothing after it, or a URL's scheme.
            continue
        is_label = (
            0 < len(head.split()) <= _MAX_LABEL_WORDS
            # A Chinese clause has no spaces to count, so bound the characters too.
            and len(head) <= _MAX_LABEL_CHARS
            and any(ch.isalpha() for ch in head)
            # `ran at 12:00` is a time, not a label: a digit on either side of
            # the colon means the colon is part of a value.
            and not head.rstrip()[-1:].isdigit()
            and not tail.lstrip()[:1].isdigit()
        )
        if is_label:
            return tail.strip()
    return line


__all__ = ["claims_text"]
