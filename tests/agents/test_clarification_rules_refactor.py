"""Comprehensive verification and regression test suite for refactored clarification rules."""

from __future__ import annotations

import pytest

from app.agents.clarification.rules import (
    _clean_comparison_target,
    assess_completeness,
    max_rounds_for,
    missing_fields,
    question_for,
)


def test_rag_design_detection_and_field_extraction():
    q = "如何设计一个企业内部的RAG系统？主要数据源是PDF文档，预计数据量500GB，要求响应延迟小于500ms"
    assessment = assess_completeness(q)
    assert assessment.intent == "rag_design"
    assert assessment.complexity == "complex"
    assert assessment.extracted_info.get("scenario") == "企业知识库"
    assert assessment.extracted_info.get("data_source") == "PDF/Office 文档"
    assert "500gb" in assessment.extracted_info.get("scale", "").lower()
    perf = assessment.extracted_info.get("performance_requirement", "")
    assert "<500ms" in perf or "小于500ms" in perf or "延迟" in perf

    # All fields extracted, so missing fields should be empty
    missing = missing_fields(assessment, assessment.extracted_info)
    assert missing == ()


def test_rag_design_missing_fields_when_only_topic_given():
    q = "如何搭建一个RAG系统？"
    assessment = assess_completeness(q)
    assert assessment.intent == "rag_design"
    missing = missing_fields(assessment, {})
    assert "scenario" in missing
    assert "data_source" in missing
    assert "scale" in missing
    assert "performance_requirement" in missing


def test_comparison_detection_and_field_extraction():
    q = "比较“方案A”和“方案B”的功能和性能差异，请输出对比表格"
    assessment = assess_completeness(q)
    assert assessment.intent == "document_comparison"
    assert assessment.extracted_info.get("doc_ids") == "方案A、方案B"
    assert assessment.extracted_info.get("comparison_aspect") in ("功能", "性能")
    assert assessment.extracted_info.get("output_format") == "表格"


def test_comparison_versus_syntax_and_cleaning():
    q = "Chroma vs Milvus 的区别"
    assessment = assess_completeness(q)
    assert assessment.intent == "document_comparison"
    assert assessment.extracted_info.get("doc_ids") == "Chroma、Milvus"


def test_clean_comparison_target_filters_instruction_noise():
    assert _clean_comparison_target("请帮我分析") is None
    assert _clean_comparison_target("方案A的区别") == "方案A"
    assert _clean_comparison_target("Chroma") == "Chroma"


@pytest.mark.parametrize(
    "query, expected_intent, expected_missing",
    [
        # Vague troubleshooting queries
        ("报错了怎么办？", "troubleshooting", ("error_details",)),
        ("出错了", "troubleshooting", ("error_details",)),
        ("系统运行失败", "troubleshooting", ("error_details",)),
        ("接口崩了怎么办？", "troubleshooting", ("error_details",)),
        ("程序无法启动", "troubleshooting", ("error_details",)),
        # Vague setup queries
        ("怎么配置？", "environment_setup", ("target_component",)),
        ("如何安装？", "environment_setup", ("target_component",)),
        ("请问怎么部署呢？", "environment_setup", ("target_component",)),
        ("how to deploy", "environment_setup", ("target_component",)),
        ("how to setup", "environment_setup", ("target_component",)),
        # Vague usage queries
        ("怎么用？", "usage_guidance", ("usage_target",)),
        ("这个系统如何使用呢？", "usage_guidance", ("usage_target",)),
        ("平台怎么操作？", "usage_guidance", ("usage_target",)),
        ("how to use", "usage_guidance", ("usage_target",)),
        # Vague optimization queries
        ("怎么优化？", "optimization", ("optimization_target",)),
        ("如何调优呢？", "optimization", ("optimization_target",)),
        ("系统怎么加速？", "optimization", ("optimization_target",)),
        ("how to optimize", "optimization", ("optimization_target",)),
    ],
)
def test_vague_intents_trigger_clarification(query, expected_intent, expected_missing):
    assessment = assess_completeness(query)
    assert assessment.intent == expected_intent
    assert missing_fields(assessment, {}) == expected_missing


@pytest.mark.parametrize(
    "query",
    [
        # Specific troubleshooting queries (should directly answer, not clarify)
        "Milvus 连接超时 500 error 怎么排查？",
        "启动时报错 CUDA out of memory 怎么解决？",
        # Specific environment setup queries (target specified)
        "如何部署前端 Web 界面？",
        "如何配置 Milvus 向量数据库？",
        "how to install docker on ubuntu",
        # Specific usage queries (target specified)
        "知识库文档上传与切片功能怎么用？",
        "如何调用多智能体问答 RESTful API？",
        # Specific optimization queries (target specified)
        "如何优化检索召回率和重排效果？",
        "如何降低大模型调用的延迟和显存占用？",
        # General knowledge & chat queries
        "请帮我总结一下这篇关于量子计算的综述论文",
        "Python 里的 GIL 是如何工作的？",
        "写一段快速排序的实现代码",
    ],
)
def test_complete_and_specific_queries_do_not_block_with_vague_clarification(query):
    assessment = assess_completeness(query)
    # Queries that already provide sufficient context or are specific should not be classified as vague intents with missing fields
    if assessment.intent != "complete":
        assert missing_fields(assessment, assessment.extracted_info) == ()
    else:
        assert assessment.intent == "complete"
        assert assessment.complexity == "simple"
        assert missing_fields(assessment, {}) == ()


@pytest.mark.parametrize(
    ("question", "component"),
    [("redis 报错", "redis"), ("docker 出错了", "docker"), ("exception", "exception")],
)
def test_a_vague_error_report_that_names_a_component_is_not_asked_about_it(question, component):
    """Troubleshooting is the one rule whose keywords can fire: its short-input
    door admits a question with a component attached, and naming one answers
    the question the clarifier would otherwise ask.

    This replaced a test of four `_extract_*_fields` wrappers, which fed them
    sentences like "如何配置 Neo4j 图谱？" -- a question `assess_completeness`
    classifies as complete, so production never extracted from it at all."""
    assessment = assess_completeness(question)

    assert assessment.intent == "troubleshooting"
    assert assessment.extracted_info.get("error_details") == component
    assert missing_fields(assessment, {}) == ()


@pytest.mark.parametrize(
    ("question", "intent", "field"),
    [
        ("如何配置", "environment_setup", "target_component"),
        ("这个系统怎么使用？", "usage_guidance", "usage_target"),
        ("how to optimize", "optimization", "optimization_target"),
    ],
)
def test_the_other_vague_intents_always_ask_for_their_field(question, intent, field):
    """Their patterns match whole sentences of filler words, so there is never a
    keyword to extract; a question that names one is not vague and answers as
    complete instead."""
    assessment = assess_completeness(question)

    assert assessment.intent == intent
    assert missing_fields(assessment, {}) == (field,)


def test_question_immutability():
    q1 = question_for("rag_design", "scenario")
    assert q1 is not None
    orig_len = len(q1.options)
    q1.options.append("New Option")

    q2 = question_for("rag_design", "scenario")
    assert q2 is not None
    assert len(q2.options) == orig_len


def test_max_rounds_for_all_intents():
    assert max_rounds_for("rag_design") == 4
    assert max_rounds_for("document_comparison") == 1
    assert max_rounds_for("environment_setup") == 1
    assert max_rounds_for("troubleshooting") == 1
    assert max_rounds_for("usage_guidance") == 1
    assert max_rounds_for("optimization") == 1
    assert max_rounds_for("complete") == 0
    assert max_rounds_for("unknown_intent") == 0
