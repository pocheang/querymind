"""`AdvancedRAGRequest.use_reasoning` is the one new field the visible-reasoning
feature adds to the public chat endpoint -- everything downstream of
`PipelineRequest` (model selection, prompt variant, the <think> extraction)
already existed or is covered by its own tests. This only pins that the field
actually reaches `PipelineRequest`, since a flag that stops at the API layer
would silently do nothing, the same failure this repo has hit before with
`use_reasoning` on the rerun path.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.api.routes.public import query as advanced_rag
from app.pipeline.contracts import PipelineRequest, PipelineResult, PipelineRoute


class _CapturingPipeline:
    captured: PipelineRequest | None = None

    async def execute(self, request: PipelineRequest) -> PipelineResult:
        _CapturingPipeline.captured = request
        return PipelineResult(
            answer=f"answer to: {request.question}",
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


@pytest.mark.asyncio
async def test_use_reasoning_true_reaches_pipeline_request():
    await advanced_rag._process_advanced_rag_query_impl(
        advanced_rag.AdvancedRAGRequest(query="explain BM25", use_reasoning=True), _Request(), _user()
    )

    assert _CapturingPipeline.captured is not None
    assert _CapturingPipeline.captured.use_reasoning is True


@pytest.mark.asyncio
async def test_use_reasoning_defaults_false():
    """Off by default: writing out full reasoning before answering costs
    meaningfully more time and tokens than the silent prompt every other
    question uses."""
    await advanced_rag._process_advanced_rag_query_impl(
        advanced_rag.AdvancedRAGRequest(query="explain BM25"), _Request(), _user()
    )

    assert _CapturingPipeline.captured is not None
    assert _CapturingPipeline.captured.use_reasoning is False
