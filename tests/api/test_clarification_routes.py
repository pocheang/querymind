"""Integration and regression tests for Clarification API endpoints (/api/v1/clarification)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import _require_user
from app.api.routes.public import clarification as clarification_module
from app.api.routes.public.clarification import router as clarification_router
from app.services.sessions.history import HistoryStore

TEST_USER: dict[str, Any] = {
    "user_id": "test-user-123",
    "tenant_id": "tenant-abc",
    "username": "tester",
    "role": "editor",
    "permissions": ["query:run", "session:create"],
}


@pytest.fixture
def temp_history_store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(base_dir=tmp_path / "sessions")


@pytest.fixture
def client(temp_history_store: HistoryStore, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(clarification_router)

    app.dependency_overrides[_require_user] = lambda: TEST_USER
    monkeypatch.setattr(clarification_module, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(clarification_module, "_history_store_for_user", lambda _u: temp_history_store)

    return TestClient(app)


class TestClarificationRoutesIntegration:
    def test_missing_session_creates_session_and_asks_clarification(self, client: TestClient):
        """Querying a RAG design query without prior session creates session and returns NEED_CLARIFICATION."""
        payload = {
            "question": "帮我设计一个企业级 RAG 知识库系统",
            "session_id": "session-test-01",
        }
        res = client.post("/api/v1/clarification/check", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["action"] == "NEED_CLARIFICATION"
        assert data["clarification"] is not None
        assert data["clarification"]["field_name"] in {
            "domain",
            "scenario",
            "source_type",
            "data_source",
            "latency_requirement",
        }
        assert data["clarification"]["options"][0].startswith("(推荐)")
        assert data["clarification"]["options"][-1] == "其他（自定义输入 / 补充说明）"
        assert data["context"]["clarification_round"] == 1
        assert data["workflow_thread_id"] == "tenant-abc:test-user-123:session-test-01"

    def test_submitting_answer_advances_round_and_persists_in_session(
        self, client: TestClient, temp_history_store: HistoryStore
    ):
        """Submitting an answer updates session store and asks the next question."""
        session_id = "session-test-02"
        # Round 1: Trigger question
        res1 = client.post(
            "/api/v1/clarification/check",
            json={"question": "帮我设计一个 RAG 系统", "session_id": session_id},
        )
        assert res1.status_code == 200
        data1 = res1.json()
        field_1 = data1["clarification"]["field_name"]
        thread_id = data1["workflow_thread_id"]

        # Round 2: Answer field 1 with recommended choice
        res2 = client.post(
            "/api/v1/clarification/check",
            json={
                "question": "帮我设计一个 RAG 系统",
                "session_id": session_id,
                "field_name": field_1,
                "answer": "(推荐) 企业内部知识库：聚焦内部文档检索与员工自助问答",
                "workflow_thread_id": thread_id,
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["action"] in {"NEED_CLARIFICATION", "CONTINUE"}
        session = temp_history_store.get_session(session_id)
        assert session is not None
        ctx = session.get("clarification_context", {})
        assert field_1 in ctx.get("collected_info", {})
        assert "企业内部知识库" in ctx["collected_info"][field_1]
        assert ctx.get("clarification_round") >= 1

    def test_submitting_custom_other_answer(self, client: TestClient, temp_history_store: HistoryStore):
        """Selecting '其他' and typing custom input successfully records custom answer."""
        session_id = "session-test-custom"
        res1 = client.post(
            "/api/v1/clarification/check",
            json={"question": "帮我设计一个 RAG 系统", "session_id": session_id},
        )
        field_1 = res1.json()["clarification"]["field_name"]
        thread_id = res1.json()["workflow_thread_id"]

        custom_text = "金融行业量化交易策略私有知识库"
        res2 = client.post(
            "/api/v1/clarification/check",
            json={
                "question": "帮我设计一个 RAG 系统",
                "session_id": session_id,
                "field_name": field_1,
                "answer": custom_text,
                "workflow_thread_id": thread_id,
            },
        )
        assert res2.status_code == 200

        session = temp_history_store.get_session(session_id)
        assert session["clarification_context"]["collected_info"][field_1] == custom_text

    def test_dynamic_llm_clarification_via_api(self, client: TestClient):
        """Open-ended vague query triggers dynamic LLM clarification through the API."""
        session_id = "session-dynamic-01"
        mock_llm_reply = SimpleNamespace(
            content=json.dumps(
                {
                    "needs_clarification": True,
                    "field_name": "tech_stack_preference",
                    "question": "请问您期望采用哪种主流开发语言与框架？",
                    "options": [
                        "(推荐) Python FastAPI：轻量高性能，与 AI 智能体原生契合",
                        "Go Gin：高吞吐微服务首选",
                        "Java Spring Boot：大型企业级稳健生态",
                        "其他（自定义输入 / 补充说明）",
                    ],
                    "reason": "缺少技术栈与生态偏好",
                },
                ensure_ascii=False,
            )
        )

        with patch("app.agents.clarification.service.get_chat_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.ainvoke = MagicMock(return_value=mock_llm_reply)

            # Support both async and sync mock depending on invocation
            async def _async_reply(*a, **k):
                return mock_llm_reply

            mock_model.ainvoke = _async_reply
            mock_model.invoke.return_value = mock_llm_reply
            mock_get_model.return_value = mock_model

            res = client.post(
                "/api/v1/clarification/check",
                json={
                    "question": "我想做一个微服务高并发系统方案，帮忙规划一下",
                    "session_id": session_id,
                },
            )
            assert res.status_code == 200
            data = res.json()

            assert data["action"] == "NEED_CLARIFICATION"
            assert data["clarification"]["field_name"] == "tech_stack_preference"
            assert data["clarification"]["options"][0].startswith("(推荐)")
            assert data["clarification"]["options"][-1] == "其他（自定义输入 / 补充说明）"
            assert data["context"]["intent"] == "dynamic_tech_stack_preference"

    def test_validation_error_on_mismatched_field_name_and_answer(self, client: TestClient):
        """Submitting field_name without answer or answer without field_name returns 422."""
        res1 = client.post(
            "/api/v1/clarification/check",
            json={
                "question": "测试问题",
                "session_id": "session-err-1",
                "field_name": "some_field",
                "answer": None,
            },
        )
        assert res1.status_code == 422

        res2 = client.post(
            "/api/v1/clarification/check",
            json={
                "question": "测试问题",
                "session_id": "session-err-2",
                "field_name": None,
                "answer": "some_answer",
            },
        )
        assert res2.status_code == 422

    def test_workflow_thread_mismatch_returns_409(self, client: TestClient):
        """Providing a thread ID belonging to a different session/user returns 409 Conflict."""
        res = client.post(
            "/api/v1/clarification/check",
            json={
                "question": "测试问题",
                "session_id": "session-legit",
                "workflow_thread_id": "tenant-other:other-user:session-other",
            },
        )
        assert res.status_code == 409
        assert "thread does not match" in res.json()["detail"]

    def test_reset_clarification_endpoint(self, client: TestClient, temp_history_store: HistoryStore):
        """POST /api/v1/clarification/reset/{session_id} clears clarification state."""
        session_id = "session-to-reset"
        client.post(
            "/api/v1/clarification/check",
            json={"question": "帮我设计一个 RAG 系统", "session_id": session_id},
        )
        session = temp_history_store.get_session(session_id)
        assert session["clarification_context"]["clarification_round"] == 1

        reset_res = client.post(f"/api/v1/clarification/reset/{session_id}")
        assert reset_res.status_code == 200
        assert reset_res.json()["status"] == "success"

        session_after = temp_history_store.get_session(session_id)
        assert session_after["clarification_context"]["clarification_round"] == 0
        assert session_after["clarification_context"]["collected_info"] == {}

    def test_get_context_endpoint(self, client: TestClient):
        """GET /api/v1/clarification/context/{session_id} returns current context."""
        session_id = "session-get-ctx"
        client.post(
            "/api/v1/clarification/check",
            json={"question": "帮我设计一个 RAG 系统", "session_id": session_id},
        )

        get_res = client.get(f"/api/v1/clarification/context/{session_id}")
        assert get_res.status_code == 200
        ctx = get_res.json()
        assert ctx["clarification_round"] == 1
        assert ctx["intent"] == "rag_design"
