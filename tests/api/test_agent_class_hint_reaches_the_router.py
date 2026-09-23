"""The chat sidebar's agent mode reaches the router.

It did not. The picker stored the choice and showed it "locked", the frontend
sent nothing, `AdvancedRAGRequest` had no field for it, and the endpoint built
`SourceScope` from `allowed_sources` alone -- so the router's forced-class
branch (confidence 1.0) existed with no way in, and every question was routed
automatically whatever the user picked. The frontend half is pinned by
`frontend/src/services/api/chat.test.ts`.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.router import routing
from app.agents.router.service import RouterAgentService
from app.api.routes.public import query as advanced_rag
from app.orchestration.request import OrchestrationRequest, RequestScope
from app.pipeline.contracts import PipelineRequest, PipelineResult, PipelineRoute


class _CapturingPipeline:
    captured: PipelineRequest | None = None

    async def execute(self, request: PipelineRequest) -> PipelineResult:
        _CapturingPipeline.captured = request
        return PipelineResult(
            answer="stub",
            route=PipelineRoute(route="vector", reason="stub"),
            execution_metadata={"validation": {"state": "validated"}},
        )


class _Request:
    client = None
    headers: dict[str, str] = {}
    url = type("U", (), {"path": "/api/advanced-rag/query"})()


@pytest.fixture(autouse=True)
def _stub_query_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(advanced_rag, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(advanced_rag, "_resolve_advanced_allowed_sources", lambda user, req: ["corpus"])
    monkeypatch.setattr(advanced_rag, "_build_memory_context_for_session", lambda *a, **k: "")
    monkeypatch.setattr(advanced_rag, "RAGPipeline", _CapturingPipeline)
    _CapturingPipeline.captured = None


def _user() -> dict[str, Any]:
    return {"user_id": "u1", "username": "u1", "role": "user", "permissions": []}


def _run(request: advanced_rag.AdvancedRAGRequest) -> PipelineRequest:
    asyncio.run(advanced_rag._process_advanced_rag_query_impl(request, _Request(), _user()))
    assert _CapturingPipeline.captured is not None
    return _CapturingPipeline.captured


def test_the_hint_reaches_the_pipeline_request():
    captured = _run(advanced_rag.AdvancedRAGRequest(query="怎么加固暴露的服务", agent_class_hint="cybersecurity"))

    assert captured.source_scope.agent_class_hint == "cybersecurity"
    # And the scope it rides on is still the resolver's, not widened by it.
    assert captured.source_scope.allowed_sources == frozenset({"corpus"})


def test_no_hint_means_automatic_routing():
    assert _run(advanced_rag.AdvancedRAGRequest(query="q")).source_scope.agent_class_hint is None


@pytest.mark.parametrize("value", ["cyber security", "../admin", "x" * 65, "1abc"])
def test_a_hint_must_look_like_an_agent_class(value: str):
    with pytest.raises(ValidationError):
        advanced_rag.AdvancedRAGRequest(query="q", agent_class_hint=value)


def test_the_router_is_handed_the_hint(monkeypatch: pytest.MonkeyPatch):
    seen: dict[str, Any] = {}

    def decider(question: str, **kwargs: Any):
        seen.update(kwargs)
        return type(
            "Legacy",
            (),
            {"route": "vector", "confidence": 0.9, "reason": "stub", "agent_class": "cybersecurity"},
        )()

    request = OrchestrationRequest(question="q", source_scope=RequestScope(agent_class_hint="cybersecurity"))
    asyncio.run(RouterAgentService(decider=decider).route(request))

    assert seen["agent_class_hint"] == "cybersecurity"


def test_a_forced_class_skips_classification():
    # What the hint buys once it arrives: the class is taken, not guessed.
    agent_class, confidence, method = routing._classify("任何问题", "cybersecurity", use_llm_intent=True)

    assert (agent_class, confidence, method) == ("cybersecurity", 1.0, "forced")
