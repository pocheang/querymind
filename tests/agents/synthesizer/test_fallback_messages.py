"""What a reader is told when no answer could be written.

One string served thirteen call sites until 2026-09-09 -- a synthesis timeout,
an LLM error, an empty completion, and *having no evidence to answer from*. It
said "抱歉，当前答案生成服务暂时不可用". Two things were wrong with that:

* The most common cause on an installation with an empty corpus is the last one,
  and it sends the reader to an administrator when what they need is a document
  or a web search. `synthesize_candidate` already tagged that branch
  `no_evidence`; the message it returned simply did not say so.
* It was Chinese only, in an application whose reason for existing is that it
  works in both languages -- and `detected_language` was in scope at every one
  of those sites.

Found by asking a question on an empty corpus and reading what came back.
"""

from __future__ import annotations

import pytest

from app.agents.synthesizer.generation import (
    FALLBACK_REASONS,
    is_synthesis_fallback,
    synthesis_fallback,
)


def test_no_evidence_does_not_blame_the_answer_service():
    """The distinction the whole change exists for."""

    no_evidence = synthesis_fallback("no_evidence", "zh")
    failed = synthesis_fallback("generation_failed", "zh")

    assert no_evidence != failed
    assert "服务" not in no_evidence, "a retrieval miss must not be reported as an outage"
    assert "资料" in no_evidence
    # And it says what the reader can actually do about it.
    assert "上传" in no_evidence


@pytest.mark.parametrize("reason", FALLBACK_REASONS)
def test_every_reason_speaks_both_languages(reason: str):
    """A bilingual application must not answer an English question in Chinese."""

    chinese = synthesis_fallback(reason, "zh")
    english = synthesis_fallback(reason, "en")

    assert chinese
    assert english
    assert chinese != english
    assert english.isascii(), f"{reason} English message is not English: {english!r}"
    assert not chinese.isascii(), f"{reason} Chinese message looks like English: {chinese!r}"


def test_an_unknown_reason_still_answers():
    """This runs when something has already gone wrong; it must not add a second
    failure by raising on a reason nobody registered."""

    assert synthesis_fallback("something-nobody-registered", "en") == synthesis_fallback("generation_failed", "en")


def test_an_unknown_language_falls_back_to_chinese():
    assert synthesis_fallback("no_evidence", "") == synthesis_fallback("no_evidence", "zh")
    assert synthesis_fallback("no_evidence", "fr") == synthesis_fallback("no_evidence", "zh")


def test_the_state_is_detected_structurally_not_by_one_string():
    """`synthesize_candidate` tags `generation_fallback` off this.

    It used to compare against the single constant, which stops being correct the
    moment the message varies by cause or language -- and inferring a state from
    user-facing text is fragile even when it happens to work.
    """

    for reason in FALLBACK_REASONS:
        for language in ("zh", "en"):
            assert is_synthesis_fallback(synthesis_fallback(reason, language))

    assert not is_synthesis_fallback("反向传播是一种梯度下降算法[1]。")
    assert not is_synthesis_fallback("")


def test_the_no_evidence_branch_uses_the_no_evidence_message():
    """Pinned at the call site, because the branch knowing the cause and the
    message stating it are different things -- and for a long time only the
    first was true."""

    import inspect

    from app.agents.synthesizer import service

    source = inspect.getsource(service.SynthesizerAgentService.synthesize_candidate)

    assert 'synthesis_fallback("no_evidence"' in source
    assert "SYNTHESIS_FALLBACK_MESSAGE" not in source


def test_a_model_written_reference_list_is_removed_before_the_real_one():
    """One answer must not carry the same heading twice.

    `output_filter` appends the authoritative list -- it is the only thing that
    knows which citations survived DLP and what number each evidence item got --
    so a section the model wrote for itself is redundant by construction. A real
    answer on 2026-09-09 ended with both, the model's copy listing `<URL_7>`,
    the outbound-redaction token it had been shown.
    """

    from app.agents.synthesizer.citations import strip_model_reference_list

    answer = "反向传播是一种梯度下降算法[E1]。\n\n参考来源\n\n[1] https://a.example\n[2] https://b.example\n"

    assert strip_model_reference_list(answer) == "反向传播是一种梯度下降算法[E1]。"
    # English heading too, and the bulleted form the pipeline itself emits.
    assert strip_model_reference_list("Answer.\n\nReferences\n- [1] https://a.example\n") == "Answer."


def test_the_stripper_keeps_anything_that_is_not_a_bare_list():
    """Losing an answer's last paragraph to a tidy-up is far worse than one
    repeated heading, so this only fires on a trailing block of bracketed
    entries."""

    from app.agents.synthesizer.citations import strip_model_reference_list

    prose = "答案正文。\n\n参考来源\n\n这些来源需要人工核对。"
    mention = "正文提到参考来源的重要性。结论如此。"
    plain = "答案正文。"

    for text in (prose, mention, plain):
        assert strip_model_reference_list(text) == text


def test_the_output_filter_strips_before_it_appends():
    """A stripper nothing calls leaves the duplicate heading on screen."""

    import inspect

    from app.orchestration.langgraph import nodes

    source = inspect.getsource(nodes)
    strip_at = source.index("numbered = strip_model_reference_list(numbered)")
    append_at = source.index('final_text = f"{numbered}')

    assert strip_at < append_at, "the model's list is stripped after the real one is appended"
