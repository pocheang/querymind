"""An answer is as long as its evidence supports, not as long as the prompt asks.

Measured on 2026-09-27: 12 of 19 evidence-backed answers were rejected by
entailment because they said far more than their sources -- a 12-sentence
answer on an 82-token ATT&CK summary, 1.5k-6k characters on one or two search
snippets. The prompt asked for it. `ANSWER_PROMPT` said both "do not add
information not in the context" and "详尽、深入、有深度与广度的长文本展开；避免一两句话
的简短回答", plus a list of sections to cover (背景成因、技术原理、核心机制、实施步骤…);
every query-type template said "elaborate in depth; avoid one-line summaries".
With one snippet of evidence the two instructions cannot both be met, and the
length one won: the model filled the space from its own knowledge.

These tests pin the removal from every place the instruction lived, and the
rule that replaced it, so it cannot come back one template at a time.
"""

from __future__ import annotations

import pytest

from app.agents.synthesizer import templates
from app.prompts.core.canonical_agent_prompts import ANSWER_PROMPT, NO_EVIDENCE_ANSWER_PROMPT

# Phrases that demand length or coverage regardless of the evidence.
LENGTH_MANDATES = (
    "长文本",
    "避免一两句话",
    "详尽解析",
    "有深度与广度",
    "充分展开",
    "avoid one-line",
    "elaborate in depth",
    "long-form",
    "comprehensive long-text",
    "in-depth",
)

QUERY_TYPE_TEMPLATES = {
    "concept": templates.CONCEPT_TEMPLATE,
    "comparison": templates.COMPARISON_TEMPLATE,
    "relationship": templates.RELATIONSHIP_TEMPLATE,
    "procedural": templates.PROCEDURAL_TEMPLATE,
    "general": templates.GENERAL_TEMPLATE,
}

EVERY_PROMPT = {
    "ANSWER_PROMPT": ANSWER_PROMPT,
    "NO_EVIDENCE_ANSWER_PROMPT": NO_EVIDENCE_ANSWER_PROMPT,
    "COT_REASONING_PROMPT": templates.COT_REASONING_PROMPT,
    "COT_VISIBLE_REASONING_PROMPT": templates.COT_VISIBLE_REASONING_PROMPT,
    **{f"{name}_TEMPLATE": text for name, text in QUERY_TYPE_TEMPLATES.items()},
}


@pytest.mark.parametrize("name", sorted(EVERY_PROMPT))
def test_no_prompt_demands_length_the_evidence_may_not_support(name):
    text = EVERY_PROMPT[name].lower()

    present = [phrase for phrase in LENGTH_MANDATES if phrase.lower() in text]

    assert not present, f"{name} still asks for length regardless of evidence: {present}"


def test_the_answer_prompt_ties_length_to_the_evidence():
    assert "篇幅随证据" in ANSWER_PROMPT
    assert "证据只支持一两句话，就只写一两句话" in ANSWER_PROMPT
    assert "不要用自身知识补上" in ANSWER_PROMPT


def test_the_answer_prompt_still_forbids_adding_what_the_context_lacks():
    """The rule that lost to the length mandate is the one that must remain."""

    assert "不要编造、推测或添加上下文中未提供的信息" in ANSWER_PROMPT


@pytest.mark.parametrize("name", sorted(QUERY_TYPE_TEMPLATES))
def test_every_query_type_template_is_a_ceiling_not_a_quota(name):
    """The numbered parts are the most an answer may contain, not what it must.

    Checked per template because `skill_answer_template` hands the model exactly
    one of them: a template that lost the rule would lose it for its whole query
    type, silently.
    """

    template = QUERY_TYPE_TEMPLATES[name]

    assert "Scale to the evidence:" in template
    assert "not what it must contain" in template
    assert "instead of filling it from general knowledge" in template


def test_the_no_evidence_prompt_does_not_invite_an_answer_from_general_knowledge():
    assert "不要用自身知识展开回答问题本身" in NO_EVIDENCE_ANSWER_PROMPT
