"""STATE_BACKEND=shared refuses to start without a Redis that answers (ARC-01 phase 1).

Shared state that quietly falls back to process memory is the ARC-01 defect
itself, so the switch is only worth having if turning it on against a dead Redis
fails loudly at startup rather than at the first cross-worker request.
"""

from __future__ import annotations

import pytest

import app.api.application.lifespan as lifespan_module
from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    # The real lifespan builds the governed tool stack, which needs a key.
    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef")
    monkeypatch.delenv("STATE_BACKEND", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _probe_calls(monkeypatch, answer: str | None) -> list[str]:
    import app.services.runtime.redis_connector as connector_module

    calls: list[str] = []

    def fake_probe(url: str, *, timeout: float = 3.0) -> str | None:
        calls.append(url)
        return answer

    monkeypatch.setattr(connector_module, "probe", fake_probe)
    return calls


def test_the_default_is_memory_and_needs_no_redis(monkeypatch):
    calls = _probe_calls(monkeypatch, "should not be asked")
    settings = Settings()

    assert settings.state_backend == "memory"
    lifespan_module._require_reachable_shared_state(settings)
    assert calls == []


def test_shared_with_an_answering_redis_starts(monkeypatch):
    calls = _probe_calls(monkeypatch, None)
    settings = Settings(STATE_BACKEND="shared", REDIS_URL="redis://:hunter2@cache:6379/0")

    lifespan_module._require_reachable_shared_state(settings)
    assert calls == ["redis://:hunter2@cache:6379/0"]


def test_shared_without_redis_refuses_and_does_not_print_the_url(monkeypatch):
    _probe_calls(monkeypatch, "ConnectionError: Connection refused")
    settings = Settings(STATE_BACKEND="shared", REDIS_URL="redis://:hunter2@cache:6379/0")

    with pytest.raises(RuntimeError) as excinfo:
        lifespan_module._require_reachable_shared_state(settings)

    message = str(excinfo.value)
    assert "STATE_BACKEND=shared" in message
    assert "Connection refused" in message
    assert "hunter2" not in message, "the Redis URL can carry its password"


def test_an_unknown_backend_is_rejected():
    with pytest.raises(ValueError):
        Settings(STATE_BACKEND="redis")


def test_the_lifespan_runs_the_check(monkeypatch):
    """Written as a spy on the real lifespan: the check is worth nothing unless startup calls it."""

    from fastapi.testclient import TestClient

    import app.api.dependencies as api_dependencies
    from app.api.main import app

    seen = []
    monkeypatch.setattr(lifespan_module, "_require_reachable_shared_state", lambda s: seen.append(s))

    with TestClient(app):
        pass

    assert seen == [api_dependencies.get_query_runtime().settings]
