"""Self-RAG never takes the response past the deadline the client declared.

It runs after the pipeline, outside its budget, with the synthesis ceiling as
its only limit (30 s). The client declares 90 s and aborts at 105 s, so a slow
pipeline plus a slow evaluation made the browser report a timeout while the
server went on to save the answer.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.api.routes.public import query as advanced_rag
from app.pipeline.contracts import PipelineResult, PipelineRoute


def test_without_a_deadline_the_synthesis_ceiling_applies() -> None:
    ceiling = advanced_rag.get_settings().stage_timeout_synthesis_ms / 1000.0

    assert advanced_rag._self_rag_timeout(None) == pytest.approx(max(1.0, ceiling))


def test_the_timeout_is_cut_to_what_the_deadline_leaves() -> None:
    timeout = advanced_rag._self_rag_timeout(datetime.now(UTC) + timedelta(seconds=5))

    assert timeout is not None and timeout <= 5.0


def test_with_no_time_left_it_is_skipped() -> None:
    assert advanced_rag._self_rag_timeout(datetime.now(UTC) + timedelta(milliseconds=200)) is None


@pytest.mark.asyncio
async def test_a_spent_deadline_skips_the_evaluation_without_calling_it(monkeypatch) -> None:
    calls: list[str] = []

    async def evaluation(**_kwargs):
        calls.append("called")
        await asyncio.sleep(0)
        return None, []

    monkeypatch.setattr(advanced_rag, "_run_self_rag_evaluation_impl", evaluation)

    result = await advanced_rag._run_self_rag_evaluation(
        query="q",
        pipeline_result=PipelineResult(answer="a", route=PipelineRoute(route="vector")),
        plan_data=None,
        deadline_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert result == (None, [])
    assert calls == []
