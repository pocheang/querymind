"""One Redis client per purpose: opened once, dropped on failure, retried after a cooldown.

Every request asks for a client, so a Redis that is down must cost one connection
attempt per cooldown rather than one per request -- at a 5s connect timeout,
retrying per request turns an unavailable dependency into an outage.

These properties were pinned for the query guard alone
(`test_query_guard_redis_client.py`). Five other modules held their own client
and disagreed about them: the retrieval cache had no cooldown, OAuth state built
a pool per call, the async rate limiter never retried after its first failure,
and the async L2 cache never dropped a broken client. They all hold a connector
now, so the properties are pinned once, here, for both flavours.
"""

from __future__ import annotations

import asyncio
import sys
import types

from app.services.runtime import redis_connector as rc
from app.services.runtime.redis_connector import AsyncRedisConnector, RedisConnector, connector_status


class _FakeClient:
    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self.ping_error = ping_error
        self.closed = False

    def ping(self) -> bool:
        if self.ping_error is not None:
            raise self.ping_error
        return True

    def close(self) -> None:
        self.closed = True


class _FakeAsyncClient:
    def __init__(self, *, ping_error: Exception | None = None) -> None:
        self.ping_error = ping_error
        self.closed = False

    async def ping(self) -> bool:
        if self.ping_error is not None:
            raise self.ping_error
        return True

    async def aclose(self) -> None:
        self.closed = True


def _install_redis(monkeypatch, client, *, error: Exception | None = None, async_client=None):
    """Stand a fake `redis` (and `redis.asyncio`) in front of the connector's import."""

    calls: list[dict] = []

    def from_url(url: str, **kwargs):
        calls.append({"url": url, **kwargs})
        if error is not None:
            raise error
        return client

    def async_from_url(url: str, **kwargs):
        calls.append({"url": url, **kwargs})
        if error is not None:
            raise error
        return async_client

    fake_async = types.SimpleNamespace(from_url=async_from_url)
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(from_url=from_url, asyncio=fake_async))
    monkeypatch.setitem(sys.modules, "redis.asyncio", fake_async)
    return calls


def _connector(**options) -> RedisConnector:
    return RedisConnector("test_sync", url=lambda: "redis://unit-test:6379/0", **options)


def _async_connector() -> AsyncRedisConnector:
    return AsyncRedisConnector("test_async", url=lambda: "redis://unit-test:6379/0")


# ---- synchronous -----------------------------------------------------------


def test_the_client_is_opened_once_and_reused(monkeypatch):
    client = _FakeClient()
    calls = _install_redis(monkeypatch, client)
    connector = _connector()

    assert connector.client() is client
    assert connector.client() is client
    assert len(calls) == 1


def test_the_options_and_url_reach_the_client(monkeypatch):
    calls = _install_redis(monkeypatch, _FakeClient())
    _connector(socket_timeout=0.2, decode_responses=True).client()

    assert calls == [{"url": "redis://unit-test:6379/0", "socket_timeout": 0.2, "decode_responses": True}]


def test_a_connection_failure_starts_a_cooldown_instead_of_retrying(monkeypatch):
    calls = _install_redis(monkeypatch, None, error=OSError("connection refused"))
    connector = _connector()

    assert connector.client() is None
    assert connector.client() is None
    assert len(calls) == 1  # the second call is inside the cooldown


def test_a_client_that_will_not_answer_ping_is_closed_rather_than_kept(monkeypatch):
    """from_url can succeed while the connection never worked, leaving a client to clean up."""

    client = _FakeClient(ping_error=OSError("no route to host"))
    _install_redis(monkeypatch, client)

    assert _connector().client() is None
    assert client.closed


def test_redis_not_installed_is_routine_and_also_cools_down(monkeypatch):
    calls = _install_redis(monkeypatch, None, error=ImportError("no module named redis"))
    connector = _connector()

    assert connector.client() is None
    assert connector.client() is None
    assert len(calls) == 1


def test_the_cooldown_expires_and_the_next_call_tries_again(monkeypatch):
    client = _FakeClient()
    calls = _install_redis(monkeypatch, client)
    connector = _connector()
    connector._unavailable_until = 1.0
    monkeypatch.setattr(rc.time, "monotonic", lambda: 0.5)

    assert connector.client() is None  # still cooling
    assert calls == []

    monkeypatch.setattr(rc.time, "monotonic", lambda: 2.0)
    assert connector.client() is client
    assert len(calls) == 1


def test_a_dropped_client_is_closed_and_not_handed_out_again(monkeypatch):
    """A failed command must cost the next request nothing: no client, and no reconnect yet."""

    client = _FakeClient()
    calls = _install_redis(monkeypatch, client)
    connector = _connector()
    assert connector.client() is client

    connector.drop(OSError("reset by peer"))

    assert client.closed
    assert connector.client() is None
    assert len(calls) == 1


def test_status_reports_what_the_connector_knows_without_connecting(monkeypatch):
    calls = _install_redis(monkeypatch, _FakeClient())
    connector = _connector()

    assert connector.status()["state"] == "not_connected"
    connector.client()
    assert connector.status()["state"] == "connected"
    connector.drop("boom")
    status = connector.status()
    assert status["state"] == "cooling_down"
    assert status["last_error"] == "boom"
    assert 0 < status["cooldown_remaining_s"] <= rc.COOLDOWN_SECONDS
    assert len(calls) == 1, "asking for status must never open a connection"


def test_connectors_are_listed_by_name_and_a_rebuilt_one_replaces_the_old(monkeypatch):
    _install_redis(monkeypatch, _FakeClient())
    first = RedisConnector("listing_probe", url=lambda: "redis://unit-test/0")
    second = RedisConnector("listing_probe", url=lambda: "redis://unit-test/0")
    second.client()

    listed = [status for status in connector_status() if status["name"] == "listing_probe"]
    assert listed == [second.status()]
    assert first is not second


# ---- asynchronous ----------------------------------------------------------


def test_async_client_is_opened_once_and_reused(monkeypatch):
    client = _FakeAsyncClient()
    calls = _install_redis(monkeypatch, None, async_client=client)
    connector = _async_connector()

    async def scenario():
        return await connector.client(), await connector.client()

    assert asyncio.run(scenario()) == (client, client)
    assert len(calls) == 1


def test_async_failure_cools_down_and_then_retries(monkeypatch):
    """The async rate limiter never retried after its first failure; this is the property it lacked."""

    client = _FakeAsyncClient(ping_error=OSError("connection refused"))
    calls = _install_redis(monkeypatch, None, async_client=client)
    connector = _async_connector()

    assert asyncio.run(connector.client()) is None
    assert client.closed
    assert asyncio.run(connector.client()) is None
    assert len(calls) == 1  # inside the cooldown

    healthy = _FakeAsyncClient()
    _install_redis(monkeypatch, None, async_client=healthy)
    monkeypatch.setattr(rc.time, "monotonic", lambda: connector._unavailable_until + 1)
    assert asyncio.run(connector.client()) is healthy


def test_async_drop_closes_the_client_and_starts_a_cooldown(monkeypatch):
    client = _FakeAsyncClient()
    calls = _install_redis(monkeypatch, None, async_client=client)
    connector = _async_connector()

    async def scenario():
        assert await connector.client() is client
        await connector.drop(OSError("reset"))
        return await connector.client()

    assert asyncio.run(scenario()) is None
    assert client.closed
    assert len(calls) == 1


def test_async_close_at_shutdown_does_not_start_a_cooldown(monkeypatch):
    client = _FakeAsyncClient()
    _install_redis(monkeypatch, None, async_client=client)
    connector = _async_connector()

    async def scenario():
        await connector.client()
        await connector.close()

    asyncio.run(scenario())
    assert client.closed
    assert connector.status()["state"] == "not_connected"


# ---- probe -----------------------------------------------------------------


def test_probe_uses_the_whole_url_including_the_password(monkeypatch):
    """The readiness check rebuilt the client from host and port, and lost the password."""

    client = _FakeClient()
    calls = _install_redis(monkeypatch, client)

    assert rc.probe("redis://:s3cret@cache:6380/2") is None
    assert calls[0]["url"] == "redis://:s3cret@cache:6380/2"
    assert client.closed, "a probe must not leave a connection behind"


def test_probe_reports_why_redis_did_not_answer(monkeypatch):
    _install_redis(monkeypatch, _FakeClient(ping_error=OSError("NOAUTH Authentication required.")))

    assert rc.probe("redis://cache:6379/0") == "OSError: NOAUTH Authentication required."


# ---- the six callers -------------------------------------------------------


def test_every_redis_caller_holds_a_connector_rather_than_its_own_client():
    """A seventh private client is how the six disagreements came about.

    `import redis` may appear only in the connector module. Checked on source,
    because the defect is a module choosing to build its own client.
    """

    from pathlib import Path

    app_root = Path(rc.__file__).resolve().parents[2]
    offenders = []
    for path in app_root.rglob("*.py"):
        if path.name == "redis_connector.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "import redis" in text or "redis.from_url" in text or "redis.Redis(" in text:
            offenders.append(path.relative_to(app_root.parent).as_posix())
    assert offenders == []
