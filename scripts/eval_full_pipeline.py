"""Measure retrieval with the parts that decide precision switched on.

    python scripts/eval_full_pipeline.py            # refuses unless the stack is real
    python scripts/eval_full_pipeline.py --explain  # report the stack and stop

`scripts/eval_retrieval.py` measures BM25 alone. That is the half that runs on a
fresh checkout, and it is what CI asserts -- but it is also the half that cannot
be much better than it already is. Ordering the top five is the reranker's job
and finding a paraphrase is the embedding model's, and this is the entry point
that measures those.

**It refuses rather than degrading, and that is the whole point of the file.**
Both models are opened with `local_files_only=True`, so a machine without them
gets a lexical reranker and deterministic hash embeddings -- and answers every
query, and prints a number, and nothing anywhere says the number describes the
fallback. The same is true of an empty Chroma directory, which is an ordinary
state on the request path and here means the vector half contributed nothing.
So the run ends at the preflight with exit code 2 and no numbers at all, rather
than publishing something that cannot be compared with the run it will be
compared with.

Deliberately not in CI, and not because it is slow: a CI runner has neither
model, so it would refuse on every commit, and a check that always refuses gets
deleted or switched off. Same reasoning as `npm run screenshots` -- a local
before/after tool.

Exit codes: 0 measured (or refused nothing under --explain), 2 refused before
measuring. Deliberately no failing code for a query that ranked somewhere
unexpected, which is what `eval_retrieval.py` returns 1 for: the ranks recorded
in `KNOWN_LEXICAL_LIMITS` are what BM25 alone does, and a fused, reranked run
disagreeing with them is the result this command exists to produce, not a
failure. It prints the comparison instead.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass

REFUSED = 2


def _print_stack() -> None:
    """Every component and its status, including the ones this run does not require.

    Printing only the required two would leave an operator guessing whether a
    refusal was about the stack as a whole. The required ones are marked, so it
    is also visible that an unavailable OCR is not what stopped the run.
    """

    from app.evaluation.preflight import ACCEPTABLE_STATUS, REQUIRED_COMPONENTS
    from app.services.models.effective import effective_model_configuration

    print("model stack:")
    for component in effective_model_configuration():
        required = "required" if component.component in REQUIRED_COMPONENTS else "not required here"
        ok = "ok " if component.status == ACCEPTABLE_STATUS else "!! "
        print(f"  {ok}{component.component:<15} {component.status:<12} {component.configured}  [{required}]")


def _prepare():
    """Resolve the inputs and point BM25 at them, exactly as `eval_retrieval` does.

    Returns the corpus path, the query path, the queries, the sources and the
    scope -- the scope in particular has to be the one the measurement uses, or
    the store probe below asks about a different set of documents.
    """

    from app.core.config import get_settings
    from app.evaluation.retrieval_eval import (
        CORPUS_PATHS,
        QUERY_PATHS,
        eval_scope,
        load_corpus_sources,
        load_queries,
        resolve,
    )
    from app.retrievers.bm25_retriever import reset_bm25_cache

    corpus = resolve(CORPUS_PATHS)
    queries_path = resolve(QUERY_PATHS)
    os.environ["CORPUS_STORE_PATH"] = str(corpus)
    get_settings.cache_clear()
    reset_bm25_cache()

    queries = load_queries(queries_path)
    sources = load_corpus_sources(corpus)
    return corpus, queries_path, queries, sources, eval_scope(sources)


def _collect_refusals(scope, queries) -> list:
    """Models first, then the store.

    The order is load-bearing: building an embedding out of hash buckets and
    searching with it would report a populated store as empty, or an empty one as
    fine, depending on what was indexed and with which model.
    """

    from app.evaluation.preflight import model_refusals, vector_store_refusal

    refusals = model_refusals()
    if refusals:
        return refusals
    store = vector_store_refusal(scope, queries[0].query if queries else "probe")
    return [store] if store is not None else []


def _report(score, corpus, queries_path, queries, sources) -> None:
    from app.evaluation.retrieval_eval import FULL_PIPELINE_SOURCES

    print(f"corpus : {corpus} ({len(sources)} sources)")
    print(f"queries: {queries_path} ({len(queries)} queries)")
    print(f"sources: {', '.join(FULL_PIPELINE_SOURCES)} + cross-encoder rerank")
    print()
    print(f"{'query':<8} {'rank':>4}  question")
    for query in queries:
        rank = score.ranks.get(query.id, 0)
        print(f"{query.id:<8} {rank if rank else '-':>4}  {query.query}")
    print()
    print(f"recall@5 : {score.recall_at_5:.4f}")
    print(f"MRR      : {score.mrr:.4f}")
    print(f"nDCG@5   : {score.ndcg_at_5:.4f}")
    ceiling = score.precision_ceiling_at_5
    reached = " (at the ceiling)" if abs(score.precision_at_5 - ceiling) < 1e-9 else ""
    print(f"P@5      : {score.precision_at_5:.4f}  ceiling {ceiling:.4f}{reached}")


def _report_against_lexical(score, queries) -> None:
    """What the reranker and the vector half bought, against the BM25 baseline.

    Reported as a comparison and never as an assertion: `expected_ranks` records
    what BM25 alone does, and this command has no business claiming a fused,
    reranked run should reproduce a lexical one. A difference here is the
    interesting result, not a failure.
    """

    from app.evaluation.retrieval_eval import expected_ranks

    lexical = expected_ranks([query.id for query in queries])
    moved = {qid: (lexical[qid], score.ranks.get(qid, 0)) for qid in lexical if score.ranks.get(qid, 0) != lexical[qid]}
    if not moved:
        return
    print()
    print("against the BM25-only baseline (KNOWN_LEXICAL_LIMITS):")
    for qid, (was, now) in sorted(moved.items()):
        direction = "better" if now and (was == 0 or now < was) else "worse"
        print(f"  {qid}: {was or 'not retrieved'} -> {now or 'not retrieved'}  ({direction})")


async def _run(explain: bool) -> int:
    from app.evaluation.preflight import render_refusals
    from app.evaluation.retrieval_eval import FULL_PIPELINE_SOURCES, measure

    corpus, queries_path, queries, sources, scope = _prepare()

    _print_stack()
    print()

    refusals = _collect_refusals(scope, queries)
    if refusals:
        print(render_refusals(refusals))
        return REFUSED

    if explain:
        print("Preflight clean -- this stack would measure what the report names.")
        print("Re-run without --explain to measure.")
        return 0

    score = await measure(queries, scope, sources=FULL_PIPELINE_SOURCES, rerank=True)
    _report(score, corpus, queries_path, queries, sources)
    _report_against_lexical(score, queries)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--explain",
        action="store_true",
        help="run the preflight and report, without measuring",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.explain))


if __name__ == "__main__":
    raise SystemExit(main())
