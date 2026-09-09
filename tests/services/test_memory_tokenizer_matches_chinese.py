"""Long-term memory retrieval could not see Chinese, and nothing said so.

`memory_store.TOKEN_PATTERN` was written doubly escaped:

    re.compile(r"[A-Za-z0-9_\\\\-]+|[\\\\u4e00-\\\\u9fff]")

In a **raw** string `\\\\u4e00` is a literal backslash followed by `u`, so the
second alternative was a handful of ASCII punctuation rather than a CJK range.
Measured on the shipped pattern, `"我喜欢向量检索"` tokenized to `[]`.

The consequence was silent and one-sided. `retrieve_relevant_long_term_memories`
scores with BM25 over these tokens and is guarded by
`if query_tokens and any(tokenized)`, so for a Chinese question the guard failed
and it fell through to **the most recent two memories, regardless of relevance**
-- in the feature whose entire purpose is recalling what a person told it, in an
application whose reason for existing is that it works in Chinese. A Chinese
memory could not be matched by an English question either, since its own tokens
were empty.

Found by a SonarCloud `python:S5869` ("duplicates in this character class"),
which is the rule pointing at the wrong thing and being right anyway -- the
duplicate was a symptom of the doubled backslash. The same shape as the
`python:S1192` that exposed the approval-token twin, and the third time this
project has recorded a shell heredoc eating a backslash.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.services.sessions.memory_store import TOKEN_PATTERN, retrieve_relevant_long_term_memories, tokenize

APP = Path(__file__).resolve().parents[2] / "app"


def test_chinese_produces_tokens():
    """The property, stated as directly as it can be."""

    assert tokenize("我喜欢向量检索") == ["我", "喜", "欢", "向", "量", "检", "索"]


def test_the_two_scripts_tokenize_together():
    """A bilingual sentence has to yield both, not one or the other."""

    assert tokenize("我喜欢 BM25 检索") == ["我", "喜", "欢", "bm25", "检", "索"]


def test_the_pattern_holds_no_literal_backslash():
    """`\\\\u4e00` compiles fine and matches nothing anyone wants, which is why
    this failed silently rather than raising."""

    assert "\\\\" not in TOKEN_PATTERN.pattern


def test_a_chinese_question_ranks_by_relevance_rather_than_recency():
    """The observable failure, and the reason it was invisible.

    With no tokens the BM25 branch is skipped and the function still returns
    memories -- just the newest ones. A caller sees a plausible answer and no
    error, which is why this survived.
    """

    memories = [
        {"content": "用户的时区是 UTC+8", "created_at": "2020-01-01"},
        {"content": "用户喜欢向量检索胜过关键词检索", "created_at": "2020-01-02"},
        {"content": "an unrelated english note", "created_at": "2099-01-01"},
    ]

    top = retrieve_relevant_long_term_memories("我喜欢什么检索方式", memories, top_k=1)

    assert [m["content"] for m in top] == ["用户喜欢向量检索胜过关键词检索"], (
        "a Chinese question fell back to recency, which is what the broken pattern did"
    )


def test_an_english_question_still_works():
    """The half that was never broken must stay unbroken."""

    memories = [
        {"content": "the user prefers vector search over keyword search", "created_at": "2020-01-01"},
        {"content": "用户的时区是 UTC+8", "created_at": "2099-01-01"},
    ]

    top = retrieve_relevant_long_term_memories("what search does the user prefer", memories, top_k=1)

    assert top[0]["content"].startswith("the user prefers")


# --- the second defect, found by the first one's test failing -------------


def test_two_memories_are_still_ranked_by_relevance():
    """BM25 scores collapse on a small set, and `score > 0` dropped everything.

    Measured on exactly these two documents: the relevant one and the unrelated
    one both scored **0.0**, because BM25 IDF is zero for a term present in half
    the corpus. The old membership test was `score > 0`, so both were discarded
    and retrieval fell back to recency -- which the newest memory then won.

    `LONG_TERM_TOP_N` is 5, so a memory set is small by design: this was the
    normal case. CLAUDE.md records the same trap for the main BM25 path, in the
    words "do not reintroduce `score > 0` as the membership test".
    """

    memories = [
        {"content": "the user prefers vector search over keyword search", "created_at": "2020-01-01"},
        {"content": "an unrelated note about deployment", "created_at": "2099-01-01"},
    ]

    top = retrieve_relevant_long_term_memories("what search does the user prefer", memories, top_k=1)

    assert top[0]["content"].startswith("the user prefers"), "the newest memory won, so ranking never ran"


def test_a_question_sharing_nothing_still_falls_back_to_recency():
    """The fallback is not the bug and must stay: a question with no overlap
    should still get something rather than nothing."""

    memories = [
        {"content": "the user prefers vector search", "created_at": "2020-01-01"},
        {"content": "the user works in Shanghai", "created_at": "2099-01-01"},
    ]

    top = retrieve_relevant_long_term_memories("zzzz qqqq", memories, fallback_k=1)

    assert len(top) == 1
    assert top[0]["created_at"] == "2099-01-01"


# --- the recurrence guard -------------------------------------------------

_DOUBLED = re.compile(r"\\\\u[0-9a-fA-F]{4}")


def _double_escaped_literals(root: Path) -> list[str]:
    """Every string whose VALUE holds a backslash before `u`+hex.

    Checking the parsed value rather than the source text is what separates the
    bug from the twenty correct siblings: `r"[\\u4e00-\\u9fff]"` has ONE
    backslash in its value and is right, and only a doubled one is wrong.
    """

    found = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - not this test's concern
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and _DOUBLED.search(node.value):
                found.append(f"{path.relative_to(root.parent)}:{node.lineno}")
    return found


def test_no_module_double_escapes_a_unicode_range():
    """One backslash too many is a range that matches punctuation, and compiles.

    Twenty other regexes in `app/` carry `\\u4e00` correctly, so a scan of the
    source text would drown in them; this asks the parsed value instead.
    """

    assert _double_escaped_literals(APP) == []


def test_the_guard_can_fail():
    """A scan nobody has watched fail proves nothing -- this project's rule for
    the sensitive-content gate, applied to a much smaller scanner."""

    planted = 'TOKEN = re.compile(r"[\\\\u4e00-\\\\u9fff]")'
    tree = ast.parse(planted)
    values = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]

    assert any(_DOUBLED.search(v) for v in values), "the guard would not catch the bug it exists for"


@pytest.mark.parametrize("correct", [r"[一-鿿]", r"[A-Za-z0-9_\-]+|[一-鿿]{2,}"])
def test_the_guard_does_not_flag_correct_patterns(correct):
    """The direction that would make it useless: twenty false positives."""

    assert not _DOUBLED.search(correct)
