"""An answer says which specialist wrote it and in what shape.

The chat response carried the route and nothing about the specialist, so the
client could name only the mode a user had pinned in the sidebar -- never the
one the router chose. And the rerun path read `agent_class` off a dict that
never held one, so every re-run answer was recorded as the general analyst.
Both paths now report the class and the answer shape (the skill after the
specialist's translation), and both are pinned here.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from app.agents.registry import answer_shape
from app.api.routes.internal import pipeline_contract
from app.api.routes.public import query as advanced_rag
from app.pipeline.contracts import PipelineResult, PipelineRoute
from app.services.sessions.history import HistoryStore

_ROUTE = PipelineRoute(route="vector", reason="stub", agent_class="cybersecurity", skill="cve_vulnerability_assessment")


class _StubPipeline:
    async def execute(self, request: Any) -> PipelineResult:
        return PipelineResult(answer="a", route=_ROUTE, execution_metadata={})

    def execute_sync(self, request: Any) -> PipelineResult:
        return PipelineResult(answer="a", route=_ROUTE, execution_metadata={})


class _Request:
    client = None
    headers: dict[str, str] = {}
    url = type("U", (), {"path": "/api/advanced-rag/query"})()


@pytest.fixture
def history(monkeypatch) -> HistoryStore:
    root = Path(tempfile.mkdtemp(prefix="querymind-specialist-"))
    store = HistoryStore(base_dir=root / "sessions")
    monkeypatch.setattr(advanced_rag, "_history_store_for_user", lambda user: store)
    monkeypatch.setattr(advanced_rag, "_promote_long_term_memory", lambda **_: None)
    monkeypatch.setattr(advanced_rag, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(advanced_rag, "_resolve_advanced_allowed_sources", lambda user, req: ["corpus"])
    monkeypatch.setattr(advanced_rag, "RAGPipeline", _StubPipeline)
    monkeypatch.setattr(advanced_rag, "_build_memory_context_for_session", lambda u, sid, q: "")
    try:
        yield store
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_specialist_translates_its_own_skill_into_the_shape_it_answers_in() -> None:
    assert answer_shape("cybersecurity", "cve_vulnerability_assessment") == "vulnerability_exposure_assessment"


def test_a_class_with_no_specialist_answers_in_the_skill_it_was_given() -> None:
    assert answer_shape("general", "timeline_builder") == "timeline_builder"


@pytest.mark.asyncio
async def test_the_chat_response_names_the_specialist_and_the_shape(history) -> None:
    user = {"user_id": "u1", "username": "u", "role": "user", "permissions": []}
    session_id = history.create_session()["session_id"]

    result = await advanced_rag._process_advanced_rag_query_impl(
        advanced_rag.AdvancedRAGRequest(query="log4j 2.14.1 受影响吗", session_id=session_id), _Request(), user
    )

    assert result.metadata["agent_class"] == "cybersecurity"
    assert result.metadata["skill"] == "vulnerability_exposure_assessment"


@pytest.mark.asyncio
async def test_the_saved_message_keeps_them_for_the_next_page_load(history) -> None:
    user = {"user_id": "u1", "username": "u", "role": "user", "permissions": []}
    session_id = history.create_session()["session_id"]

    await advanced_rag._process_advanced_rag_query_impl(
        advanced_rag.AdvancedRAGRequest(query="log4j 2.14.1 受影响吗", session_id=session_id), _Request(), user
    )

    saved = [m for m in history.get_session(session_id)["messages"] if m["role"] == "assistant"][-1]
    assert saved["metadata"]["agent_class"] == "cybersecurity"
    assert saved["metadata"]["skill"] == "vulnerability_exposure_assessment"


def test_the_rerun_contract_carries_the_specialist_too(monkeypatch) -> None:
    monkeypatch.setattr(pipeline_contract, "RAGPipeline", _StubPipeline)

    result = pipeline_contract.execute_standard_compatibility(question="log4j 2.14.1 受影响吗")

    assert result["agent_class"] == "cybersecurity"
    assert result["skill"] == "vulnerability_exposure_assessment"
