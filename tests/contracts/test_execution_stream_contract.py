"""A run's SSE stream says the same thing whether it came from memory or from Redis (ARC-01 phase 10).

The pipeline writes through the same entry points in both modes -- the tracker
and the process-wide event, answer and thought stores -- and the SSE endpoint
reads this process's stores (STATE_BACKEND=memory) or the run's Redis stream
(shared, where the subscriber may be on another worker and holds nothing).
Here one producer drives those entry points and the endpoint is read both ways.

What the contract is, and what it deliberately is not: every stage event,
answer fragment and thought fragment arrives, each channel in the order it was
written, and the terminal event last. The *interleaving across* channels is not
part of it. Redis keeps one stream in write order; memory mode polls three
stores every 50ms and emits each poll channel by channel, so a completed run
replayed from memory comes back grouped. The client renders the stage timeline
and the draft answer separately, so nothing reads the interleaving -- which is
why the plan kept memory mode on polling, and why pinning it either way would
be a contract nothing depends on.
"""

from __future__ import annotations

import json
import threading
import time
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.application.factory import shared_state_unavailable
from app.api.deps.runtime import (
    get_answer_stream_store,
    get_execution_event_store,
    get_thought_stream_store,
    require_trace_actor,
)
from app.api.routes.public import orchestration as orchestration_module
from app.domain.events import ExecutionEvent
from app.orchestration import shared_execution
from app.orchestration.answer_stream import (
    AnswerStreamStore,
    get_default_answer_stream_store,
    get_default_thought_stream_store,
)
from app.orchestration.execution_events import ExecutionEventStore, get_default_execution_event_store
from app.orchestration.request import RequestActor
from app.services.observability.agent_execution_tracker import AgentExecutionTracker
from app.services.runtime import shared_state

OWNER = RequestActor(user_id="u-owner", role="viewer")
STRANGER = RequestActor(user_id="u-stranger", role="viewer")
ADMIN = RequestActor(user_id="u-admin", role="admin")


@pytest.fixture(params=["memory", "shared"])
def mode(request, settings_env, fake_server, sync_redis, install, monkeypatch) -> str:
    import fakeredis

    settings_env(STATE_BACKEND=request.param)
    monkeypatch.setattr(orchestration_module, "_SUBSCRIBE_GRACE_SECONDS", 0.4)
    if request.param == "shared":
        install(shared_state._CONNECTOR, sync_redis)
        install(shared_execution._READER, fakeredis.aioredis.FakeRedis(server=fake_server, decode_responses=True))
    yield request.param
    if request.param == "shared":
        shared_execution.flush()


def _app(mode: str, actor: RequestActor) -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(shared_state.SharedStateUnavailable, shared_state_unavailable)
    app.include_router(orchestration_module.router)
    app.dependency_overrides[require_trace_actor] = lambda: actor
    if mode == "shared":
        # Another worker: none of this run is in its own stores.
        app.dependency_overrides[get_execution_event_store] = ExecutionEventStore
        app.dependency_overrides[get_answer_stream_store] = AnswerStreamStore
        app.dependency_overrides[get_thought_stream_store] = AnswerStreamStore
    else:
        # The same process: the app's services hand out these very instances
        # (`build_app_services`), which is how the pipeline and the SSE route meet.
        app.dependency_overrides[get_execution_event_store] = get_default_execution_event_store
        app.dependency_overrides[get_answer_stream_store] = get_default_answer_stream_store
        app.dependency_overrides[get_thought_stream_store] = get_default_thought_stream_store
    return app


def _produce(execution_id: str, *, fail: bool = False) -> None:
    """What the pipeline does, through the functions it calls, in either mode."""

    tracker = AgentExecutionTracker.get_instance()
    events = get_default_execution_event_store()
    tracker.start_execution("what is the retention window?", execution_id, user_id=OWNER.user_id)
    events.publish(execution_id, ExecutionEvent(stage="route", status="completed", duration_ms=5))
    get_default_answer_stream_store().publish(execution_id, "Backups are ")
    get_default_thought_stream_store().publish(execution_id, "checking policy")
    events.publish(execution_id, ExecutionEvent(stage="knowledge", status="completed", duration_ms=9))
    get_default_answer_stream_store().publish(execution_id, "kept 35 days.")
    if fail:
        tracker.fail_execution(execution_id, "synthesis failed")
    else:
        tracker.complete_execution(execution_id)
    shared_execution.flush()


def _messages(body: str) -> list[tuple[str, dict | str]]:
    out = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        data = fields.get("data", "")
        out.append((fields.get("event", ""), json.loads(data) if data.startswith("{") else data))
    return out


def _channels(body: str) -> dict[str, list]:
    channels: dict[str, list] = {"execution_event": [], "answer_fragment": [], "thought_fragment": []}
    for name, data in _messages(body):
        if name == "execution_event":
            channels[name].append((data["stage"], data["status"]))
        else:
            channels[name].append(data["text"])
    return channels


def _url(execution_id: str) -> str:
    return f"/api/v1/orchestration/executions/{execution_id}/events"


def test_every_message_arrives_each_channel_in_order_terminal_last(mode):
    execution_id = str(uuid.uuid4())
    _produce(execution_id)

    response = TestClient(_app(mode, OWNER)).get(_url(execution_id))

    assert response.status_code == 200
    assert _channels(response.text) == {
        "execution_event": [("route", "completed"), ("knowledge", "completed"), ("complete", "completed")],
        "answer_fragment": ["Backups are ", "kept 35 days."],
        "thought_fragment": ["checking policy"],
    }
    assert _messages(response.text)[-1][1]["stage"] == "complete"


def test_a_failed_run_ends_with_a_failed_terminal(mode):
    execution_id = str(uuid.uuid4())
    _produce(execution_id, fail=True)

    messages = _messages(TestClient(_app(mode, OWNER)).get(_url(execution_id)).text)

    assert messages[-1][0] == "execution_event"
    assert messages[-1][1]["status"] == "failed"


def test_a_subscription_opened_before_the_run_receives_all_of_it(mode):
    """The point of a client-chosen execution id: subscribe first, then ask."""

    execution_id = str(uuid.uuid4())
    received = {}

    def subscribe():
        received["response"] = TestClient(_app(mode, OWNER)).get(_url(execution_id))

    subscriber = threading.Thread(target=subscribe)
    subscriber.start()
    time.sleep(0.1)
    _produce(execution_id)
    subscriber.join(15)

    assert received["response"].status_code == 200
    assert [stage for stage, _ in _channels(received["response"].text)["execution_event"]] == [
        "route",
        "knowledge",
        "complete",
    ]


def test_only_the_owner_or_an_administrator_may_watch(mode):
    execution_id = str(uuid.uuid4())
    _produce(execution_id)

    assert TestClient(_app(mode, STRANGER)).get(_url(execution_id)).status_code == 403
    assert TestClient(_app(mode, ADMIN)).get(_url(execution_id)).status_code == 200


def test_an_id_nobody_opens_is_a_404_after_the_grace_period(mode):
    started = time.monotonic()

    response = TestClient(_app(mode, OWNER)).get(_url(str(uuid.uuid4())))

    assert response.status_code == 404
    assert time.monotonic() - started >= 0.3
