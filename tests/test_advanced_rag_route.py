from types import SimpleNamespace

import pytest

from app.api.routes import advanced_rag as advanced_rag_routes
from app.models.advanced_rag_models import AdvancedRAGResult


class _FakeWorkflow:
    seen_allowed_sources = None

    def __init__(self, enable_decomposition: bool = False, enable_self_rag: bool = False):
        self.enable_decomposition = enable_decomposition
        self.enable_self_rag = enable_self_rag

    async def process_query(self, query: str, allowed_sources=None, retrieval_strategy=None):
        type(self).seen_allowed_sources = allowed_sources
        return AdvancedRAGResult(
            query=query,
            decomposed_query=None,
            sub_query_results=[],
            final_answer="ok",
            answer_quality=None,
            metadata={},
        )


@pytest.mark.asyncio
async def test_advanced_rag_query_intersects_requested_sources(monkeypatch):
    user = {"user_id": "u-advanced", "role": "viewer", "status": "active"}
    monkeypatch.setattr(advanced_rag_routes, "_require_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(advanced_rag_routes, "_allowed_sources_for_user", lambda _user: ["allowed.md", "shared.md"])
    monkeypatch.setattr(advanced_rag_routes, "AdvancedRAGWorkflow", _FakeWorkflow)

    result = await advanced_rag_routes.process_advanced_rag_query(
        request_data=advanced_rag_routes.AdvancedRAGRequest(
            query="scope test",
            allowed_sources=["forbidden.md", "allowed.md"],
        ),
        request=SimpleNamespace(),
        user=user,
    )

    assert result.final_answer == "ok"
    assert _FakeWorkflow.seen_allowed_sources == ["allowed.md"]


@pytest.mark.asyncio
async def test_advanced_rag_query_defaults_to_visible_sources(monkeypatch):
    user = {"user_id": "u-advanced", "role": "viewer", "status": "active"}
    monkeypatch.setattr(advanced_rag_routes, "_require_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(advanced_rag_routes, "_allowed_sources_for_user", lambda _user: ["doc-a.md", "doc-b.md"])
    monkeypatch.setattr(advanced_rag_routes, "AdvancedRAGWorkflow", _FakeWorkflow)

    result = await advanced_rag_routes.process_advanced_rag_query(
        request_data=advanced_rag_routes.AdvancedRAGRequest(query="default scope"),
        request=SimpleNamespace(),
        user=user,
    )

    assert result.final_answer == "ok"
    assert _FakeWorkflow.seen_allowed_sources == ["doc-a.md", "doc-b.md"]
