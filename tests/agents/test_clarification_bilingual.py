"""Regression tests for clarification language and non-fatal degradation.

Two defects: the question catalogue was Chinese-only in a system that promises
bilingual support, and the in-pipeline clarification node raised on
``action == "ask"`` — which it always returns there, because the pipeline calls
the clarifier without any collected context.
"""

from __future__ import annotations

from app.agents.clarification.rules import question_for


def _has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def test_chinese_question_is_the_default():
    q = question_for("rag_design", "scenario")
    assert q is not None
    assert _has_cjk(q.question)


def test_english_question_is_available():
    q = question_for("rag_design", "scenario", language="en")
    assert q is not None
    assert not _has_cjk(q.question)
    assert q.field_name == "scenario"
    assert q.options


def test_both_languages_agree_on_field_names_and_option_counts():
    catalogue = {
        "rag_design": ("scenario", "data_source", "scale", "performance_requirement"),
        "document_comparison": ("doc_ids", "comparison_aspect", "output_format"),
        "environment_setup": ("target_component",),
        "troubleshooting": ("error_details",),
        "usage_guidance": ("usage_target",),
        "optimization": ("optimization_target",),
    }
    for intent, fields in catalogue.items():
        for field_name in fields:
            zh = question_for(intent, field_name)
            en = question_for(intent, field_name, language="en")
            assert zh is not None, f"{intent}.{field_name}"
            assert en is not None, f"{intent}.{field_name}"
            assert zh.field_name == en.field_name
            assert len(zh.options) == len(en.options)
            assert zh.allow_custom_input == en.allow_custom_input


def test_claude_code_style_question_options_and_recommended_prefix():
    catalogue = {
        "rag_design": ("scenario", "data_source", "scale", "performance_requirement"),
        "document_comparison": ("comparison_aspect", "output_format"),
        "environment_setup": ("target_component",),
        "troubleshooting": ("error_details",),
        "usage_guidance": ("usage_target",),
        "optimization": ("optimization_target",),
    }
    for intent, fields in catalogue.items():
        for field_name in fields:
            zh = question_for(intent, field_name)
            en = question_for(intent, field_name, language="en")
            assert zh is not None and zh.options, f"{intent}.{field_name} zh"
            assert en is not None and en.options, f"{intent}.{field_name} en"

            # Check Claude Code / Codex recommended prefix convention
            assert zh.options[0].startswith("(推荐)"), (
                f"{intent}.{field_name} ZH first option should start with '(推荐)'"
            )
            assert en.options[0].startswith("(Recommended)"), (
                f"{intent}.{field_name} EN first option should start with '(Recommended)'"
            )

            # Check detailed, rich explanations rather than bare keywords
            for opt in zh.options:
                assert len(opt) >= 10, f"ZH option too short: {opt}"
            for opt in en.options:
                assert len(opt) >= 15, f"EN option too short: {opt}"


def test_vague_queries_require_clarification():
    from app.agents.clarification.rules import assess_completeness, missing_fields

    cases = [
        ("怎么配置？", "environment_setup", ("target_component",)),
        ("报错了怎么办？", "troubleshooting", ("error_details",)),
        ("如何使用？", "usage_guidance", ("usage_target",)),
        ("怎么优化？", "optimization", ("optimization_target",)),
        ("总结这份季度报告", "complete", ()),
    ]
    for question, expected_intent, expected_missing in cases:
        assessment = assess_completeness(question)
        assert assessment.intent == expected_intent, f"{question} -> {assessment.intent}"
        assert missing_fields(assessment, {}) == expected_missing, f"{question} -> missing"


def test_unknown_language_falls_back_to_chinese():
    q = question_for("rag_design", "scenario", language="fr")
    assert q is not None
    assert _has_cjk(q.question)


def test_unknown_field_still_returns_none():
    assert question_for("rag_design", "nope") is None
    assert question_for("nope", "scenario", language="en") is None


# `test_clarification_node_does_not_raise_on_ask` stood here. It read the source
# of the pipeline's clarification node to check its `ask` branch degraded rather
# than raising. That node is gone -- it could never do anything, because a graph
# node has no collected context to give the clarifier -- so the property is now
# structural rather than asserted:
# tests/orchestration/test_clarification_is_not_a_pipeline_stage.py.
