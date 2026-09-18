"""Unit and integration tests for dynamic LLM-based Clarification Agent."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.clarification.prompts import build_clarification_prompt
from app.agents.clarification.service import (
    ClarificationAgentService,
    _clean_field_name,
    _extract_json,
    _normalize_options,
)
from app.domain.contracts import ClarificationContext
from app.orchestration.request import OrchestrationRequest


class TestDynamicClarificationHelperFunctions:
    def test_clean_field_name_valid(self):
        assert _clean_field_name("target_framework") == "target_framework"
        assert _clean_field_name("Scale_Tier_2") == "scale_tier_2"

    def test_clean_field_name_invalid_prefix(self):
        # Leading digits or symbols get normalized to valid identifier
        cleaned = _clean_field_name("123_scale")
        assert cleaned.startswith("field_")
        assert cleaned == "field_123_scale"

    def test_clean_field_name_empty(self):
        assert _clean_field_name("") == "field_requirement"
        assert _clean_field_name("___") == "field_requirement"

    def test_clean_field_name_length_limit(self):
        long_name = "a" * 100
        cleaned = _clean_field_name(long_name)
        assert len(cleaned) <= 64

    def test_normalize_options_chinese(self):
        raw = ["FastAPI 方案", "Django 方案"]
        opts = _normalize_options(raw, "zh")
        assert opts[0].startswith("(推荐)")
        assert opts[-1] == "其他（自定义输入 / 补充说明）"
        assert len(opts) == 3

    def test_normalize_options_english(self):
        raw = ["Docker deployment", "Serverless deployment"]
        opts = _normalize_options(raw, "en")
        assert opts[0].startswith("(Recommended)")
        assert opts[-1] == "Other (Custom input / specify details)"
        assert len(opts) == 3

    def test_extract_json_from_markdown_block(self):
        content = """```json
        {
            "needs_clarification": true,
            "field_name": "target_cloud",
            "question": "Which cloud provider?",
            "options": ["(Recommended) AWS", "GCP", "Other (Custom input / specify details)"]
        }
        ```"""
        data = _extract_json(content)
        assert data is not None
        assert data["needs_clarification"] is True
        assert data["field_name"] == "target_cloud"

    def test_extract_json_invalid(self):
        assert _extract_json("not json at all") is None
        assert _extract_json("{broken json:") is None


class TestClarificationAgentDualTrack:
    def test_fast_path_rules_take_precedence(self):
        service = ClarificationAgentService()
        # "帮我设计一个 RAG 系统" hits rag_design rule
        req = OrchestrationRequest(question="帮我设计一个 RAG 系统")
        result = service.clarify(req)
        assert result.action == "ask"
        assert result.context.intent == "rag_design"
        assert result.question is not None
        assert result.question.field_name in {"domain", "scenario", "source_type", "latency_requirement"}

    def test_smalltalk_query_continues_directly(self):
        service = ClarificationAgentService()
        req = OrchestrationRequest(question="你好呀")
        result = service.clarify(req)
        assert result.action == "continue"

    def test_dynamic_clarification_sync_ask(self):
        service = ClarificationAgentService()
        mock_response = SimpleNamespace(
            content=json.dumps(
                {
                    "needs_clarification": True,
                    "field_name": "tech_stack",
                    "question": "请问您期望采用哪种主流技术栈？",
                    "options": [
                        "(推荐) Python / FastAPI：生态成熟且对 AI Agent 支持最佳",
                        "Go / Gin：高性能并发网络服务",
                        "其他（自定义输入 / 补充说明）",
                    ],
                    "reason": "缺少技术栈约束",
                },
                ensure_ascii=False,
            )
        )

        with patch("app.agents.clarification.service.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.invoke.return_value = mock_response
            mock_get_model.return_value = mock_model

            req = OrchestrationRequest(question="帮我规划一个高并发微服务系统方案")
            result = service.clarify(req)

            assert result.action == "ask"
            assert result.question is not None
            assert result.question.field_name == "tech_stack"
            assert result.question.options[0].startswith("(推荐)")
            assert result.question.options[-1] == "其他（自定义输入 / 补充说明）"
            assert result.context.clarification_round == 1
            assert result.context.asked_questions == ["tech_stack"]
            assert result.context.intent == "dynamic_tech_stack"

    @pytest.mark.asyncio
    async def test_dynamic_clarification_async_ask(self):
        service = ClarificationAgentService()
        mock_response = SimpleNamespace(
            content=json.dumps(
                {
                    "needs_clarification": True,
                    "field_name": "target_cloud",
                    "question": "What is your primary target cloud platform?",
                    "options": [
                        "(Recommended) AWS: Most comprehensive enterprise services",
                        "Google Cloud: Best integrated AI and data stack",
                        "Other (Custom input / specify details)",
                    ],
                    "reason": "Missing cloud deployment target",
                }
            )
        )

        with patch("app.agents.clarification.service.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_response)
            mock_get_model.return_value = mock_model

            req = OrchestrationRequest(question="Help me build a scalable cloud infrastructure")
            result = await service.a_clarify(req)

            assert result.action == "ask"
            assert result.question is not None
            assert result.question.field_name == "target_cloud"
            assert result.question.options[0].startswith("(Recommended)")
            assert result.question.options[-1] == "Other (Custom input / specify details)"
            assert result.context.clarification_round == 1
            assert result.context.asked_questions == ["target_cloud"]

    def test_dynamic_clarification_llm_says_no_clarification_needed(self):
        service = ClarificationAgentService()
        mock_response = SimpleNamespace(
            content=json.dumps({"needs_clarification": False, "reason": "Query is specific and direct"})
        )

        with patch("app.agents.clarification.service.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.invoke.return_value = mock_response
            mock_get_model.return_value = mock_model

            req = OrchestrationRequest(question="Python 3.12 的核心新特性是什么？")
            result = service.clarify(req)

            assert result.action == "continue"
            assert result.question is None

    def test_dynamic_clarification_llm_error_fails_open_to_continue(self):
        service = ClarificationAgentService()
        with patch("app.agents.clarification.service.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.invoke.side_effect = RuntimeError("API connection timeout")
            mock_get_model.return_value = mock_model

            req = OrchestrationRequest(question="随意的一个非规则提问")
            result = service.clarify(req)

            assert result.action == "continue"
            assert result.question is None

    def test_dynamic_clarification_multi_round_and_max_rounds_cap(self):
        service = ClarificationAgentService()
        mock_response = SimpleNamespace(
            content=json.dumps(
                {
                    "needs_clarification": True,
                    "field_name": "extra_req",
                    "question": "还有额外需求吗？",
                    "options": ["(推荐) 默认设置", "其他（自定义输入 / 补充说明）"],
                },
                ensure_ascii=False,
            )
        )

        with patch("app.agents.clarification.service.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.invoke.return_value = mock_response
            mock_get_model.return_value = mock_model

            # Context already at 3 rounds
            context = ClarificationContext(
                clarification_round=3,
                max_rounds=3,
                asked_questions=["f1", "f2", "f3"],
                collected_info={"f1": "ans1", "f2": "ans2", "f3": "ans3"},
            )
            req = OrchestrationRequest(question="帮我设计一个复杂系统方案")
            result = service.clarify(req, context=context)

            # Reached max rounds: must terminate with continue
            assert result.action == "continue"
            assert "Confirmed constraints:" in str(result.complete_query)
            assert "ans1" in str(result.complete_query)

    def test_local_evidence_chat_model_clarification_integration(self):
        # When using LocalEvidenceChatModel, test that invoke handles clarification prompt
        from app.services.models.runtime import LocalEvidenceChatModel

        local_model = LocalEvidenceChatModel()
        prompt = build_clarification_prompt(question="帮我设计一个微服务系统架构方案", language="zh")
        response = local_model.invoke([("system", prompt)])
        data = json.loads(response.content)

        assert data["needs_clarification"] is True
        assert data["field_name"] == "target_architecture"
        assert data["options"][0].startswith("(推荐)")
        assert data["options"][-1] == "其他（自定义输入 / 补充说明）"
