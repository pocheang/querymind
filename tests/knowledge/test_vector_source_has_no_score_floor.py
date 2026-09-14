"""The chat path's vector source applies no relevance-score floor.

A floor was added (`VECTOR_SIMILARITY_THRESHOLD`, raised to 0.30 in the same
change) and would have switched vector retrieval off on a fresh checkout.
Relevance scores are not comparable across embedding backends, and the hash
embeddings `MODEL_BACKEND=local` runs score low by construction. Measured over
the tracked `config/eval/` corpus with those embeddings and Chroma's own
relevance function: with no floor 16 of 16 queries kept a vector result and
their gold document, at 0.2 only 6, at 0.30 only 3.

RRF fuses on rank and the reranker orders what survives, so a cut here only ever
removes evidence. These tests pin that no score reaches the vector source's
decision about what to keep, and that the seam which carried one is gone.
"""

from __future__ import annotations

import asyncio
import inspect

from langchain_core.documents import Document

from app.domain.knowledge import AccessScope, KnowledgeSourcePlan
from app.knowledge import adapters
from app.retrievers.stores import vector


def _low_scoring_match() -> tuple[Document, float]:
    source = "uploads/alice/backup_policy.md"
    return (
        Document(
            page_content="Nightly database backups run at 02:00 UTC and are retained for thirty days.",
            metadata={
                "source": source,
                "document_id": "doc-1",
                "version": 1,
                "page": 1,
                "chunk_id": "chunk-1",
                "tenant_id": "alice",
                "owner_user_id": "alice",
                "visibility": "private",
            },
        ),
        # What the hash embeddings give a correct match: q-01's gold scored 0.163.
        0.05,
    )


def test_a_low_scoring_match_still_reaches_fusion(monkeypatch) -> None:
    calls: list[tuple] = []

    def fake_similarity_search(*args, **kwargs):
        calls.append((args, kwargs))
        return [_low_scoring_match()]

    monkeypatch.setattr(vector, "similarity_search", fake_similarity_search)
    scope = AccessScope(
        tenant_id="alice",
        user_id="alice",
        role="viewer",
        allowed_sources=frozenset({"uploads/alice/backup_policy.md"}),
    )
    plan = KnowledgeSourcePlan(source="vector", queries=("how long are backups kept",), top_k=4, timeout_ms=5000)

    groups = asyncio.run(adapters._retrieve_vector(plan, scope))

    assert len(groups) == 1
    assert [item.source for item in groups[0]] == ["uploads/alice/backup_policy.md"]
    # query, k, allowed_sources, require_source_filter, owner -- and nothing that
    # could be a threshold.
    ((args, kwargs),) = calls
    assert len(args) == 5 and not kwargs


def test_the_store_offers_no_score_threshold_to_reintroduce() -> None:
    """A parameter nothing passes is an invitation to wire the floor back in."""

    assert "score_threshold" not in inspect.signature(vector.similarity_search).parameters
