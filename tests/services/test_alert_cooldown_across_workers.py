"""One incident reaches an alert channel once, however many workers see it (ARC-01 audit, 2026-09-25).

The cooldown that keeps a repeating trigger from spamming a channel lived in
each process's `_LAST_SENT` dict, so with N workers one incident was sent N
times -- a category-A state in the phase 0 inventory that the plan's table
never picked up. With STATE_BACKEND=shared the cooldown is a Redis key claimed
with SET NX.

"Another worker" is modelled the only way that matters: a process whose own
`_LAST_SENT` is empty.
"""

from __future__ import annotations

import time

import pytest

fakeredis = pytest.importorskip("fakeredis")

from app.core.config import get_settings  # noqa: E402
from app.services.observability import alerting  # noqa: E402
from app.services.runtime import shared_state  # noqa: E402


@pytest.fixture
def settings(tmp_path, monkeypatch):
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")

    def apply(**values: str) -> None:
        for key, value in {"RUNTIME_ENV_FILE": str(empty), "NACOS_ENABLED": "false", **values}.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()

    monkeypatch.setattr(alerting, "_LAST_SENT", {})
    yield apply
    get_settings.cache_clear()


@pytest.fixture
def redis(monkeypatch):
    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    monkeypatch.setattr(shared_state._CONNECTOR, "_client", client)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", 0.0)
    return client


def _another_worker() -> None:
    alerting._LAST_SENT.clear()


def test_a_second_worker_stays_quiet_inside_the_cooldown(settings, redis):
    settings(STATE_BACKEND="shared", ALERT_MIN_INTERVAL_SECONDS="60")

    assert alerting._rate_limit_ok("webhook:index_failed") is True
    _another_worker()

    assert alerting._rate_limit_ok("webhook:index_failed") is False


def test_channels_and_events_are_separate_cooldowns(settings, redis):
    settings(STATE_BACKEND="shared", ALERT_MIN_INTERVAL_SECONDS="60")
    alerting._rate_limit_ok("webhook:index_failed")
    _another_worker()

    assert alerting._rate_limit_ok("slack:index_failed") is True
    assert alerting._rate_limit_ok("webhook:reindex_failed") is True


def test_the_cooldown_ends(settings, redis):
    settings(STATE_BACKEND="shared", ALERT_MIN_INTERVAL_SECONDS="1")
    alerting._rate_limit_ok("webhook:index_failed")
    _another_worker()

    time.sleep(1.2)

    assert alerting._rate_limit_ok("webhook:index_failed") is True


def test_without_redis_the_local_cooldown_still_holds(settings, monkeypatch):
    """An alert is often about the outage; a duplicate beats silence, but not a flood."""

    settings(STATE_BACKEND="shared", ALERT_MIN_INTERVAL_SECONDS="60")
    monkeypatch.setattr(shared_state._CONNECTOR, "_client", None)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", float("inf"))

    assert alerting._rate_limit_ok("webhook:redis_down") is True
    assert alerting._rate_limit_ok("webhook:redis_down") is False


def test_memory_mode_keeps_the_cooldown_in_the_process(settings, redis):
    settings(STATE_BACKEND="memory", ALERT_MIN_INTERVAL_SECONDS="60")

    assert alerting._rate_limit_ok("webhook:index_failed") is True
    assert alerting._rate_limit_ok("webhook:index_failed") is False
    assert redis.keys("*") == []


def test_the_channel_receives_one_post_from_two_workers(settings, redis, monkeypatch):
    settings(
        STATE_BACKEND="shared",
        ALERT_MIN_INTERVAL_SECONDS="60",
        ALERTING_ENABLED="true",
        ALERT_WEBHOOK_URL="https://alerts.example.com/hook",
    )
    monkeypatch.setattr(alerting, "_is_webhook_allowed", lambda url: True)
    posts = []

    class _Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> None:
            return None

        def post(self, url, json):
            posts.append((url, json["event_type"]))
            return type("Response", (), {"raise_for_status": lambda self: None})()

    monkeypatch.setattr(alerting.httpx, "Client", _Client)

    sent = [alerting.emit_alert("index_failed", {"n": 1})]
    _another_worker()
    sent.append(alerting.emit_alert("index_failed", {"n": 2}))

    assert sent == [True, False]
    assert posts == [("https://alerts.example.com/hook", "index_failed")]
