"""A retrieval metric that runs on a fresh checkout, and can fail.

CLAUDE.md has claimed P@5 > 0.85 for a long time with nothing measuring it: the
one endpoint that could reads `data/evaluation/*.json`, `data/` is gitignored, so
on every checkout where nobody hand-placed a file it returned 404. This suite
ships a corpus and a query set instead, and measures them through the real
`KnowledgeOrchestrator`.

The most important test here is `test_a_mismatched_scope_returns_nothing`.
`mask_evidence` runs inside `_retrieve_source`, so a corpus whose ownership
metadata does not match the scope drops every item and scores 0.00 for a reason
that has nothing to do with retrieval quality -- indistinguishable from a broken
retriever. Proving the metric can fail is the precondition for trusting it when
it passes, the same lesson as the sensitive-content gate.

Scores are pinned exactly rather than ratcheted on an aggregate: BM25 over a
fixed JSONL file is deterministic, and with twelve queries an aggregate moves in
jumps of about 0.08, so a ratchet on it would either never fire or fire on a
corpus edit. Per-query reciprocal ranks name the offender instead.
"""

from __future__ import annotations

import json
import subprocess
from math import log2
from pathlib import Path

import pytest

from app.evaluation.retrieval_eval import (
    CORPUS_PATHS,
    QUERY_PATHS,
    eval_scope,
    expected_ranks,
    load_corpus_sources,
    load_queries,
    measure,
    resolve,
)
from app.retrievers.bm25_retriever import tokenize_chinese_aware

TRACKED_CORPUS = Path("config/eval/retrieval_corpus.jsonl")
TRACKED_QUERIES = Path("config/eval/retrieval_queries.json")


# --- the set ships and is internally consistent -----------------------------


def test_the_tracked_default_exists_and_is_the_fallback_path():
    assert TRACKED_CORPUS.exists()
    assert TRACKED_QUERIES.exists()
    assert CORPUS_PATHS[-1] == TRACKED_CORPUS
    assert QUERY_PATHS[-1] == TRACKED_QUERIES


def test_the_shipped_set_is_actually_tracked_by_git():
    """Existing on disk is not the same as shipping, and this file nearly proved it.

    `.gitignore` carries a blanket `*.jsonl` for logs, which silently swallowed
    `config/eval/retrieval_corpus.jsonl` -- so the corpus would have been absent
    on every fresh clone while every test here passed on the machine that wrote
    it. That is precisely the defect this whole suite exists to fix, one level up.

    `git check-ignore` rather than `git ls-files`, so this also fails for a file
    that was force-added once and would go invisible on its next edit.
    """

    for path in (TRACKED_CORPUS, TRACKED_QUERIES):
        result = subprocess.run(
            ["git", "check-ignore", str(path)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        # Exit code 1 means "not ignored", which is what we need.
        assert result.returncode == 1, f"{path} is gitignored and would not survive a clone"


def test_a_deployment_override_wins_over_the_tracked_default():
    """Same precedence as `_BENCHMARK_QUERY_PATHS`: `data/` first."""

    assert CORPUS_PATHS[0].parts[0] == "data"
    assert QUERY_PATHS[0].parts[0] == "data"


def test_a_genuinely_missing_set_raises_rather_than_scoring_zero():
    with pytest.raises(FileNotFoundError):
        resolve((Path("nowhere/absent-corpus.jsonl"),))


def test_every_expected_doc_exists_in_the_shipped_corpus():
    """The single most valuable test here.

    An `expected_docs` entry naming a source the corpus does not contain scores
    0.0 forever and looks exactly like a retrieval failure. `expected_docs` holds
    *source identifiers*, not document ids -- the retriever reports
    `metadata["source"]`.
    """

    sources = set(load_corpus_sources(TRACKED_CORPUS))
    missing = {
        expected
        for query in load_queries(TRACKED_QUERIES)
        for expected in query.expected_docs
        if expected not in sources
    }

    assert missing == set()


def test_the_query_set_is_bilingual():
    """An English-only evaluation corpus measures the wrong system in an
    application whose reason for existing is that it works in Chinese."""

    queries = load_queries(TRACKED_QUERIES)
    chinese = [query for query in queries if any("一" <= ch <= "鿿" for ch in query.query)]

    assert len(chinese) >= 4
    assert len(queries) - len(chinese) >= 4


def test_the_corpus_declares_the_ownership_the_scope_asks_for():
    """The precondition for the metric meaning anything -- see the module
    docstring on `mask_evidence`."""

    from app.evaluation.retrieval_eval import EVAL_TENANT, EVAL_USER

    rows = [json.loads(line) for line in TRACKED_CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert rows
    for row in rows:
        metadata = row["metadata"]
        assert metadata["tenant_id"] == EVAL_TENANT
        assert metadata["owner_user_id"] == EVAL_USER


# --- the measurement --------------------------------------------------------


# Queries whose gold document BM25 alone cannot rank first, with the reason and
# the rank it does achieve. A ratchet, not an allowlist: the rank is pinned
# exactly, so an improvement fails this test just as a regression does, and the
# entry has to be revisited either way.
#
# These are not defects in the retriever. They are the boundary of lexical
# matching, which is why the production pipeline fuses BM25 with vector search --
# something this BM25-only harness deliberately does not do.


@pytest.mark.asyncio
async def test_every_query_puts_its_gold_document_first(eval_corpus: None):
    """A hand-authored micro-corpus should be unambiguous, so rank 1 everywhere.

    Deterministic input, deterministic retriever: this is pinned rather than
    ratcheted. The per-query map is asserted so a failure names the query.
    """

    queries = load_queries(TRACKED_QUERIES)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    expected = expected_ranks([query.id for query in queries])

    assert score.ranks == expected, f"MRR={score.mrr:.4f} P@5={score.precision_at_5:.4f} ranks={score.ranks}"


@pytest.mark.asyncio
async def test_a_word_jieba_does_not_know_is_still_retrievable(eval_corpus: None):
    """The assertion that would have caught the tokenizer.

    jieba splits "年假" into two single characters, and the tokenizer dropped
    every single-character token -- so the word vanished from the query and from
    the document alike and could never match. Not ranked badly: absent.

    **This asserted `rank == 1` until the corpus gained distractors**, and that
    conflated two claims the distractors then separated: that "年假" tokenizes at
    all, and that BM25 puts the document answering it first. The second is false
    today and is recorded as `q-13` in `KNOWN_LEXICAL_LIMITS`; the first is what
    this test is for, and it is still true. Asserting a rank here would make a
    test named for the tokenizer fail for a reason that has nothing to do with
    it -- and, worse, would have been "fixed" by relaxing it to whatever the
    ranking happens to be.

    So it asserts retrievability, and it asserts the tokenizer directly on the
    function the index is built with, which no corpus change can dilute.
    """

    assert "年假" in tokenize_chinese_aware("年假有多少天"), "the bigram that makes the word matchable at all"

    queries = [query for query in load_queries(TRACKED_QUERIES) if query.id == "q-13"]
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    # Retrieved, not absent -- 0 is what the broken tokenizer produced.
    assert score.ranks["q-13"] != 0
    assert score.recall_at_5 == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_a_mismatched_scope_returns_nothing(eval_corpus: None):
    """Prove the metric can fail before trusting it when it passes.

    A scope that authorizes no source drops every item in `mask_evidence`, and
    the score goes to zero without anything about retrieval having changed. If
    this test ever passes *and* the one above also passes with the same scope
    bug present, the metric is measuring nothing.
    """

    queries = load_queries(TRACKED_QUERIES)
    score = await measure(queries, eval_scope(("eval://corpus/not-a-real-document.md",)))

    assert score.mrr == 0.0
    assert score.precision_at_5 == 0.0
    assert set(score.ranks.values()) == {0}


@pytest.mark.asyncio
async def test_precision_at_five_is_capped_by_one_gold_document_per_query(eval_corpus: None):
    """Pins why P@5 here is 0.2 and why that is not a bad score.

    Each query names exactly one relevant document, so at most one of five
    retrieved items can be relevant. Reading this number against a P@5 > 0.85
    target quoted for a multi-gold corpus is a category error, and it is an easy
    one to make from a metrics table.
    """

    queries = load_queries(TRACKED_QUERIES)

    assert all(len(query.expected_docs) == 1 for query in queries)

    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.precision_at_5 == pytest.approx(0.2)
    # And the ceiling the judgements allow is that same 0.2, so the score is
    # perfect rather than poor. Computed from the corpus rather than written
    # down: if somebody adds a second relevant document to a query, this rises
    # and the paragraph above stops being true in the same commit.
    assert score.precision_ceiling_at_5 == pytest.approx(0.2)
    assert score.precision_at_5 == pytest.approx(score.precision_ceiling_at_5)


@pytest.mark.asyncio
async def test_the_metrics_with_range_are_what_the_corpus_is_judged_on(eval_corpus: None):
    """recall@5, MRR and nDCG@5 -- the three the report leads with.

    Pinned exactly, not as floors: BM25 over a fixed JSONL is deterministic, so
    an improvement has to fail here as loudly as a regression, the rule
    `expected_ranks` already follows.

    The closed forms are written out because they are what makes a failure
    readable: 14 queries at rank 1, `q-13` and `q-15` at rank 3 (see
    `KNOWN_LEXICAL_LIMITS`). A number alone would say the aggregate moved; these
    say which ranks would have to have moved to produce it.

    **These were 0.9688 and 0.9769 until the corpus gained distractors**, and the
    drop is the distractors working rather than retrieval regressing -- recall@5
    is still 1.0000, so nothing became unfindable; two golds lost the top slot to
    documents that share their vocabulary and do not answer the question. A
    corpus with nothing to be wrong about cannot report an ordering defect, which
    is what the previous numbers were measuring.
    """

    queries = load_queries(TRACKED_QUERIES)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.recall_at_5 == pytest.approx(1.0), "every query should find its document in the top five"
    assert score.mrr == pytest.approx((14 + 2 / 3) / 16)
    assert score.mrr == pytest.approx(0.9167, abs=1e-4)
    # Gain 1 at rank 3 is 1/log2(4) = 0.5 against an ideal DCG of 1.
    assert score.ndcg_at_5 == pytest.approx((14 + 2 / log2(4)) / 16)
    assert score.ndcg_at_5 == pytest.approx(0.9375, abs=1e-4)


@pytest.mark.asyncio
async def test_precision_at_five_is_recall_over_five_on_this_corpus(eval_corpus: None):
    """Which is why the report does not lead with it.

    The identity holds only while every query has one relevant document, so this
    also fails the day the corpus gains multi-gold judgements -- at which point
    P@5 starts carrying information and the reporting order is worth revisiting.
    """

    queries = load_queries(TRACKED_QUERIES)
    score = await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))

    assert score.precision_at_5 == pytest.approx(score.recall_at_5 / 5)


def _corpus_rows() -> list[dict]:
    return [json.loads(line) for line in TRACKED_CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_the_corpus_keeps_documents_that_exist_only_to_be_wrong():
    """Precision measures how many chances to be wrong were not taken, so a
    corpus with nothing to be wrong about measures nothing.

    Before the distractors landed, every query's gold document was the only one
    in the corpus that shared its vocabulary, and 15 of 16 queries ranked it
    first -- a result about the corpus, not about the retriever. Deleting the
    distractors would send MRR and nDCG back up, and the honest-looking repair is
    to update the aggregate assertions to match. This is what makes that a red
    test instead: the numbers are allowed to move, the reason for them is not.

    Both halves matter. A distractor that is secretly somebody's gold document
    silently removes a judgement, which is the one way this file could corrupt
    the measurement rather than harden it.
    """

    rows = _corpus_rows()
    distractors = {row["metadata"]["source"] for row in rows if row["metadata"].get("role") == "distractor"}
    gold = {source for query in load_queries(TRACKED_QUERIES) for source in query.expected_docs}

    assert len(distractors) >= 10, f"only {len(distractors)} distractors -- precision has little to discriminate"
    assert distractors & gold == set(), "a distractor is also a gold document, which deletes a judgement"
    # Bilingual for the reason the query set is: a Chinese distractor exercises
    # the CJK bigrams, and those are where this corpus's known limits live.
    assert any(
        any("一" <= ch <= "鿿" for ch in row["text"]) for row in rows if row["metadata"].get("role") == "distractor"
    )
    assert any(row["text"].isascii() for row in rows if row["metadata"].get("role") == "distractor")
