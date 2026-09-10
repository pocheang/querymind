from __future__ import annotations

import re
from typing import Any

_NEGATIVE = {"not", "no", "never", "cannot", "can't", "without", "未", "不", "没有", "无法"}

# Maximum pairs to check (early exit optimization for large citation sets)
_MAX_PAIRS_TO_CHECK = 100


def _record_pair(
    i: int,
    j: int,
    texts: list[str],
    tokenized_texts: list[set[str]],
    has_neg_cache: list[bool],
    pairs: int,
    conflict_hits: int,
    snippets: list[str],
) -> tuple[int, bool]:
    """Score one (i, j) pair, appending a snippet in place when it is a new
    example. Returns the updated `conflict_hits` and whether the current row
    (this `i`'s remaining `j`s) has seen strong enough evidence to stop early --
    the caller's `for j` loop, not the whole scan, since a later `i` may still
    be worth checking."""
    max_snippets = 3
    if tokenized_texts[i].isdisjoint(tokenized_texts[j]):
        return conflict_hits, False
    if has_neg_cache[i] == has_neg_cache[j]:
        return conflict_hits, False
    conflict_hits += 1
    if len(snippets) < max_snippets:
        snippets.append(f"{_trim(texts[i])} <> {_trim(texts[j])}")
        return conflict_hits, False
    return conflict_hits, conflict_hits >= 5 and (conflict_hits / pairs) >= 0.3


def _collect_conflicts(texts: list[str]) -> tuple[int, int, list[str]]:
    # OPTIMIZATION: Pre-tokenize all texts once (avoids re-tokenization in _shared_keywords)
    tokenized_texts = [_tokenize(text.lower()) for text in texts]
    has_neg_cache = [_has_neg(text.lower()) for text in texts]

    pairs = 0
    conflict_hits = 0
    snippets: list[str] = []

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            # OPTIMIZATION: Early exit if we've checked enough pairs
            if pairs >= _MAX_PAIRS_TO_CHECK:
                break
            pairs += 1
            conflict_hits, row_done = _record_pair(
                i, j, texts, tokenized_texts, has_neg_cache, pairs, conflict_hits, snippets
            )
            if row_done:
                break

        # Break outer loop too if we hit the limit
        if pairs >= _MAX_PAIRS_TO_CHECK:
            break

    return pairs, conflict_hits, snippets


def detect_evidence_conflict(citations: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [
        str((c or {}).get("content", "") or "").strip()
        for c in citations
        if str((c or {}).get("content", "") or "").strip()
    ]
    if len(texts) < 2:
        return {"conflict": False, "score": 0.0, "pairs_checked": 0}

    pairs, conflict_hits, snippets = _collect_conflicts(texts)

    score = (conflict_hits / pairs) if pairs else 0.0
    return {
        "conflict": score >= 0.25 and conflict_hits > 0,
        "score": round(score, 4),
        "pairs_checked": pairs,
        "conflict_hits": conflict_hits,
        "examples": snippets,
    }


def _has_neg(text: str) -> bool:
    for token in _NEGATIVE:
        if token in text:
            return True
    return False


def _tokenize(text: str) -> set[str]:
    """Tokenize text and filter out common stop words (used for caching)."""
    tokens = set(re.findall(r"[a-zA-Z_]{4,}", text))
    # Filter stop words
    return {x for x in tokens if x not in {"this", "that", "with", "from", "have", "will", "should"}}


def _trim(text: str, limit: int = 64) -> str:
    s = " ".join(text.split())
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."
