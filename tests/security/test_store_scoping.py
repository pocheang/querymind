"""The keyword and graph stores must scope the same way the vector store does.

Phase 1 made the vector store fail closed on a missing scope. BM25 and the Neo4j
fallback templates are the other two ways a question reaches stored content, and
both had softer contracts:

- `bm25_search(allowed_sources=None)` searched the whole corpus, and every scoped
  query re-filtered the corpus and rebuilt the index from scratch.
- `get_simpler_query` chose its template on the truthiness of `allowed_sources`,
  so an *empty* scope -- "this caller may read nothing" -- selected the
  unfiltered template. The three Neo4jClient entry points return early on an
  empty list so nothing reached it that way today, but the function's own
  contract was the wrong way round.

See P1-4 and P1-5 in docs/superpowers/plans/2026-08-29-user-data-isolation.md.
"""

from __future__ import annotations

import json

import pytest

from app.core.config import get_settings
from app.graph.knowledge.cypher_validation import get_simpler_query
from app.retrievers import bm25_retriever

ALICE_DOC = "/uploads/alice/notes.pdf"
BOB_DOC = "/uploads/bob/salary.pdf"


def _chunks(owner: str, source: str) -> list[dict]:
    """One matching chunk plus filler.

    The filler is load-bearing: BM25 IDF goes negative when a term appears in
    every document of the index, and bm25_search drops non-positive scores, so a
    single-chunk scope scores nothing at all. That is inherent to BM25 on a tiny
    corpus and predates the per-scope index cache -- see
    test_a_single_chunk_scope_scores_nothing.
    """
    return [
        {
            "id": f"chunk-{owner}-hit",
            "text": f"{owner} quarterly compensation review",
            "metadata": {"source": source, "owner_user_id": owner},
        },
        *(
            {
                "id": f"chunk-{owner}-{topic}",
                "text": f"{owner} {topic} document",
                "metadata": {"source": source, "owner_user_id": owner},
            }
            for topic in ("travel", "onboarding", "roadmap")
        ),
    ]


_CORPUS = [*_chunks("alice", ALICE_DOC), *_chunks("bob", BOB_DOC)]


@pytest.fixture
def use_corpus(monkeypatch, tmp_path):
    """Write `rows` as the corpus file and point the settings at it.

    A real file rather than a patched reader, because the cache is keyed on the
    file's stat signature and that is part of what is under test.
    """

    target = tmp_path / "chunks.jsonl"
    monkeypatch.setenv("CORPUS_STORE_PATH", str(target))
    get_settings.cache_clear()

    def write(rows: list[dict]) -> None:
        target.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        bm25_retriever.reset_bm25_cache()

    bm25_retriever.clear_bm25_indexes()
    try:
        yield write
    finally:
        get_settings.cache_clear()
        bm25_retriever.clear_bm25_indexes()


@pytest.fixture
def corpus(use_corpus) -> list[dict]:
    use_corpus(_CORPUS)
    return _CORPUS


@pytest.fixture
def builds(monkeypatch) -> list[int]:
    """One entry per scoped index actually built."""

    calls: list[int] = []
    real = bm25_retriever._build_index

    def counting(records, use_chinese_tokenizer):
        calls.append(len(records))
        return real(records, use_chinese_tokenizer)

    monkeypatch.setattr(bm25_retriever, "_build_index", counting)
    return calls


def _sources(rows) -> set[str]:
    return {row["metadata"]["source"] for row in rows}


# --- BM25 ------------------------------------------------------------------


def test_bm25_returns_only_the_scoped_records(corpus):
    rows = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert _sources(rows) == {ALICE_DOC}


def test_bm25_refuses_a_missing_scope(corpus):
    with pytest.raises(ValueError, match="allowed_sources is required"):
        bm25_retriever.bm25_search("compensation", k=6)


def test_bm25_returns_nothing_for_an_empty_scope(corpus):
    assert bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[]) == []


def test_bm25_does_not_serve_one_scope_from_another_scopes_index(corpus):
    """The per-scope index cache must key on the scope, not just the query."""
    first = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])
    second = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[BOB_DOC])

    assert _sources(first) == {ALICE_DOC}
    assert _sources(second) == {BOB_DOC}


def test_bm25_reuses_a_scopes_index_across_queries(corpus, builds):
    """A user asking twice must not rebuild their index twice."""
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])
    bm25_retriever.bm25_search("roadmap", k=6, allowed_sources=[ALICE_DOC])

    assert len(builds) == 1


def test_bm25_scope_order_does_not_split_the_cache(corpus, builds):
    """The same source set in a different order is the same scope."""
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC, BOB_DOC])
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[BOB_DOC, ALICE_DOC])

    assert len(builds) == 1


def test_no_index_is_built_over_sources_outside_the_scope(corpus, builds):
    """There is no global index any more (PERF-02): the only index built for
    Alice's question holds Alice's four chunks, not the whole corpus."""
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert builds == [4]


def test_another_users_ingest_does_not_rebuild_this_scope(use_corpus, builds):
    """PERF-02: one user's upload used to clear every user's index."""
    use_corpus(_CORPUS)
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    use_corpus([*_CORPUS, {"id": "bob-new", "text": "bob new upload", "metadata": {"source": BOB_DOC}}])
    rows = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert [row["id"] for row in rows] == ["chunk-alice-hit"]
    assert len(builds) == 1


def test_a_change_to_a_scoped_source_rebuilds_that_scope(use_corpus, builds):
    """The other half: reuse must never serve a scope its own stale chunks."""
    use_corpus(_CORPUS)
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    changed = [{**row, "text": "alice relocated budget"} if row["id"] == "chunk-alice-hit" else row for row in _CORPUS]
    use_corpus(changed)

    assert bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC]) == []
    assert [row["id"] for row in bm25_retriever.bm25_search("relocated", k=6, allowed_sources=[ALICE_DOC])] == [
        "chunk-alice-hit"
    ]
    assert len(builds) == 2


def test_a_metadata_only_change_rebuilds_the_scope(use_corpus):
    """Results carry metadata, so a visibility relabel must reach them too."""
    use_corpus(_CORPUS)
    bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    use_corpus([{**row, "metadata": {**row["metadata"], "visibility": "public"}} for row in _CORPUS])
    rows = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert rows[0]["metadata"]["visibility"] == "public"


def test_a_single_chunk_scope_still_matches(corpus, use_corpus):
    """A one-document scope must still return its document.

    BM25 IDF goes negative for a term present in most documents, so in a
    one-document index *every* term scores below zero. The old inclusion test
    kept whatever scored above zero -- only a proxy for "contains a query term",
    and one that inverts here -- so a user whose whole corpus was a single chunk
    got no BM25 hits at all. Matching is now term overlap; BM25 only ranks.
    """
    use_corpus([{"id": "solo", "text": "alice quarterly compensation review", "metadata": {"source": ALICE_DOC}}])

    rows = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert [row["id"] for row in rows] == ["solo"]


def test_a_document_without_any_query_term_is_not_returned(corpus):
    """The half that must not regress: matching is still matching, not everything."""
    rows = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert [row["id"] for row in rows] == ["chunk-alice-hit"]


def test_a_query_with_no_overlap_returns_nothing(corpus):
    assert bm25_retriever.bm25_search("helicopter", k=6, allowed_sources=[ALICE_DOC]) == []


def test_ranking_still_orders_by_bm25(corpus, use_corpus):
    """Term overlap decides membership; BM25 decides order."""
    use_corpus(
        [
            {
                "id": "weak",
                "text": "compensation " + " ".join(f"filler{i}" for i in range(60)),
                "metadata": {"source": ALICE_DOC},
            },
            {"id": "strong", "text": "compensation compensation compensation", "metadata": {"source": ALICE_DOC}},
            {"id": "other", "text": "unrelated travel policy", "metadata": {"source": ALICE_DOC}},
        ]
    )

    rows = bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    assert [row["id"] for row in rows] == ["strong", "weak"]


def test_k_counts_matching_documents_not_candidates(corpus, use_corpus):
    """Truncation happens after matching, so k returns k results when k exist."""
    use_corpus(
        [{"id": f"hit-{i}", "text": f"compensation review {i}", "metadata": {"source": ALICE_DOC}} for i in range(5)]
        + [{"id": f"miss-{i}", "text": f"travel policy {i}", "metadata": {"source": ALICE_DOC}} for i in range(5)]
    )

    rows = bm25_retriever.bm25_search("compensation", k=3, allowed_sources=[ALICE_DOC])

    assert len(rows) == 3
    assert all(row["id"].startswith("hit-") for row in rows)


def test_resetting_the_cache_picks_up_a_reindex(corpus, use_corpus):
    """Ingest calls reset_bm25_cache; the scoped indexes must go with it."""
    assert bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC])

    use_corpus([])

    assert bm25_retriever.bm25_search("compensation", k=6, allowed_sources=[ALICE_DOC]) == []


# --- Neo4j fallback templates ----------------------------------------------


@pytest.mark.parametrize("query_type", ["entity_paths_2hop", "entity_neighbors"])
def test_an_empty_scope_still_selects_a_filtered_template(query_type):
    """Empty means "read nothing", which is not the same as "no filter"."""
    fallback = get_simpler_query(query_type, [])

    assert fallback is not None
    assert "$allowed_sources" in fallback


@pytest.mark.parametrize("query_type", ["entity_paths_2hop", "entity_neighbors"])
def test_a_scoped_query_keeps_its_filter_when_it_degrades(query_type):
    fallback = get_simpler_query(query_type, [ALICE_DOC])

    assert fallback is not None
    assert "$allowed_sources" in fallback


@pytest.mark.parametrize("query_type", ["entity_paths_2hop", "entity_neighbors"])
def test_only_an_absent_scope_degrades_to_an_unfiltered_template(query_type):
    """Documents the one remaining case, which the primary query shares."""
    fallback = get_simpler_query(query_type, None)

    assert fallback is not None
    assert "$allowed_sources" not in fallback


@pytest.mark.parametrize("method", ["search_entities", "entity_neighbors", "entity_paths_2hop"])
def test_the_graph_entry_points_short_circuit_an_empty_scope(method):
    """The upstream guard that made the template bug unreachable; keep it that way."""
    import inspect

    from app.graph.knowledge.client import Neo4jClient

    source = inspect.getsource(getattr(Neo4jClient, method))
    assert "if not allowed_sources:" in source
    assert "return []" in source


# --- retrieval cache keying -------------------------------------------------


@pytest.fixture
def recorded_cache_keys(monkeypatch) -> list[str]:
    """Capture the retrieval cache key without running real retrieval."""
    from app.retrievers.hybrid import retriever

    keys: list[str] = []
    monkeypatch.setattr(retriever, "cache_lookup", lambda key, settings, span: keys.append(key) or None)
    monkeypatch.setattr(retriever, "cache_store", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        retriever,
        "_collect_candidates_for_current_module",
        lambda *args, **kwargs: ([], {}),
    )
    monkeypatch.setattr(retriever, "rerank_with_diagnostics", lambda query, fused, top_n: ([], {}))
    monkeypatch.setattr(retriever, "_expand_to_parent_context", list)
    return keys


def _search(owner_user: str | None, recorded: list[str]) -> str:
    from app.retrievers.hybrid.retriever import hybrid_search_with_diagnostics
    from app.retrievers.stores.vector import OwnerScope

    owner = None if owner_user is None else OwnerScope(user_id=owner_user, tenant_id=owner_user)
    hybrid_search_with_diagnostics("compensation", allowed_sources=[ALICE_DOC], owner=owner)
    return recorded[-1]


def test_two_owners_do_not_share_a_retrieval_cache_entry(recorded_cache_keys):
    """The owner narrows what the store returns, so it must key the cache.

    Without it, two callers holding the same source list but different
    identities collide -- and after P1-4 that is no longer a distinction without
    a difference.
    """
    assert _search("alice", recorded_cache_keys) != _search("bob", recorded_cache_keys)


def test_an_ownerless_search_keys_separately_from_an_owned_one(recorded_cache_keys):
    assert _search(None, recorded_cache_keys) != _search("alice", recorded_cache_keys)


def test_the_same_owner_reuses_its_cache_entry(recorded_cache_keys):
    """Guards against keying on something that varies per call.

    The two owner ids are distinct objects with equal content, because the key
    has to be derived from what the owner *is* and not from the object carrying
    it -- an `OwnerScope` is built fresh per request, so identity would make
    every request a miss while still passing a same-literal comparison.
    """
    literal = "alice"
    rebuilt = "".join(["ali", "ce"])  # joined, not concatenated: literals get folded

    assert rebuilt is not literal, "the interpreter interned these; the test would prove less"
    assert _search(literal, recorded_cache_keys) == _search(rebuilt, recorded_cache_keys)
