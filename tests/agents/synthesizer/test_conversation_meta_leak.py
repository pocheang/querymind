"""A model given conversation history sometimes narrates reading it, instead
of just answering (found live on a follow-up question, 2026-09-15).

Asked "What is BM25 used for in information retrieval?" and then, in the same
session, "What are its main limitations?", the model answered:

    Based on the conversation history, the user is asking about the
    limitations of BM25 in information retrieval.

    Main Limitations of BM25:
    ...

The leading sentence is the model's own reading of the exchange, not part of
the answer -- the same class of failure `strip_chain_of_thought_preamble`
already exists for, but a different shape: it names no fixed second marker
like that prompt's "Answer:" line, because nothing asked the model to reason
step by step here. The root cause was `ANSWER_PROMPT`
(app/prompts/core/canonical_agent_prompts.py) embedding its own Chinese
four-step "think before answering" block -- 问题分析 ("what does the user
really want to know") among them -- as a near-duplicate of
`COT_REASONING_PROMPT` (app/agents/synthesizer/templates.py) sent in the same
request without that prompt's "keep this internal" guardrail. The duplicate
block is removed and both prompts now say so explicitly;
`strip_conversation_meta_preamble` is the safety net for a model that
narrates anyway.
"""

from __future__ import annotations

import inspect

from app.agents.synthesizer.citations import strip_conversation_meta_preamble
from app.prompts.core.canonical_agent_prompts import ANSWER_PROMPT, NO_EVIDENCE_ANSWER_PROMPT

LEAKED_ANSWER = """Based on the conversation history, the user is asking about the limitations of BM25 in information retrieval.

Main Limitations of BM25:

BM25 is less effective for non-Latin scripts, transliterations, and indirect descriptions [1]. The method works well when queries resemble the indexed text, such as English titles, but struggles with queries that don't match the document's vocabulary or language structure [1].

The core limitation is BM25's lexical matching dependency: it relies on exact or similar term matching between queries and documents [1]."""


def test_the_leading_meta_sentence_is_removed():
    assert strip_conversation_meta_preamble(LEAKED_ANSWER) == (
        "Main Limitations of BM25:\n\n"
        "BM25 is less effective for non-Latin scripts, transliterations, and indirect descriptions [1]. "
        "The method works well when queries resemble the indexed text, such as English titles, but "
        "struggles with queries that don't match the document's vocabulary or language structure [1].\n\n"
        "The core limitation is BM25's lexical matching dependency: it relies on exact or similar term "
        "matching between queries and documents [1]."
    )


def test_a_chinese_meta_sentence_with_no_space_is_recognised_too():
    leaked = "根据对话历史，用户问的是BM25的局限性。BM25的核心问题是只能做词面匹配。"

    assert strip_conversation_meta_preamble(leaked) == "BM25的核心问题是只能做词面匹配。"


def test_an_ordinary_answer_is_left_untouched():
    ordinary = "BM25 is a lexical ranking function used by search engines [1]."

    assert strip_conversation_meta_preamble(ordinary) == ordinary


def test_mentioning_the_conversation_alone_is_not_enough_to_trigger_it():
    """Only one of the two signals present -- a real answer that happens to
    reference the conversation in passing must not be touched."""

    prose = "As mentioned earlier in our conversation history, RAG combines retrieval with generation [1]."

    assert strip_conversation_meta_preamble(prose) == prose


def test_mentioning_the_user_asking_alone_is_not_enough_to_trigger_it():
    prose = "The user is asking a common question about vector databases [1]."

    assert strip_conversation_meta_preamble(prose) == prose


def test_a_first_sentence_with_no_terminator_is_left_alone():
    """No sentence boundary within the head -- nothing safe to cut at."""

    no_terminator = "Based on the conversation history the user is asking about BM25 limitations without a period"

    assert strip_conversation_meta_preamble(no_terminator) == no_terminator


def test_the_prompts_no_longer_embed_a_duplicate_unguarded_cot_block():
    """`ANSWER_PROMPT` used to carry its own Chinese four-step reasoning block
    -- a near-duplicate of `COT_REASONING_PROMPT` sent in the same request,
    without that prompt's instruction to keep the analysis out of the reply.
    Both prompts now say explicitly that this kind of narration must stay
    internal."""

    assert "不要在开头复述你是如何理解用户问题" in ANSWER_PROMPT
    assert "不要在开头复述你是如何理解用户问题" in NO_EVIDENCE_ANSWER_PROMPT
    assert "问题分析" not in ANSWER_PROMPT


def test_generation_strips_it_before_self_review_and_citation_normalization_see_it():
    from app.agents.synthesizer import generation

    source = inspect.getsource(generation)
    strip_at = source.index("initial = strip_conversation_meta_preamble(initial)")
    final_answer_at = source.index("final_answer = initial")
    normalize_at = source.index("final_answer = normalize_answer_citations(")

    assert strip_at < final_answer_at < normalize_at
