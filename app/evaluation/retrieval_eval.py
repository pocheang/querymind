"""Measure retrieval quality on a corpus that ships with the repository.

Why this exists at all: CLAUDE.md has claimed P@5 > 0.85 for a long time and
nothing measured it. `POST /api/evaluation/run` reads `data/evaluation/*.json`,
and `data/` is gitignored -- so on every checkout where nobody hand-placed a file
the endpoint returned 404. A target with no measurement behind it is a number,
not a claim.

Two decisions worth knowing before changing this module.

**It runs through `KnowledgeOrchestrator`, not through the evaluation
baselines.** The baselines in `app/evaluation/baselines/api_retriever.py` call
`similarity_search` and `hybrid_search_with_diagnostics` directly: they never
touch the orchestrator, the adapters, or `reciprocal_rank_fuse`, so they cannot
observe a change to any of them. Going through the orchestrator costs one more
import and measures the path the chat request actually takes -- including
`_flatten`, RRF, deduplication and `mask_evidence`.

**BM25 only, so it needs no model.** `read_corpus_records` reads a plain JSONL
file at `corpus_store_path`; nothing here needs an embedding model, Chroma,
Neo4j or an LLM, which is what lets it run in CI and on a fresh checkout. The
vector and hybrid paths deliberately stay manual: `_load_cross_encoder` is built
with `local_files_only=True`, so a CI run without the model downloaded would
silently fall back to `lexical_rerank` and publish a number measuring the
fallback rather than the reranker. A green metric measuring the wrong thing is
worse than no metric.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.domain.knowledge import AccessScope, KnowledgeSourcePlan, KnowledgeStrategy
from app.evaluation.metrics import complete_at_k, ndcg_at_k, precision_ceiling_at_k, recall_at_k
from app.evaluation.models import TestQuery
from app.knowledge.orchestrator import KnowledgeOrchestrator, discard_trace
from app.services.security.access_scope import DEFAULT_CONTEXT_FIELDS

# Deployment-specific override first, then the set that ships with the repo --
# the same order and the same reason as `_BENCHMARK_QUERY_PATHS` in
# app/services/runtime/runtime_ops.py. Only the tracked default makes this
# runnable on a fresh checkout.
CORPUS_PATHS = (
    Path("data/eval/retrieval_corpus.jsonl"),
    Path("config/eval/retrieval_corpus.jsonl"),
)
QUERY_PATHS = (
    Path("data/eval/retrieval_queries.json"),
    Path("config/eval/retrieval_queries.json"),
)

EVAL_TENANT = "eval-tenant"
EVAL_USER = "eval-user"

# Every query on the shipped set ranks its gold document first except these.
# Defined here rather than in the test because `scripts/eval_retrieval.py` needs
# the same answer: a command whose exit code disagrees with the suite about what
# "correct" means teaches people to ignore one of them, and until 2026-09-05 it
# did -- `make eval-retrieval` returned 1 on a state the suite asserts.
#
# An entry is a *limit that has been reasoned about*, not a tolerance. Ranks are
# compared to this map exactly, so an improvement fails as loudly as a
# regression: reaching rank 1 here means something got better and this entry
# should go.
KNOWN_LEXICAL_LIMITS: dict[str, int] = {
    # Both entries are the same defect, and the corpus could not express it until
    # it gained distractors -- documents that share the query's vocabulary and do
    # not answer it. Measured, the three candidates for each query come back
    # adjacent (RRF 1/61, 1/62, 1/63), so this is an ordering failure by a hair,
    # not a retrieval failure: recall@5 stays 1.0000.
    #
    # The mechanism is BM25 length normalisation. The gold document is the long
    # one, because actually answering a question takes more words than mentioning
    # its subject; a short document sharing the query term is charged less for
    # its length and wins. The query's remaining tokens do not rescue it: "天" is
    # in most of the 假 family, so its IDF is near nothing.
    #
    # `q-07` is the control that proves it is the mechanism rather than a story.
    # It is `q-13` plus "可以结转吗", and "结转" is in one document in the corpus --
    # high IDF, and the gold jumps back to rank 1. One discriminating rare term
    # beats the length penalty; "年假" alone does not.
    #
    # This is the boundary of lexical retrieval, and the remedy is the half this
    # harness deliberately switches off: vector fusion puts a paraphrase of the
    # question next to the document that answers it, and the cross-encoder
    # reorders the top few. `scripts/eval_full_pipeline.py` is what measures that,
    # and it refuses to run rather than degrade -- see its module docstring.
    #
    # "年假有多少天" -- the gold (十五天带薪年假) is outranked by a document about
    # cashing out unused 年假 on departure and one about applying for it.
    "q-13": 3,
    # "产假多少天" -- outranked by 陪产假 (paternity leave: "产假" is a substring of
    # it, so bigrams cannot separate them in this direction; asking about 陪产假
    # *is* fixed by them, because "陪产" then discriminates) and by a document
    # about who pays wages during 产假.
    "q-15": 3,
}


CROSSDOC_QUERY_PATH = Path("config/eval/retrieval_queries_crossdoc.json")

# Cross-document queries BM25 alone cannot assemble: at least one required
# document is outside the top five, so the question is not answerable at all
# rather than answered badly. Same shape and same rule as KNOWN_LEXICAL_LIMITS --
# each entry is a limit that has been reasoned about, compared exactly, so an
# improvement fails as loudly as a regression.
#
# **Both are the defect KNOWN_LEXICAL_LIMITS already records, measured where it
# costs an answer.** On the main set, BM25 length normalisation pushed the long
# gold document to rank 3 and recall@5 stayed 1.0000 -- it looked like an
# ordering blemish. Here the same documents fall out of the window entirely:
#
#   x-08 (年假没休完又要离职) loses nianjia.md, the long one carrying the
#        entitlement and the carry-over rule, to the three short 年假 documents
#        that mention the word without answering anything. This is q-13 exactly,
#        one rank worse, and one rank worse happens to be the difference between
#        a thin answer and no answer.
#   x-06 loses backup_policy.md to backup_restore_drill.md, which carries both
#        "backup" and "restore" where the gold carries only the first -- and the
#        remaining four slots go to documents sharing nothing but common words,
#        so the gold is not merely outranked, it is below noise.
#
# The remedy is the same one and it is not lexical: vector fusion puts a
# paraphrase next to the document that answers it. `scripts/eval_full_pipeline.py`
# is what would measure whether it does.
KNOWN_INCOMPLETE_CROSSDOC: dict[str, tuple[str, ...]] = {
    "x-06": ("eval://corpus/backup_policy.md",),
    "x-08": ("eval://corpus/nianjia.md",),
}


def expected_ranks(query_ids: tuple[str, ...] | list[str]) -> dict[str, int]:
    """Rank 1 for every query, except the limits recorded above."""

    return {query_id: KNOWN_LEXICAL_LIMITS.get(query_id, 1) for query_id in query_ids}


def resolve(paths: tuple[Path, ...]) -> Path:
    """First existing path wins; a genuinely missing set is an error, not a zero."""

    for candidate in paths:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"no retrieval evaluation file found at any of: {', '.join(str(p) for p in paths)}")


def load_corpus_sources(path: Path | None = None) -> tuple[str, ...]:
    target = path or resolve(CORPUS_PATHS)
    sources: list[str] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        source = str((json.loads(line).get("metadata") or {}).get("source", "") or "")
        if source:
            sources.append(source)
    return tuple(dict.fromkeys(sources))


def load_queries(path: Path | None = None) -> tuple[TestQuery, ...]:
    target = path or resolve(QUERY_PATHS)
    payload = json.loads(target.read_text(encoding="utf-8"))
    return tuple(TestQuery(**row) for row in payload.get("queries", []))


def eval_scope(sources: tuple[str, ...]) -> AccessScope:
    """The scope the corpus rows declare.

    `mask_evidence` runs inside `_retrieve_source`, so the rows' `tenant_id`,
    `owner_user_id` and `visibility` have to match what is asked for here. When
    they do not, every item is dropped and the metric reads 0.00 for a reason
    that has nothing to do with retrieval -- which is why
    `test_a_mismatched_scope_returns_nothing` exists.
    """

    return AccessScope(
        tenant_id=EVAL_TENANT,
        user_id=EVAL_USER,
        role="viewer",
        allowed_sources=frozenset(sources),
        allowed_fields=DEFAULT_CONTEXT_FIELDS,
    )


@dataclass(frozen=True)
class RetrievalScore:
    """Per-query outcome plus the aggregates, so a failure can name the query.

    **`precision_at_5` is bounded by the annotations, and `precision_ceiling_at_5`
    says by how much.** Every query in the shipped set has exactly one relevant
    document, so at most one of five retrieved items can be relevant and P@5
    cannot exceed 0.2 however good retrieval is -- 0.2 there is a *perfect*
    score, not a poor one. The ceiling is computed from the judgements rather
    than written down, so the two can never be compared by mistake.

    On a single-gold corpus P@5 is `recall_at_5 / 5` exactly and carries no
    information the recall does not, which is why `recall_at_5`, `mrr` and
    `ndcg_at_5` are what the report leads with.

    The three new fields carry defaults so that a caller constructing a score by
    hand -- the tests do -- is not forced to supply an aggregate it does not
    measure.
    """

    ranks: dict[str, int]  # query id -> 1-based rank of the best relevant source, 0 if absent
    precision_at_5: float
    mrr: float
    recall_at_5: float = 0.0
    ndcg_at_5: float = 0.0
    precision_ceiling_at_5: float = 0.0
    # The fraction of queries whose every relevant document made the top five.
    # Equal to `recall_at_5` on a single-gold set and the metric that matters on
    # a cross-document one, where half the evidence produces a confident wrong
    # answer rather than half an answer.
    complete_at_5: float = 0.0
    # query id -> the required documents that were NOT in the top k, for the
    # queries that have any. A count of incomplete queries is a number nobody can
    # act on; the missing document is the whole diagnosis, and both entries on
    # the shipped cross-document set turned out to name the same defect.
    missing: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def reciprocal_ranks(self) -> dict[str, float]:
        return {query_id: (1.0 / rank if rank else 0.0) for query_id, rank in self.ranks.items()}


# The BM25-only strategy this module has always measured, and the full one
# `scripts/eval_full_pipeline.py` measures once its preflight is satisfied.
# Named here rather than in the scripts so there is one answer to "what did that
# number measure", and so the difference between the two is one line to read.
BM25_ONLY_SOURCES: tuple[str, ...] = ("bm25",)
FULL_PIPELINE_SOURCES: tuple[str, ...] = ("vector", "bm25")


async def measure(
    queries: tuple[TestQuery, ...],
    scope: AccessScope,
    *,
    top_k: int = 5,
    sources: tuple[str, ...] = BM25_ONLY_SOURCES,
    rerank: bool = False,
) -> RetrievalScore:
    """Run each query through the real orchestrator.

    The defaults are the BM25-only measurement: no embedding model, no Chroma,
    no reranker, so it runs on a fresh checkout and is what CI asserts.

    `sources` and `rerank` exist for the full-pipeline harness, which may only
    pass `rerank=True` **after** `app.evaluation.preflight` has established that
    the cross-encoder is really loaded. Turning it on with the model absent does
    not raise: it degrades to `lexical_rerank` and measures that instead, which
    is the whole reason the preflight exists. Query rewriting stays off in both
    -- an LLM in the loop makes the measurement non-deterministic, and this
    corpus is asserted rank by rank.
    """

    orchestrator = KnowledgeOrchestrator()
    ranks: dict[str, int] = {}
    hits_at_5 = 0.0
    recall_total = 0.0
    ndcg_total = 0.0
    ceiling_total = 0.0
    complete_total = 0.0
    missing: dict[str, tuple[str, ...]] = {}
    for query in queries:
        strategy = KnowledgeStrategy(
            sources=tuple(
                KnowledgeSourcePlan(
                    source=source,
                    queries=(query.query,),
                    top_k=top_k,
                    timeout_ms=10_000,
                )
                for source in sources
            ),
            # Rewriting stays off in every form of this measurement: it can reach
            # an LLM, and a metric asserted per query cannot be non-deterministic.
            rewrite=False,
            rerank=rerank,
            rerank_top_n=top_k if rerank else None,
            rationale="offline retrieval evaluation",
        )
        context = await orchestrator.retrieve(strategy, scope, discard_trace)
        retrieved = [item.source for item in context.evidence][:top_k]
        graded = query.graded_relevance()
        # A grade of 0 is "judged and not relevant", so it must not count as gold
        # here any more than it counts toward recall inside the metrics.
        gold = {source for source, grade in graded.items() if grade > 0}
        ranks[query.id] = next((index for index, source in enumerate(retrieved, start=1) if source in gold), 0)
        hits_at_5 += len([source for source in retrieved if source in gold]) / top_k
        recall_total += recall_at_k(retrieved, graded, top_k)
        ndcg_total += ndcg_at_k(retrieved, graded, top_k)
        ceiling_total += precision_ceiling_at_k(graded, top_k)
        complete_total += complete_at_k(retrieved, graded, top_k)
        absent = tuple(sorted(source for source in gold if source not in retrieved))
        if absent:
            missing[query.id] = absent

    total = max(1, len(queries))
    return RetrievalScore(
        ranks=ranks,
        precision_at_5=hits_at_5 / total,
        mrr=sum(1.0 / rank for rank in ranks.values() if rank) / total,
        recall_at_5=recall_total / total,
        ndcg_at_5=ndcg_total / total,
        precision_ceiling_at_5=ceiling_total / total,
        complete_at_5=complete_total / total,
        missing=missing,
    )


__all__ = [
    "BM25_ONLY_SOURCES",
    "CORPUS_PATHS",
    "CROSSDOC_QUERY_PATH",
    "EVAL_TENANT",
    "EVAL_USER",
    "FULL_PIPELINE_SOURCES",
    "KNOWN_INCOMPLETE_CROSSDOC",
    "KNOWN_LEXICAL_LIMITS",
    "QUERY_PATHS",
    "RetrievalScore",
    "eval_scope",
    "expected_ranks",
    "load_corpus_sources",
    "load_queries",
    "measure",
    "resolve",
]
