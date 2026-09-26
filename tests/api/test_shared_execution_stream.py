"""A run's SSE stream and its dashboard numbers are shared by every worker (ARC-01 phase 3).

The pipeline answering a question and the SSE connection watching it can land on
different workers. Everything here runs against fakeredis standing in for the
Redis they share, and "another worker" is modelled the only way that matters: the
subscribing side has no record of the run in its own process at all.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import timedelta

import pytest

fakeredis = pytest.importorskip("fakeredis")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.application.factory import shared_state_unavailable  # noqa: E402
from app.api.deps.runtime import (  # noqa: E402
    get_answer_stream_store,
    get_execution_event_store,
    get_thought_stream_store,
    require_trace_actor,
)
from app.api.routes.public import orchestration as orchestration_module  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.domain.events import ExecutionEvent  # noqa: E402
from app.orchestration import shared_execution  # noqa: E402
from app.orchestration.answer_stream import AnswerStreamStore, get_default_answer_stream_store  # noqa: E402
from app.orchestration.execution_events import ExecutionEventStore, get_default_execution_event_store  # noqa: E402
from app.orchestration.request import RequestActor  # noqa: E402
from app.services.observability.agent_execution_tracker import AgentExecutionTracker, utcnow  # noqa: E402
from app.services.runtime import shared_state  # noqa: E402

OWNER = RequestActor(user_id="u-owner", role="viewer")
STRANGER = RequestActor(user_id="u-stranger", role="viewer")
ADMIN = RequestActor(user_id="u-admin", role="admin")
QUESTION = "what is the salary of employee 4471?"


@pytest.fixture
def shared(monkeypatch, tmp_path):
    """STATE_BACKEND=shared over one fakeredis server, with a scratch app.db."""

    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty))
    monkeypatch.setenv("STATE_BACKEND", "shared")
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.db"))
    get_settings.cache_clear()

    server = fakeredis.FakeServer()
    sync_client = fakeredis.FakeRedis(server=server, decode_responses=True)
    async_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr(shared_state._CONNECTOR, "_client", sync_client)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", 0.0)
    monkeypatch.setattr(shared_execution._READER, "_client", async_client)
    monkeypatch.setattr(shared_execution._READER, "_unavailable_until", 0.0)
    monkeypatch.setattr(orchestration_module, "_SUBSCRIBE_GRACE_SECONDS", 0.3)
    yield sync_client
    shared_execution.flush()
    get_settings.cache_clear()


def _app(actor: RequestActor) -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(shared_state.SharedStateUnavailable, shared_state_unavailable)
    app.include_router(orchestration_module.router)
    app.dependency_overrides[require_trace_actor] = lambda: actor
    # The subscribing worker's own stores: deliberately empty.
    app.dependency_overrides[get_execution_event_store] = ExecutionEventStore
    app.dependency_overrides[get_answer_stream_store] = AnswerStreamStore
    app.dependency_overrides[get_thought_stream_store] = AnswerStreamStore
    return app


def _events(body: str) -> list[tuple[str, str]]:
    """(event name, data) for every SSE message in `body`."""

    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        out.append((lines.get("event", ""), lines.get("data", "")))
    return out


def _run_on_another_worker(execution_id: str) -> None:
    """What the answering worker writes, through the same functions the pipeline calls."""

    shared_execution.open_execution(execution_id, OWNER.user_id)
    shared_execution.publish_event(execution_id, ExecutionEvent(stage="route", status="completed", duration_ms=5))
    shared_execution.publish_fragment(execution_id, shared_execution.KIND_ANSWER, "BM25 ranks ")
    shared_execution.publish_fragment(execution_id, shared_execution.KIND_THOUGHT, "thinking")
    shared_execution.publish_event(execution_id, ExecutionEvent(stage="synthesize", status="completed", duration_ms=9))
    shared_execution.finish_execution(
        execution_id, ExecutionEvent(stage="complete", status="completed", duration_ms=20)
    )
    assert shared_execution.flush()


def test_a_subscriber_on_another_worker_receives_the_whole_run_in_order(shared):
    execution_id = str(uuid.uuid4())
    _run_on_another_worker(execution_id)
    assert AgentExecutionTracker.get_instance().get_execution_trace(execution_id) is None  # not this process

    response = TestClient(_app(OWNER)).get(f"/api/v1/orchestration/executions/{execution_id}/events")

    assert response.status_code == 200
    names = [name for name, _ in _events(response.text)]
    assert names == ["execution_event", "answer_fragment", "thought_fragment", "execution_event", "execution_event"]
    assert '"stage":"complete"' in _events(response.text)[-1][1]


def test_only_the_owner_or_an_administrator_may_watch(shared):
    execution_id = str(uuid.uuid4())
    _run_on_another_worker(execution_id)
    url = f"/api/v1/orchestration/executions/{execution_id}/events"

    assert TestClient(_app(STRANGER)).get(url).status_code == 403
    assert TestClient(_app(ADMIN)).get(url).status_code == 200


def test_an_id_nobody_opens_is_a_404_after_the_grace_period(shared):
    response = TestClient(_app(OWNER)).get(f"/api/v1/orchestration/executions/{uuid.uuid4()}/events")

    assert response.status_code == 404


def test_redis_down_when_subscribing_is_a_503(shared, monkeypatch):
    monkeypatch.setattr(shared_execution._READER, "_client", None)
    monkeypatch.setattr(shared_execution._READER, "_unavailable_until", float("inf"))

    response = TestClient(_app(OWNER)).get(f"/api/v1/orchestration/executions/{uuid.uuid4()}/events")

    assert response.status_code == 503


def test_the_tracker_and_the_stores_mirror_into_redis_without_the_question(shared):
    execution_id = str(uuid.uuid4())
    tracker = AgentExecutionTracker()
    tracker.start_execution(QUESTION, execution_id, user_id=OWNER.user_id)
    get_default_execution_event_store().publish(execution_id, ExecutionEvent(stage="route", status="completed"))
    get_default_answer_stream_store().publish(execution_id, "a draft")
    tracker.complete_execution(execution_id, {"answer": "the full final answer"})
    assert shared_execution.flush()

    meta = shared.hgetall(shared_execution.meta_key(execution_id))
    assert (meta["user_id"], meta["status"]) == (OWNER.user_id, "completed")
    kinds = [fields["kind"] for _, fields in shared.xrange(shared_execution.stream_key(execution_id))]
    assert kinds == ["event", "answer", "terminal"]
    assert 0 < shared.ttl(shared_execution.meta_key(execution_id)) <= shared_execution.FINISHED_TTL_S

    everything = " ".join(str(shared.dump(key)) for key in shared.keys("*"))
    assert "4471" not in everything
    assert "salary" not in everything
    assert "the full final answer" not in everything


def test_a_client_cannot_claim_an_id_another_worker_is_using(shared):
    from app.api.routes.public.query import _execution_id_taken

    execution_id = str(uuid.uuid4())
    shared_execution.open_execution(execution_id, "someone-else")
    assert shared_execution.flush()

    import asyncio

    assert asyncio.run(_execution_id_taken(AgentExecutionTracker(), execution_id)) is True
    assert asyncio.run(_execution_id_taken(AgentExecutionTracker(), str(uuid.uuid4()))) is False


def test_the_dashboard_counts_every_workers_stages_and_stores_no_error_text(shared, tmp_path):
    worker_a, worker_b = AgentExecutionTracker(), AgentExecutionTracker()
    execution_id = str(uuid.uuid4())
    worker_a.start_execution(QUESTION, execution_id, user_id=OWNER.user_id)
    now = utcnow()
    worker_a.record_finished_step(execution_id, "route", status="completed", duration_ms=12, finished_at=now)
    worker_a.record_finished_step(
        execution_id,
        "knowledge",
        status="failed",
        duration_ms=30,
        finished_at=now + timedelta(milliseconds=50),
        error="RetrievalFailureError: nothing found for salary of employee 4471",
    )
    worker_a._shared_stage_stats().flush()

    stats = worker_b.get_quality_stats()  # the other worker, which saw none of it

    assert stats["summary"]["total_executions"] == 2
    assert {agent["agent_name"] for agent in stats["agents"]} == {"route", "knowledge"}
    assert stats["error_distribution"] == {"RetrievalFailureError": 1}
    with sqlite3.connect(tmp_path / "app.db") as conn:
        rows = conn.execute("SELECT * FROM execution_stage_stats").fetchall()
    assert len(rows) == 2
    assert "4471" not in str(rows)


def test_clearing_the_dashboard_clears_what_every_worker_recorded(shared):
    worker_a, worker_b = AgentExecutionTracker(), AgentExecutionTracker()
    execution_id = str(uuid.uuid4())
    worker_a.start_execution(QUESTION, execution_id, user_id=OWNER.user_id)
    worker_a.record_finished_step(execution_id, "route", status="completed", duration_ms=1, finished_at=utcnow())
    worker_a._shared_stage_stats().flush()

    worker_b.clear_all_traces()

    assert worker_a.get_quality_stats()["summary"]["total_executions"] == 0


def test_waiting_subscriptions_are_capped_per_user():
    """Any signed-in user could otherwise park unbounded waits on random ids (ARC-02)."""

    from fastapi import HTTPException

    held = [orchestration_module._PendingSubscription(OWNER) for _ in range(4)]
    for subscription in held:
        subscription.__enter__()
    try:
        one_too_many = orchestration_module._PendingSubscription(OWNER)
        with pytest.raises(HTTPException) as refused:
            one_too_many.__enter__()
        assert refused.value.status_code == 429
        orchestration_module._PendingSubscription(STRANGER).__enter__()  # someone else is unaffected
        orchestration_module._PendingSubscription(STRANGER).__exit__(None, None, None)
    finally:
        for subscription in held:
            subscription.__exit__(None, None, None)
    assert orchestration_module._pending_subscriptions == {}


def test_the_stream_no_longer_repeats_each_stage_as_a_mislabelled_rag_event(monkeypatch):
    """Tracker steps were the same stage events again, relabelled: six of ten became `rag`."""

    empty_stores = (ExecutionEventStore(), AnswerStreamStore(), AnswerStreamStore())
    event_store = empty_stores[0]
    execution_id = str(uuid.uuid4())
    tracker = AgentExecutionTracker.get_instance()
    tracker.start_execution(QUESTION, execution_id, user_id=OWNER.user_id)
    for stage in ("privacy_permission", "route", "knowledge", "verifier"):
        event_store.publish(execution_id, ExecutionEvent(stage=stage, status="completed"))
        tracker.record_finished_step(execution_id, stage, status="completed", duration_ms=1, finished_at=utcnow())
    tracker.complete_execution(execution_id)

    app = _app(OWNER)
    app.dependency_overrides[get_execution_event_store] = lambda: event_store
    body = TestClient(app).get(f"/api/v1/orchestration/executions/{execution_id}/events").text
    stages = [data.split('"stage":"')[1].split('"')[0] for name, data in _events(body) if name == "execution_event"]

    assert stages == ["privacy_permission", "route", "knowledge", "verifier", "complete"]
