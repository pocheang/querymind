"""Fixtures for the contract suites (ARC-01 phase 10).

Each suite in this directory runs one set of behavioural assertions against both
implementations of something a caller cannot tell apart: the per-process one
and the shared one that STATE_BACKEND=shared (or a backend setting) swaps in. A
property that holds for one and not the other is a deployment whose behaviour
depends on a switch nobody connected to the difference -- which is how the two
fixed in this phase were found.

The Redis side is fakeredis, which executes the real commands and the real Lua.
Every path is under tmp_path and the runtime settings file is empty, so nothing
here reads the developer's `.runtime/` or writes their `data/`.
"""

from __future__ import annotations

import pytest

fakeredis = pytest.importorskip("fakeredis")

from app.core.config import get_settings  # noqa: E402


@pytest.fixture
def settings_env(tmp_path, monkeypatch):
    """Isolated Settings: an empty runtime file, every store under tmp_path. Returns a setter."""

    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    base = {
        "RUNTIME_ENV_FILE": str(empty),
        "NACOS_ENABLED": "false",
        "API_SETTINGS_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef0123456789abcdef",
        "APP_DB_PATH": str(tmp_path / "app.db"),
        "DATABASE_URL": f"sqlite:///{(tmp_path / 'querymind.db').as_posix()}",
        "SESSIONS_DIR": str(tmp_path / "sessions"),
        "HISTORY_COLD_DIR": str(tmp_path / "sessions_cold"),
        "HISTORY_SQLITE_PATH": str(tmp_path / "history.db"),
        "CHROMA_PERSIST_DIR": str(tmp_path / "chroma"),
    }

    def apply(**values: str) -> None:
        for key, value in {**base, **values}.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()

    apply()
    yield apply
    get_settings.cache_clear()


@pytest.fixture
def fake_server():
    return fakeredis.FakeServer()


@pytest.fixture
def sync_redis(fake_server):
    return fakeredis.FakeRedis(server=fake_server, decode_responses=True)


@pytest.fixture
def async_redis(fake_server):
    return fakeredis.aioredis.FakeRedis(server=fake_server, decode_responses=True)


@pytest.fixture
def install(monkeypatch):
    """Hand a connector a working client, as if it had connected and pinged."""

    def hand_over(connector, client) -> None:
        monkeypatch.setattr(connector, "_client", client)
        monkeypatch.setattr(connector, "_unavailable_until", 0.0)

    return hand_over
