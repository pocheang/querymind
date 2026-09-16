"""extract_reasoning_block: the post-hoc, complete-text half of the
visible-reasoning feature (ReasoningStreamSplitter, in
test_thinking_stream.py, does the same split live). This is the
authoritative one -- it runs on the full generated text regardless of
whether streaming was active, and its output is what gets persisted.
"""

from __future__ import annotations

from app.agents.synthesizer.citations import extract_reasoning_block


def test_a_tagged_block_is_extracted_and_removed_from_the_answer():
    text = "<think>\nStep 1: analyze the question\nStep 2: check evidence\n</think>\nThe real answer [E1]."

    reasoning, answer = extract_reasoning_block(text)

    assert reasoning == "Step 1: analyze the question\nStep 2: check evidence"
    assert answer == "The real answer [E1]."
    assert "<think>" not in answer
    assert "</think>" not in answer


def test_no_tag_falls_back_to_the_silent_heuristic_stripper():
    """`use_reasoning=False` never selects the tagged prompt, so this is the
    ordinary path for almost every answer -- and the one case
    `strip_chain_of_thought_preamble` already exists to guard (same fixture
    shape as test_chain_of_thought_leak.py's LEAKED_ANSWER, inlined here to
    avoid a cross-file import -- `tests/agents` is not a package)."""
    leaked_answer = """Chain-of-Thought Analysis:

1. Query Analysis: The user is asking for a concept explanation of "retrieval augmented generation."

2. Context Assessment:
   - E1 provides a clear definition

4. Answer Structure: Definition -> Key characteristics

Answer:
Retrieval-augmented generation (RAG) is a technique that enables large language models to retrieve and incorporate information from external sources [1]."""

    reasoning, answer = extract_reasoning_block(leaked_answer)

    assert reasoning is None
    assert "Chain-of-Thought Analysis" not in answer
    assert answer.startswith("Retrieval-augmented generation")


def test_an_ordinary_untagged_answer_passes_through_unchanged():
    text = "BM25 is a lexical ranking function [E1]."

    reasoning, answer = extract_reasoning_block(text)

    assert reasoning is None
    assert answer == text


def test_an_empty_think_block_reports_no_reasoning():
    """<think></think> with nothing inside is not genuine reasoning content --
    reporting it as such would show an empty, pointless panel."""
    text = "<think></think>\nJust the answer."

    reasoning, answer = extract_reasoning_block(text)

    assert reasoning is None
    assert answer == "Just the answer."


def test_a_think_tag_that_never_closes_falls_back_to_the_heuristic():
    """Truncated generation, or a model that opens the tag and then abandons
    it. No reliable inner boundary exists to extract from, so this is treated
    the same as no tag at all -- the heuristic stripper is a second, weaker
    line of defense, not a second way to recover reasoning text."""
    text = "<think>\nQuery Analysis: what is being asked\nAnswer Structure: unclear, generation cut off"

    reasoning, answer = extract_reasoning_block(text)

    assert reasoning is None
    # Nothing to safely cut at (no "Answer:" line), so the heuristic leaves
    # it untouched rather than guessing -- same rule strip_chain_of_thought_preamble
    # already applies to a genuinely stuck scaffold.
    assert answer == text


def test_a_think_block_appearing_mid_answer_is_left_alone():
    """Anchored to the start on purpose: a <think> the model writes as part of
    discussing the concept of reasoning, mid-answer, is not this system's own
    scaffold and must not be treated as one."""
    text = "The model wrote <think>a nested example</think> as part of its answer."

    reasoning, answer = extract_reasoning_block(text)

    assert reasoning is None
    assert answer == text


def test_reasoning_is_stripped_of_surrounding_whitespace():
    text = "<think>\n\n   plenty of padding   \n\n</think>\n\nanswer text"

    reasoning, answer = extract_reasoning_block(text)

    assert reasoning == "plenty of padding"
    assert answer == "answer text"
