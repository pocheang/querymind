"""A model that takes "think through" literally writes the thinking out too.

`COT_REASONING_PROMPT` (app/agents/synthesizer/templates.py) asks the model to
work through four numbered steps -- Query Analysis, Context Assessment,
Citation Planning, Answer Structure -- before answering. Nothing told it that
analysis had to stay out of the reply, so a real configured model (observed on
2026-09-15, in a browser, against a live backend) answered with the entire
scaffold as the visible message, self-labelled "Chain-of-Thought Analysis",
with the actual answer starting only after a line reading just "Answer:". The
reader saw the machinery that produced the answer instead of the answer -- the
same class of failure this codebase already has a stripper for
(`strip_model_reference_list`, for a model's own hallucinated reference list).

Two changes, same as that one: the prompt now says the analysis must not
appear in the reply, and `strip_chain_of_thought_preamble` is a safety net for
a model that writes it out anyway.
"""

from __future__ import annotations

import inspect

from app.agents.synthesizer.citations import strip_chain_of_thought_preamble
from app.agents.synthesizer.templates import COT_REASONING_PROMPT

LEAKED_ANSWER = """Chain-of-Thought Analysis:

1. Query Analysis: The user is asking for a concept explanation of "retrieval augmented generation."

2. Context Assessment:
   - E1 provides a clear definition
   - Missing: technical implementation details

3. Citation Planning:
   - Core definition -> [1]

4. Answer Structure: Definition -> Key characteristics -> Use cases

Answer:
Retrieval-augmented generation (RAG) is a technique that enables large language models to retrieve and incorporate information from external sources [1]."""


def test_the_scaffold_is_removed_and_only_the_real_answer_remains():
    assert strip_chain_of_thought_preamble(LEAKED_ANSWER) == (
        "Retrieval-augmented generation (RAG) is a technique that enables large "
        "language models to retrieve and incorporate information from external "
        "sources [1]."
    )


def test_a_bold_or_chinese_answer_marker_is_recognised_too():
    bold = "Query Analysis: ...\nAnswer Structure: ...\n**Answer:**\nThe real answer."
    chinese = "Query Analysis: ...\nAnswer Structure: ...\n答案：\n真正的回答。"

    assert strip_chain_of_thought_preamble(bold) == "The real answer."
    assert strip_chain_of_thought_preamble(chinese) == "真正的回答。"


def test_an_ordinary_answer_is_left_untouched():
    """Neither step name present -- nothing to strip."""

    ordinary = "Retrieval-augmented generation (RAG) is a technique [1]."

    assert strip_chain_of_thought_preamble(ordinary) == ordinary


def test_a_partial_scaffold_with_no_answer_marker_is_left_alone():
    """Guessing a cut point without a marker would risk taking the only
    content the model produced -- the same reasoning `strip_model_reference_list`
    already applies to a reference section with no clear end."""

    stuck = (
        "Query Analysis: what is being asked...\n\n"
        "Answer Structure: definition, then use cases...\n\n"
        "Complete information gap: no relevant evidence was retrieved."
    )

    assert strip_chain_of_thought_preamble(stuck) == stuck


def test_mentioning_one_step_name_in_passing_is_not_enough_to_trigger_it():
    """Both signal phrases must appear -- a real answer that happens to
    discuss "query analysis" as a topic must not be touched."""

    prose = "Query analysis is a subtopic of information retrieval [1]."

    assert strip_chain_of_thought_preamble(prose) == prose


def test_the_prompt_now_tells_the_model_to_keep_it_out_of_the_reply():
    """The stripper is a safety net; the prompt is the actual fix."""

    assert "does not belong" in COT_REASONING_PROMPT or "None of this analysis belongs" in COT_REASONING_PROMPT


def test_generation_strips_before_self_review_and_citation_normalization_see_it():
    """A stripper nothing calls, or called too late, leaves the scaffold in
    front of the stages that are supposed to review or cite the real answer.

    `strip_chain_of_thought_preamble` itself is now called from inside
    `extract_reasoning_block` (app/agents/synthesizer/citations.py), which
    generation.py calls in its place -- same ordering guarantee, one more
    layer of indirection since it also has to split out a `<think>` block
    when one is present."""

    from app.agents.synthesizer import generation

    source = inspect.getsource(generation)
    strip_at = source.index("reasoning, initial = extract_reasoning_block(initial)")
    final_answer_at = source.index("final_answer = initial")
    normalize_at = source.index("final_answer = normalize_answer_citations(")

    assert strip_at < final_answer_at < normalize_at
