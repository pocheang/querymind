"""Shared stub for tests that pin a chat request field reaching the pipeline.

Several `AdvancedRAGRequest` fields exist only to be forwarded, and the failure
they guard against is the same each time: the field is accepted and stops at
the API layer. One stub keeps those tests asserting the forwarding rather than
each carrying its own copy of the endpoint's dependencies.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from app.api.routes.public import query as advanced_rag
from app.pipeline.contracts import PipelineRequest, PipelineResult, PipelineRoute

SubmitQuery = Callable[[advanced_rag.AdvancedRAGRequest], Awaitable[PipelineRequest]]


class _Request:
    client = None
    headers: dict[str, str] = {}
    url = type("U", (), {"path": "/api/advanced-rag/query"})()


@pytest.fixture
def submit_query(monkeypatch: pytest.MonkeyPatch) -> SubmitQuery:
    """Run the chat endpoint once and return the `PipelineRequest` it built."""
    captured: list[PipelineRequest] = []

    class _CapturingPipeline:
        async def execute(self, request: PipelineRequest) -> PipelineResult:
            captured.append(request)
            return PipelineResult(
                answer=f"answer to: {request.question}",
                route=PipelineRoute(route="vector", reason="stub"),
                execution_metadata={"validation": {"state": "validated"}},
            )

    monkeypatch.setattr(advanced_rag, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(advanced_rag, "_resolve_advanced_allowed_sources", lambda user, req: ["corpus"])
    monkeypatch.setattr(advanced_rag, "_build_memory_context_for_session", lambda *a, **k: "")
    monkeypatch.setattr(advanced_rag, "RAGPipeline", _CapturingPipeline)

    user: dict[str, Any] = {"user_id": "u1", "username": "u1", "role": "user", "permissions": []}

    async def submit(request: advanced_rag.AdvancedRAGRequest) -> PipelineRequest:
        await advanced_rag._process_advanced_rag_query_impl(request, _Request(), user)
        assert len(captured) == 1, "the endpoint did not reach the pipeline exactly once"
        return captured.pop()

    return submit
