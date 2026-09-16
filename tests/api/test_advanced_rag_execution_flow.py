"""Pins for two defects on the input-to-output chat path (found 2026-09-15).

1. The chat UI can only ever learn `execution_id` from this endpoint's own
   response, and that response does not exist until the whole run has
   finished -- so the SSE trace panel's subscription, and the answer-fragment
   draft stream it carries, could never show anything live for a normal
   question. `AdvancedRAGRequest.execution_id` lets a caller supply its own
   id up front, so it can open the subscription before or as it sends this
   request. `_process_advanced_rag_query_impl` must use the supplied id
   end-to-end, and must refuse to let one caller claim an id that already
   names a different, live execution.

2. Self-RAG evaluation runs after `RAGPipeline.execute` returns, entirely
   outside its `ExecutionBudget`: two fixed LLM calls plus one per planner
   sub-task, none of it counted against the caller's declared deadline. The
   chat UI enables it on every message. `_run_self_rag_evaluation` must
   degrade instead of hanging when it runs long, and must not scale its
   sub-query loop with however many tasks the planner happened to produce.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

import pytest

from app.api.routes.public import query as advanced_rag
from app.pipeline.contracts import PipelineResult, PipelineRoute
from app.services.observability.agent_execution_tracker import AgentExecutionTracker


class _StubPipeline:
    async def execute(self, request):
        return PipelineResult(
            answer=f"answer to: {request.question}",
            route=PipelineRoute(route="vector", reason="stub"),
            execution_metadata={"validation": {"state": "validated"}},
        )


class _Request:
    """Minimal stand-in for starlette Request; only used by audit helpers."""

    client = None
    headers: dict[str, str] = {}
    url = type("U", (), {"path": "/api/advanced-rag/query"})()


@pytest.fixture(autouse=True)
def _stub_query_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(advanced_rag, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(advanced_rag, "_resolve_advanced_allowed_sources", lambda user, req: ["corpus"])
    monkeypatch.setattr(advanced_rag, "_build_memory_context_for_session", lambda *a, **k: "")
    monkeypatch.setattr(advanced_rag, "RAGPipeline", _StubPipeline)


def _user(user_id: str = "u1") -> dict[str, Any]:
    return {"user_id": user_id, "username": user_id, "role": "user", "permissions": []}


# --- 1. client-supplied execution_id ------------------------------------


@pytest.mark.asyncio
async def test_a_client_supplied_execution_id_is_used_end_to_end():
    """A caller that names its own id gets exactly that id back, already
    registered with the tracker -- which is what lets it open the SSE
    subscription without waiting for this call to return."""

    execution_id = str(uuid.uuid4())
    result = await advanced_rag._process_advanced_rag_query_impl(
        advanced_rag.AdvancedRAGRequest(query="hello", execution_id=execution_id), _Request(), _user()
    )

    assert result.metadata["execution_id"] == execution_id
    trace = AgentExecutionTracker.get_instance().get_execution_trace(execution_id)
    assert trace is not None
    assert trace.user_id == "u1"


@pytest.mark.asyncio
async def test_a_colliding_client_execution_id_is_not_reused():
    """One caller must not be able to claim (or overwrite) an id that already
    names another, still-live execution."""

    tracker = AgentExecutionTracker.get_instance()
    colliding_id = str(uuid.uuid4())
    tracker.start_execution("someone else's question", colliding_id, user_id="other-user", profile="advanced")

    result = await advanced_rag._process_advanced_rag_query_impl(
        advanced_rag.AdvancedRAGRequest(query="hello", execution_id=colliding_id), _Request(), _user()
    )

    assert result.metadata["execution_id"] != colliding_id
    other_trace = tracker.get_execution_trace(colliding_id)
    assert other_trace is not None
    assert other_trace.user_id == "other-user"


def test_execution_id_must_look_like_a_uuid():
    """A short or predictable id would make colliding into someone else's
    live trace by chance, not just by malice, a real possibility."""

    with pytest.raises(ValueError):
        advanced_rag.AdvancedRAGRequest(query="hello", execution_id="not-a-uuid")


# --- 2. bounded, capped self-RAG evaluation --------------------------------


@pytest.mark.asyncio
async def test_self_rag_evaluation_gives_up_instead_of_hanging(monkeypatch: pytest.MonkeyPatch):
    async def hangs(**_kwargs):
        await asyncio.sleep(999)

    monkeypatch.setattr(advanced_rag, "_run_self_rag_evaluation_impl", hangs)
    monkeypatch.setattr(advanced_rag.get_settings(), "stage_timeout_synthesis_ms", 50)

    pipeline_result = PipelineResult(answer="a", route=PipelineRoute(route="vector", reason="stub"))

    started = time.perf_counter()
    answer_quality, sub_query_results = await advanced_rag._run_self_rag_evaluation(
        query="q", pipeline_result=pipeline_result, plan_data=None
    )
    elapsed = time.perf_counter() - started

    assert (answer_quality, sub_query_results) == (None, [])
    assert elapsed < 2.0, "a stuck evaluation must not hold up the response by seconds, let alone forever"


@pytest.mark.asyncio
async def test_self_rag_sub_query_loop_is_capped_at_the_decomposer_bound(monkeypatch: pytest.MonkeyPatch):
    from app.services.query.decomposer import DEFAULT_MAX_SUB_QUERIES

    seen_task_counts: list[int] = []

    async def fake_sub_query_results(tasks, docs, llm_client, relevance_scores):
        seen_task_counts.append(len(tasks))
        return []

    class _FakeEvaluator:
        def __init__(self, llm_client):
            del llm_client

        async def evaluate_retrieval_relevance(self, query, docs):
            del query, docs
            return {}

        async def evaluate_answer_quality(self, query, answer, docs):
            del query, answer, docs
            return None

    monkeypatch.setattr(advanced_rag, "_sub_query_results", fake_sub_query_results)
    monkeypatch.setattr("app.services.models.runtime.get_reasoning_model", lambda **_: object())
    monkeypatch.setattr("app.services.retrieval.self_rag_evaluator.SelfRAGEvaluator", _FakeEvaluator)

    plan_data = {"tasks": [{"prompt": f"sub {i}", "depends_on": []} for i in range(DEFAULT_MAX_SUB_QUERIES + 5)]}
    pipeline_result = PipelineResult(answer="a", route=PipelineRoute(route="vector", reason="stub"))

    await advanced_rag._run_self_rag_evaluation(query="q", pipeline_result=pipeline_result, plan_data=plan_data)

    assert seen_task_counts == [DEFAULT_MAX_SUB_QUERIES]
