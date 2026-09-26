"""A log level set from the admin console reaches every worker (ARC-01 phase 8).

`POST /admin/ops/logging/level` changed only the worker that took the request.
With STATE_BACKEND=shared the level is stored in Redis and announced through
the phase 6 generation counters (`log_levels`); the other workers apply it on
their next request, and a worker that starts later applies it at startup.

"Another worker" is simulated the way the phase 6 tests do it: write Redis the
way that worker would, and increment the generation it would have announced.
"""

from __future__ import annotations

import logging

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.runtime import invalidation, shared_log_levels
from app.services.runtime.shared_state import SharedStateUnavailable

LOGGER = "qm.test.log_levels"
ADMIN = {"X-Test-User": "ops-admin", "X-Test-User-Id": "ops-admin", "X-Test-Role": "admin"}


@pytest.fixture
def levels_restored():
    root = logging.getLogger()
    saved_root, saved = root.level, logging.getLogger(LOGGER).level
    yield
    root.setLevel(saved_root)
    logging.getLogger(LOGGER).setLevel(saved)


@pytest.fixture
def shared(tmp_path, monkeypatch, levels_restored):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    get_settings.cache_clear()
    server = fakeredis.FakeRedis(decode_responses=True)
    for module in (invalidation, shared_log_levels):
        monkeypatch.setattr(module, "is_shared", lambda: True)
        monkeypatch.setattr(module, "shared_client", lambda: server)
    invalidation.reset_for_tests()
    yield server
    invalidation.reset_for_tests()
    get_settings.cache_clear()


def _key() -> str:
    return shared_log_levels._key()


def _another_worker_sets(server, logger_name: str, level: str) -> None:
    server.hset(_key(), logger_name, level)
    server.incr("qm:gen:log_levels")


def test_a_level_another_worker_set_is_applied_here_on_the_next_request(shared):
    invalidation.catch_up()
    _another_worker_sets(shared, LOGGER, "DEBUG")

    assert invalidation.catch_up() == ["log_levels"]
    assert logging.getLogger(LOGGER).level == logging.DEBUG


def test_a_reset_another_worker_published_is_applied_here(shared):
    logging.getLogger(LOGGER).setLevel(logging.DEBUG)
    invalidation.catch_up()
    shared.delete(_key())
    shared.incr("qm:gen:log_levels")

    invalidation.catch_up()

    assert logging.getLogger(LOGGER).level == logging.NOTSET
    assert logging.getLogger().level == logging.INFO


def test_publishing_stores_the_level_and_announces_it(shared):
    shared_log_levels.publish_level(LOGGER, "ERROR")

    assert shared.hgetall(_key()) == {LOGGER: "ERROR"}
    assert shared.get("qm:gen:log_levels") == "1"


def test_a_worker_starting_later_applies_stored_levels_without_resetting_its_own(shared):
    shared.hset(_key(), LOGGER, "DEBUG")
    logging.getLogger().setLevel(logging.WARNING)  # this process's own configuration

    shared_log_levels.apply_stored_levels(reset_first=False)

    assert logging.getLogger(LOGGER).level == logging.DEBUG
    assert logging.getLogger().level == logging.WARNING


def test_the_endpoint_changes_nothing_anywhere_when_redis_does_not_answer(levels_restored, monkeypatch):
    from app.api import main
    from app.api.routes.admin import ops as ops_route

    def unavailable():
        raise SharedStateUnavailable("shared state store (Redis) is unavailable")

    monkeypatch.setattr(shared_log_levels, "is_shared", lambda: True)
    monkeypatch.setattr(shared_log_levels, "shared_client", unavailable)
    monkeypatch.setattr(ops_route, "is_shared", lambda: True)
    logging.getLogger(LOGGER).setLevel(logging.WARNING)

    response = TestClient(main.app).post(
        "/admin/ops/logging/level", json={"logger": LOGGER, "level": "DEBUG"}, headers=ADMIN
    )

    assert response.status_code == 503
    assert logging.getLogger(LOGGER).level == logging.WARNING


def test_the_endpoint_says_which_processes_a_change_reaches(levels_restored):
    from app.api import main

    body = (
        TestClient(main.app)
        .post("/admin/ops/logging/level", json={"logger": LOGGER, "level": "INFO"}, headers=ADMIN)
        .json()
    )

    assert body["applies_to"] == "this_process"  # memory mode: one process
    assert logging.getLogger(LOGGER).level == logging.INFO


def test_in_shared_mode_the_endpoint_says_the_change_reaches_every_worker(shared, monkeypatch):
    from app.api import main
    from app.api.routes.admin import ops as ops_route

    monkeypatch.setattr(ops_route, "is_shared", lambda: True)

    body = (
        TestClient(main.app)
        .post("/admin/ops/logging/level", json={"logger": LOGGER, "level": "ERROR"}, headers=ADMIN)
        .json()
    )

    assert body["applies_to"] == "all_workers"
    assert shared.hgetall(_key()) == {LOGGER: "ERROR"}
