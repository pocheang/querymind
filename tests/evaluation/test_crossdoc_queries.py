"""Cross-document queries, and the metric they needed.

The main set asks whether the answer is ranked first, and MRR is its metric. This
set asks whether the answer can be *assembled* from the top five, and `complete@5`
is its metric -- every required document in the window, or the question cannot be
answered at all.

The two failures pinned here are worth more than the aggregates: they are the
same BM25 length-normalisation defect `KNOWN_LEXICAL_LIMITS` already records,
measured where it costs an answer rather than a rank.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.evaluation.metrics import complete_at_k, recall_at_k
from app.evaluation.models import TestQuery as EvalQuery
from app.evaluation.retrieval_eval import (
    CROSSDOC_QUERY_PATH,
    KNOWN_INCOMPLETE_CROSSDOC,
    eval_scope,
    load_corpus_sources,
    load_queries,
    measure,
)

TRACKED_CORPUS = Path("config/eval/retrieval_corpus.jsonl")
TRACKED_QUERIES = Path("config/eval/retrieval_queries.json")


def has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def corpus_text() -> dict[str, str]:
    rows = [json.loads(line) for line in TRACKED_CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["metadata"]["source"]: row["text"] for row in rows}


# --- complete@k, the metric itself ------------------------------------------


@pytest.mark.parametrize(
    ("retrieved", "relevant", "expected"),
    [
        (["a", "b", "c"], {"a", "b"}, 1.0),
        (["a", "x", "y"], {"a", "b"}, 0.0),  # half the evidence is not half an answer
        (["a"], {"a"}, 1.0),
        ([], {"a"}, 0.0),
        (["a"], set(), 0.0),  # no judgements is not "trivially complete"
        (["a", "b"], {"a": 3, "b": 1}, 1.0),  # a grade-1 document still has to be found
        (["a", "b"], {"a": 3, "c": 0}, 1.0),  # a grade-0 one does not
    ],
)
def test_complete_at_k_requires_every_judged_relevant_document(retrieved, relevant, expected):
    assert complete_at_k(retrieved, relevant, 5) == expected


def test_complete_and_recall_agree_on_a_single_gold_corpus():
    """Why adding this metric changed no existing number.

    One relevant document is either in the window or it is not, so "all of them"
    and "the fraction of them" are the same value. They diverge only when a query
    has several -- which is exactly when the lenient reading starts hiding the
    outcome that matters.
    """

    for retrieved in (["a", "b"], ["b", "a"], ["b", "c"], []):
        assert complete_at_k(retrieved, {"a"}, 5) == recall_at_k(retrieved, {"a"}, 5)


def test_complete_is_stricter_than_recall_the_moment_a_query_needs_two():
    assert recall_at_k(["a", "x"], {"a", "b"}, 5) == pytest.approx(0.5)
    assert complete_at_k(["a", "x"], {"a", "b"}, 5) == 0.0


# --- the set is what it claims to be ----------------------------------------


def test_every_query_here_genuinely_needs_more_than_one_document():
    """The property that makes it a cross-document set rather than a second main
    set. A single-gold query in here would be measured by a metric that cannot
    say anything about it."""

    for query in load_queries(CROSSDOC_QUERY_PATH):
        required = [source for source, grade in query.graded_relevance().items() if grade > 0]
        assert len(required) >= 2, f"{query.id} needs only {len(required)} document(s)"


def test_every_source_it_names_exists_in_the_corpus():
    sources = set(load_corpus_sources(TRACKED_CORPUS))
    named = {source for query in load_queries(CROSSDOC_QUERY_PATH) for source in query.graded_relevance()}

    assert named <= sources, f"named but absent from the corpus: {sorted(named - sources)}"


def test_no_query_overlaps_the_main_set():
    """Two sets measuring different things must not share ids, or a failure names
    a query the reader will look up in the wrong file."""

    main = {query.id for query in load_queries(TRACKED_QUERIES)}
    cross = {query.id for query in load_queries(CROSSDOC_QUERY_PATH)}

    assert main & cross == set()


def test_every_query_is_answered_in_its_own_language():
    """The constraint that was found by measuring rather than by reasoning.

    The first version of `x-07` was a Chinese question whose gold documents were
    English. BM25 shares no token across the two scripts, so it returned nothing
    at all -- measured, rank '-'. That is a real limit of this corpus, but it is
    a limit on *cross-lingual matching*, and this set exists to measure
    cross-document assembly. Mixing them would drag every aggregate down for a
    reason the set does not name, which is the same argument this set makes for
    not merging itself into the main one.

    Cross-lingual retrieval needs a multilingual embedding, so it belongs in a
    set `eval_full_pipeline.py` runs. Until that set exists, this keeps a
    guaranteed zero out of a metric that is asserted exactly.
    """

    text = corpus_text()
    for query in load_queries(CROSSDOC_QUERY_PATH):
        chinese_query = has_cjk(query.query)
        for source, grade in query.graded_relevance().items():
            if grade <= 0:
                continue
            assert has_cjk(text[source]) == chinese_query, (
                f"{query.id} is {'Chinese' if chinese_query else 'English'} but {source} is not; "
                "BM25 cannot match across scripts, so this query would score zero for a reason "
                "unrelated to cross-document assembly"
            )


# --- what it measures today -------------------------------------------------


@pytest.mark.asyncio
async def test_the_cross_document_set_is_where_every_metric_has_range(eval_corpus: None):
    """The main set pins recall@5 at 1.0000 and P@5 at its ceiling, so neither
    can move. Here both can, and P@5 is **below** its ceiling for the first time
    -- which is the difference between measuring retrieval and measuring the
    annotations.

    Pinned exactly, for the reason `expected_ranks` is: BM25 over a fixed JSONL
    is deterministic, so an improvement has to fail as loudly as a regression.
    """

    queries = load_queries(CROSSDOC_QUERY_PATH)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.complete_at_5 == pytest.approx(6 / 8), "six of eight questions are assemblable"
    assert score.recall_at_5 == pytest.approx(0.8958, abs=1e-4)
    assert score.ndcg_at_5 == pytest.approx(0.8459, abs=1e-4)
    assert score.precision_ceiling_at_5 == pytest.approx(0.45)
    assert score.precision_at_5 == pytest.approx(0.4)
    assert score.precision_at_5 < score.precision_ceiling_at_5, (
        "the headline claim of this set: P@5 finally reports something retrieval can change"
    )


@pytest.mark.asyncio
async def test_the_queries_that_cannot_be_assembled_are_the_ones_on_record(eval_corpus: None):
    """`KNOWN_INCOMPLETE_CROSSDOC` names which *document* is missing, not just
    which query failed -- the missing document is the whole diagnosis, and both
    entries turn out to be the length-normalisation defect the main set already
    records, at rank 6+ instead of at rank 3.

    The first version of this test was **vacuous** and worth recording as such:
    it built the failing set by calling `complete_at_k([], ...)`, which is 0.0
    for every query, then intersected it with the very map it was checking. It
    could only ever have passed. The harness reports `missing` per query now, so
    this compares two things that were derived independently.
    """

    queries = load_queries(CROSSDOC_QUERY_PATH)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.missing == KNOWN_INCOMPLETE_CROSSDOC
    # The aggregate and the named map have to agree: a count without names is a
    # number nobody can act on, and names without the count go stale.
    assert score.complete_at_5 == pytest.approx((len(queries) - len(KNOWN_INCOMPLETE_CROSSDOC)) / len(queries))


@pytest.mark.asyncio
async def test_the_main_set_leaves_nothing_missing(eval_corpus: None):
    """The other direction, and the reason `missing` is safe to assert exactly:
    on a single-gold set where recall@5 is 1.0000 it is empty, so a non-empty
    map there would be a regression rather than a property of the set."""

    queries = load_queries(TRACKED_QUERIES)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.missing == {}
    assert score.complete_at_5 == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_missing_and_complete_never_disagree_about_a_low_graded_document(eval_corpus: None):
    """`missing` must follow exactly the rule `complete_at_k` follows: every
    document graded above zero, with no threshold of its own.

    Written because a mutation exposed a hole rather than a bug. Giving `missing`
    a `grade >= 3` threshold reddened **nothing** -- both documents absent on the
    shipped cross-document set happen to be graded 3, so the two rules agree on
    this data and would have drifted apart invisibly. The failure that would
    cause is the worst shape available: the aggregate reports a query as
    incomplete and the diagnosis beside it names nothing.

    So this drives one query whose only relevant document is graded 1 and cannot
    be retrieved, through the real harness rather than through a transcription of
    it.
    """

    unfindable = EvalQuery(
        id="synthetic-01",
        query="qqq zzz xxx",  # shares no token with any document in the corpus
        category="synthetic",
        relevance={"eval://corpus/chanjia.md": 1},
    )

    score = await measure((unfindable,), eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.complete_at_5 == 0.0
    assert score.missing == {"synthetic-01": ("eval://corpus/chanjia.md",)}


@pytest.mark.asyncio
async def test_the_aggregate_and_the_named_map_are_the_same_count(eval_corpus: None):
    """Stated over the shipped set as well, so the two cannot drift apart in the
    ordinary direction either."""

    queries = load_queries(CROSSDOC_QUERY_PATH)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.complete_at_5 == pytest.approx((len(queries) - len(score.missing)) / len(queries))
