"""Print retrieval quality over the evaluation corpus.

    python scripts/eval_retrieval.py            # BM25, no model needed
    python scripts/eval_retrieval.py --vector   # adds vector + hybrid, needs BGE-M3

The BM25 form is the one `tests/evaluation/test_retrieval_metric.py` asserts on,
and it runs anywhere: `read_corpus_records` reads a plain JSONL file, so there is
no embedding model, no Chroma, no Neo4j and no LLM involved.

`--vector` is deliberately **not** in CI. `_load_cross_encoder` is built with
`local_files_only=True`, so on a machine without the reranker downloaded it
returns None and retrieval silently degrades to `lexical_rerank` -- a CI job
would publish a number measuring the lexical fallback rather than the reranker,
which is worse than publishing nothing. It also needs a populated (gitignored)
Chroma directory. Same reasoning as `npm run screenshots`: a local before/after
tool, not a gate.

Point it at your own corpus by placing `data/eval/retrieval_corpus.jsonl` and
`data/eval/retrieval_queries.json`; those win over the tracked defaults.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# The query set is bilingual and a Windows console defaults to cp1252, where
# printing a Chinese question raises UnicodeEncodeError and the run dies after
# the measurement but before the numbers.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass


def _report_metrics(score) -> None:
    """Recall, MRR, nDCG and complete@5 lead because they have range.

    P@5 is last and never alone: the shipped set has one relevant document per
    query, so it cannot exceed 0.2 however good retrieval is, and printing 0.2 by
    itself invites reading a perfect score as a failing one.
    """

    print(f"recall@5 : {score.recall_at_5:.4f}")
    print(f"MRR      : {score.mrr:.4f}")
    print(f"nDCG@5   : {score.ndcg_at_5:.4f}")
    # Every relevant document in the window, not a fraction of them. Equal to
    # recall on a single-gold set, which is why it is printed beside it rather
    # than instead of it -- the two agreeing is the evidence the set is
    # single-gold, and the two parting is the point of a cross-document one.
    print(f"complete@5: {score.complete_at_5:.4f}")
    ceiling = score.precision_ceiling_at_5
    reached = " (at the ceiling)" if abs(score.precision_at_5 - ceiling) < 1e-9 else ""
    print(f"P@5      : {score.precision_at_5:.4f}  ceiling {ceiling:.4f}{reached}")
    if ceiling < 1.0:
        print()
        print(f"P@5 cannot exceed {ceiling:.4f} on these judgements -- this corpus averages")
        print(f"{ceiling * 5:.2f} relevant documents per query. Compare recall@5 and nDCG@5 instead;")
        print("a P@5 target quoted for a multi-gold corpus is not comparable to this number.")

    # Naming the absent document is the diagnosis; the aggregate above only says
    # that something was. Empty on a single-gold set that retrieves everything.
    if score.missing:
        print()
        print("required documents outside the top five:")
        for qid, absent in sorted(score.missing.items()):
            print(f"  {qid}: {', '.join(source.rsplit('/', 1)[-1] for source in absent)}")


def _report_unexpected_ranks(score, queries) -> bool:
    """Compare against `expected_ranks` and say whether anything differed.

    Two defects used to live in the single line this replaced, and the second was
    the worse one.

    `score.mrr == 1.0` is a float equality (`python:S1244`). It happened to be
    exact -- a mean of n ones is exact in IEEE 754 -- but it expressed the intent
    badly and stops being safe the moment a query has two gold documents. What is
    required is that each query ranks its gold document where it is expected to,
    which is a comparison between integers.

    And it had been returning 1 since the CJK tokenizer landed, because MRR was
    not 1.0. A command that reports failure on a state the suite asserts is
    correct teaches people to ignore it. `expected_ranks` is the one definition of
    what this corpus should do, shared with the test module -- so an improvement
    is reported here too, rather than passing silently.
    """

    from app.evaluation.retrieval_eval import expected_ranks

    expected = expected_ranks([query.id for query in queries])
    unexpected = {qid: score.ranks.get(qid, 0) for qid, want in expected.items() if score.ranks.get(qid, 0) != want}
    if not unexpected:
        return False
    print()
    for qid, got in sorted(unexpected.items()):
        print(f"{qid}: expected rank {expected[qid]}, got {got or 'not retrieved'}")
    print("An improvement counts too -- update KNOWN_LEXICAL_LIMITS if a limit is gone.")
    return True


async def _run(use_vector: bool, queries_override: str | None) -> int:
    from app.core.config import get_settings
    from app.evaluation.retrieval_eval import (
        CORPUS_PATHS,
        QUERY_PATHS,
        eval_scope,
        load_corpus_sources,
        load_queries,
        measure,
        resolve,
    )
    from app.retrievers.bm25_retriever import reset_bm25_cache

    corpus = resolve(CORPUS_PATHS)
    # A named set measures something the tracked default does not, so the rank
    # comparison is skipped for it: `expected_ranks` records what BM25 does on the
    # MAIN set, and asserting it against another one reports a failure for every
    # query it has never seen.
    tracked = queries_override is None
    queries_path = resolve(QUERY_PATHS) if tracked else Path(queries_override)
    if not queries_path.exists():
        print(f"no such query set: {queries_path}")
        return 1

    os.environ["CORPUS_STORE_PATH"] = str(corpus)
    get_settings.cache_clear()
    reset_bm25_cache()

    queries = load_queries(queries_path)
    sources = load_corpus_sources(corpus)
    score = await measure(queries, eval_scope(sources))

    print(f"corpus : {corpus} ({len(sources)} sources)")
    print(f"queries: {queries_path} ({len(queries)} queries)")
    print()
    print(f"{'query':<8} {'rank':>4}  question")
    for query in queries:
        rank = score.ranks.get(query.id, 0)
        print(f"{query.id:<8} {rank if rank else '-':>4}  {query.query}")
    print()
    _report_metrics(score)

    if use_vector:
        print()
        print("--vector is not implemented here yet: it needs a populated Chroma")
        print("directory and a downloaded BGE-M3, neither of which this script builds.")
        print("Use `scripts/eval_full_pipeline.py`, which measures that stack and")
        print("refuses to run rather than measure a degraded one.")

    if not tracked:
        print()
        print("Ranks are not asserted for a named query set -- `expected_ranks` records")
        print("what BM25 does on the tracked default, and this is a different question.")
        return 0

    return 1 if _report_unexpected_ranks(score, queries) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector", action="store_true", help="also report the vector/hybrid baselines")
    parser.add_argument(
        "--queries",
        default=None,
        metavar="PATH",
        help="measure a named query set instead of the tracked default (ranks are not asserted for it)",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.vector, args.queries))


if __name__ == "__main__":
    raise SystemExit(main())
