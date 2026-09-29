"""One live stream per execution, one trace endpoint (follow-up to ARC-06).

`/api/v1/orchestration/executions/{id}/events` is the stream: pushed, shared
across workers in shared mode, and what the frontend subscribes to. Beside it
were `/agent-tracking/stream/{id}` -- a 0.5 s polling SSE over this worker's
tracker only, with a different event vocabulary -- and `/agents/trace/{id}`, an
admin-only copy of `/agent-tracking/trace/{id}`. Neither had a caller.
"""

from __future__ import annotations

from app.api.main import app


def _operations() -> set[tuple[str, str]]:
    return {(m.upper(), p) for p, ops in app.openapi()["paths"].items() for m in ops}


def test_the_removed_duplicates_stay_removed():
    ops = _operations()
    assert ("GET", "/api/v1/agent-tracking/stream/{execution_id}") not in ops
    assert ("GET", "/api/v1/agents/trace/{execution_id}") not in ops


def test_the_canonical_stream_and_trace_remain():
    ops = _operations()
    assert ("GET", "/api/v1/orchestration/executions/{execution_id}/events") in ops
    assert ("GET", "/api/v1/agent-tracking/trace/{execution_id}") in ops
