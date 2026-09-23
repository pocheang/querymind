"""`AdvancedRAGRequest.use_reasoning` is the one new field the visible-reasoning
feature adds to the public chat endpoint -- everything downstream of
`PipelineRequest` (model selection, prompt variant, the <think> extraction)
already existed or is covered by its own tests. This only pins that the field
actually reaches `PipelineRequest`, since a flag that stops at the API layer
would silently do nothing, the same failure this repo has hit before with
`use_reasoning` on the rerun path.
"""

from __future__ import annotations

import pytest

from app.api.routes.public import query as advanced_rag


@pytest.mark.asyncio
async def test_use_reasoning_true_reaches_pipeline_request(submit_query):
    captured = await submit_query(advanced_rag.AdvancedRAGRequest(query="explain BM25", use_reasoning=True))

    assert captured.use_reasoning is True


@pytest.mark.asyncio
async def test_use_reasoning_defaults_false(submit_query):
    """Off by default: writing out full reasoning before answering costs
    meaningfully more time and tokens than the silent prompt every other
    question uses."""
    captured = await submit_query(advanced_rag.AdvancedRAGRequest(query="explain BM25"))

    assert captured.use_reasoning is False
