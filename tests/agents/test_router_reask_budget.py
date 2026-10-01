"""The low-confidence re-ask runs only when it can finish (PERF-03).

A routing call was measured at 3-4 s against an 8 s router stage ceiling, so a
second, reasoning-model call after a slow first one could not finish: the stage
timed out and took the safe route anyway, and the abandoned call kept a pool
thread busy. The re-ask now runs only when the first call's duration -- a floor
on the second's -- fits in what is left of both the stage ceiling and the
caller's deadline.

And a decision shaped by one request's lack of time is not cached: the router
memo is per question for thirty minutes, so caching it would hand the safe
route to every later caller of the same question, however much time they had.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.agents.router import routing
from app.agents.shared.cache import clear_router_decision_cache
from app.services.runtime.request_context import request_context

UNSURE = {"route": "graph", "reason": "maybe", "confidence": 0.1}
SURE = {"route": "hybrid", "reason": "second opinion", "confidence": 0.9}


class _Clock:
    """`time.monotonic` for routing, advanced by the fake models."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


class _Model:
    def __init__(self, payload: dict, clock: _Clock, seconds: float) -> None:
        self.payload, self.clock, self.seconds = payload, clock, seconds
        self.calls = 0

    def invoke(self, prompt):
        del prompt
        self.calls += 1
        self.clock.now += self.seconds
        return SimpleNamespace(content=json.dumps(self.payload))


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(routing.time, "monotonic", fake)
    clear_router_decision_cache()
    monkeypatch.setattr(routing, "_get_calibrator", lambda: None)
    monkeypatch.setattr(routing, "classify_agent_class", lambda question: "general")
    monkeypatch.setattr(
        routing,
        "get_settings",
        lambda: SimpleNamespace(enable_web_route_downgrade=False, stage_timeout_route_ms=8_000),
    )
    yield fake
    clear_router_decision_cache()


def _models(monkeypatch, clock: _Clock, *, first_seconds: float) -> tuple[_Model, _Model]:
    chat = _Model(UNSURE, clock, first_seconds)
    reasoning = _Model(SURE, clock, 1.0)
    monkeypatch.setattr(routing, "get_chat_model", lambda: chat)
    monkeypatch.setattr(routing, "get_reasoning_model", lambda: reasoning)
    return chat, reasoning


def test_a_fast_first_call_still_gets_its_second_opinion(monkeypatch, clock):
    _, reasoning = _models(monkeypatch, clock, first_seconds=1.0)

    decision = routing.decide_route("how are the services related")

    assert reasoning.calls == 1
    assert decision.route == "hybrid"
    assert decision.cacheable is True


def test_a_slow_first_call_leaves_no_room_in_the_router_stage(monkeypatch, clock):
    # 5 s spent of an 8 s stage: a re-ask at least as long cannot finish.
    _, reasoning = _models(monkeypatch, clock, first_seconds=5.0)

    decision = routing.decide_route("how are the services related")

    assert reasoning.calls == 0
    assert decision.route == routing.ROUTE_VECTOR
    assert routing.REASK_SKIPPED_FOR_BUDGET in decision.reason
    assert decision.raw_confidence == pytest.approx(0.5)


def test_the_callers_deadline_bounds_it_too(monkeypatch, clock):
    _, reasoning = _models(monkeypatch, clock, first_seconds=1.0)

    with request_context(timeout_ms=500, overload_mode=False):
        decision = routing.decide_route("how are the services related")

    assert reasoning.calls == 0
    assert routing.REASK_SKIPPED_FOR_BUDGET in decision.reason


def test_a_decision_skipped_for_time_is_not_served_to_the_next_caller(monkeypatch, clock):
    chat, reasoning = _models(monkeypatch, clock, first_seconds=5.0)
    routing.decide_route("how are the services related")

    chat.seconds = 1.0
    decision = routing.decide_route("how are the services related")

    assert chat.calls == 2
    assert reasoning.calls == 1
    assert decision.route == "hybrid"


def test_a_failed_call_is_not_cached_either(monkeypatch, clock):
    class _Broken:
        calls = 0

        def invoke(self, prompt):
            del prompt
            self.calls += 1
            raise TimeoutError

    broken = _Broken()
    monkeypatch.setattr(routing, "get_chat_model", lambda: broken)

    first = routing.decide_route("what changed in the backup policy")
    routing.decide_route("what changed in the backup policy")

    assert "router_invoke_error" in first.reason
    assert first.cacheable is False
    assert broken.calls == 2


def test_a_normal_decision_is_still_cached(monkeypatch, clock):
    chat, _ = _models(monkeypatch, clock, first_seconds=1.0)
    chat.payload = SURE

    routing.decide_route("how are the services related")
    routing.decide_route("how are the services related")

    assert chat.calls == 1
