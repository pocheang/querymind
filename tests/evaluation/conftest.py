"""Shared fixtures for the retrieval-evaluation suites.

`eval_corpus` lives here rather than in one test module because three files now
measure against the tracked corpus, and a second copy of it would be a second
answer to "which corpus did that number come from" -- the failure this
repository records for the audit-action vocabulary, met in a fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings

TRACKED_CORPUS = Path("config/eval/retrieval_corpus.jsonl")


@pytest.fixture
def eval_corpus(monkeypatch):
    """Point BM25 at the tracked corpus and clear its cache.

    `_load_bm25` is `lru_cache(maxsize=1)`, so without the reset this would
    silently measure whatever corpus the developer's own `data/chunks` holds --
    a green number about the wrong documents.
    """

    from app.retrievers.bm25_retriever import reset_bm25_cache

    monkeypatch.setenv("CORPUS_STORE_PATH", str(TRACKED_CORPUS))
    get_settings.cache_clear()
    reset_bm25_cache()
    try:
        yield
    finally:
        get_settings.cache_clear()
        reset_bm25_cache()
