"""The five prompt sections travel as one value, and none of them may go missing.

`synthesize_answer` took the sections as five separate parameters, which is what
carried it over the 13-parameter ceiling (`python:S107`) the moment the governed
tool block was added.  Bundling them is the fix, and it introduces a failure the
five parameters could not have: a field added to `SynthesisContexts` and never
rendered is invisible -- the caller sets it, the type checker is satisfied, and
the section simply never reaches the model.

So these tests are about the *seam*, not about the wording of any one section:
every field is discovered from the dataclass rather than listed here, so a sixth
one is covered the day it is added.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.agents.synthesizer.citations import citation_labels_from_contexts
from app.agents.synthesizer.generation import SynthesisContexts, _build_prompt_with_language

_FIELDS = tuple(field.name for field in dataclasses.fields(SynthesisContexts))


def _prompt(contexts: SynthesisContexts, *, nonce: str = "") -> str:
    return _build_prompt_with_language(
        question="年假多少天",
        detected_language="zh",
        skill_name="answer_with_citations",
        contexts=contexts,
        nonce=nonce,
    )


def test_the_bundle_has_the_five_sections_the_prompt_renders():
    assert _FIELDS == ("memory", "vector", "graph", "web", "tool")


@pytest.mark.parametrize("field_name", _FIELDS)
@pytest.mark.parametrize("nonce", ["", "abc123"], ids=["unsandboxed", "sandboxed"])
def test_every_section_reaches_the_prompt(field_name: str, nonce: str):
    """Set one field to a sentinel and require it in the rendered prompt.

    Parametrized per field rather than looped inside one assertion, so a failure
    names the section that went missing.  Both sandbox modes, because the
    builder renders the evidence sections twice -- once wrapped and once bare --
    and a section can be dropped from exactly one branch.
    """

    sentinel = f"SENTINEL-{field_name.upper()}-7f3a"
    prompt = _prompt(SynthesisContexts(**{field_name: sentinel}), nonce=nonce)

    assert sentinel in prompt


def test_an_empty_bundle_renders_no_section_headings_for_what_is_absent():
    """The tool section is omitted entirely when empty, where the four evidence
    sections render as `无`.  That asymmetry is deliberate -- an empty labelled
    heading would end the excerpt before it -- and is worth pinning so a tidying
    pass does not make them uniform."""

    prompt = _prompt(SynthesisContexts())

    assert "工具执行结果" not in prompt
    for heading in ("记忆上下文:", "向量检索上下文:", "图谱上下文:", "联网补充上下文:"):
        assert f"{heading}\n无" in prompt


def test_the_governed_tool_block_is_not_an_evidence_section():
    """`evidence_sections` is what citation labels are drawn from.  Tool output
    is governed, carries no `[E{k}]` marker, and must never mint one: a label
    with no evidence behind it is a citation pointing at nothing."""

    contexts = SynthesisContexts(vector="[E1] a", graph="[E2] b", web="[E3] c", tool="[E9] not evidence")

    assert contexts.evidence_sections == ("[E1] a", "[E2] b", "[E3] c")
    assert citation_labels_from_contexts(*contexts.evidence_sections) == frozenset({"E1", "E2", "E3"})


def test_the_bundle_is_immutable():
    """One value now travels through six functions.  If a hop could rewrite a
    section in place, the stage after it would be handed something no caller
    chose -- which is the whole hazard a shared mutable bag introduces and the
    five parameters did not have."""

    contexts = SynthesisContexts(vector="[E1] a")

    with pytest.raises(dataclasses.FrozenInstanceError):
        contexts.vector = "rewritten"  # type: ignore[misc]
