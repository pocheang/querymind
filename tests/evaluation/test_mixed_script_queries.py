"""A Chinese question keeps its gold document when English text rides along with it.

Measured through the real `KnowledgeOrchestrator` over the tracked corpus, the
same harness as `test_retrieval_metric.py`, so these assert what retrieval does
rather than what a tokenizer emits.

Before the fix, `tokenize_chinese_aware` segmented Chinese only when more than
20% of the characters were CJK, and tokenized everything else as English --
each Chinese character a single token, matching nothing an index of words and
bigrams holds:

- the verifier's retry appended "Retrieve additional primary evidence for: ..."
  to the question, and all ten Chinese questions lost their gold document from
  the top five (recall@5 1.0 -> 0.375);
- a five-word English lead-in cost one of the ten its document outright.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.verifier.service import _retry_query
from app.evaluation.retrieval_eval import eval_scope, load_corpus_sources, load_queries, measure

TRACKED_CORPUS = Path("config/eval/retrieval_corpus.jsonl")
TRACKED_QUERIES = Path("config/eval/retrieval_queries.json")


def _chinese_queries():
    return tuple(q for q in load_queries(TRACKED_QUERIES) if any("一" <= c <= "鿿" for c in q.query))


async def _ranks(queries) -> dict[str, int]:
    return (await measure(queries, eval_scope(load_corpus_sources(TRACKED_CORPUS)))).ranks


@pytest.mark.asyncio
async def test_english_text_beside_a_chinese_question_does_not_lose_its_document(eval_corpus: None):
    # The old retry suffix, written out, so this pins the tokenizer on its own:
    # it was enough to push every Chinese question under the threshold.
    suffixed = tuple(
        q.model_copy(update={"query": f"{q.query}\nRetrieve additional primary evidence for: missing evidence."})
        for q in _chinese_queries()
    )

    ranks = await _ranks(suffixed)

    assert all(0 < rank <= 5 for rank in ranks.values()), ranks


@pytest.mark.asyncio
async def test_an_english_lead_in_does_not_lose_the_document(eval_corpus: None):
    prefixed = tuple(q.model_copy(update={"query": f"Quick HR policy question: {q.query}"}) for q in _chinese_queries())

    ranks = await _ranks(prefixed)

    # q-15 (产假多少天) fell out of the top five before the fix.
    assert all(0 < rank <= 5 for rank in ranks.values()), ranks


@pytest.mark.asyncio
async def test_the_retry_searches_what_the_first_attempt_did_when_there_is_no_claim_text(eval_corpus: None):
    """The verifier's retry query, built by the real function.

    The validator's issue text is its own English diagnosis, none of which is in
    the answer, so none of it reaches the query -- and a retry that has nothing
    better to add searches exactly as well as the first attempt did.
    """

    queries = _chinese_queries()
    diagnostics = ("3 sentences contradicted", "Citation number 2 not in source", "answer has no attributable citation")
    retried = tuple(
        q.model_copy(update={"query": _retry_query(q.query, "年假一共十五天。", diagnostics)}) for q in queries
    )

    assert await _ranks(retried) == await _ranks(queries)
