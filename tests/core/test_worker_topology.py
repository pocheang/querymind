from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings, validate_worker_topology


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Isolate from ambient .runtime/*.env or developer machine environment."""
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.delenv("APP_WORKERS", raising=False)
    monkeypatch.delenv("app_workers", raising=False)
    monkeypatch.setenv("NACOS_ENABLED", "false")
    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef")
    get_settings.cache_clear()
    yield empty_env
    get_settings.cache_clear()


def test_default_settings_has_one_worker_and_validation_passes():
    settings = Settings()
    assert settings.app_workers == 1
    validate_worker_topology(settings)


def test_worker_topology_rejects_more_than_one_worker(monkeypatch):
    monkeypatch.setenv("APP_WORKERS", "2")
    settings = Settings()
    assert settings.app_workers == 2

    with pytest.raises(RuntimeError) as exc_info:
        validate_worker_topology(settings)

    message = str(exc_info.value)
    assert "APP_WORKERS" in message
    assert "2" in message
    assert "ARC-01" in message


def test_worker_topology_rejects_zero_workers():
    with pytest.raises(ValidationError):
        Settings(APP_WORKERS=0)


def test_lifespan_wires_worker_topology_validation(monkeypatch):
    from fastapi.testclient import TestClient

    import app.api.application.lifespan as lifespan_module
    import app.api.dependencies as api_dependencies
    from app.api.main import app

    seen = []
    monkeypatch.setattr(lifespan_module, "validate_worker_topology", lambda s: seen.append(s))

    with TestClient(app):
        pass

    expected_settings = api_dependencies.get_query_runtime().settings
    assert len(seen) == 1
    assert seen[0] is expected_settings
