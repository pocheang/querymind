"""The callers that held their own Redis client now recover the way the connector does.

Pinned per caller, because each had its own way of getting this wrong and a
connector nobody reports failures to would reintroduce it:

- the async rate limiter set "connection attempted" once and never reset it, so
  a single Redis blip moved it to per-process counting until restart;
- OAuth state built a new client per call and never pinged, so every operation
  against a dead Redis paid its own 0.5s timeout;
- the admin readiness check rebuilt the client from host and port and lost the
  password, so it reported a password-protected Redis as down.
"""

from __future__ import annotations

import asyncio
import sys
import types

from app.services.runtime import redis_connector as rc


class _BrokenAsyncClient:
    """Answers ping, then fails every command -- a Redis that went away mid-flight."""

    def __init__(self) -> None:
        self.closed = False

    async def ping(self):
        return True

    def pipeline(self):
        raise ConnectionError("connection reset")

    async def aclose(self):
        self.closed = True


class _HealthyAsyncClient:
    def __init__(self) -> None:
        self.zsets: dict[str, dict[str, float]] = {}

    async def ping(self):
        return True

    def pipeline(self):
        client = self

        class _Pipe:
            def __init__(self):
                self.ops = []

            def zremrangebyscore(self, key, lo, hi):
                self.ops.append(("zrem", key, lo, hi))

            def zcard(self, key):
                self.ops.append(("zcard", key))

            def zadd(self, key, mapping):
                self.ops.append(("zadd", key, mapping))

            def expire(self, key, seconds):
                self.ops.append(("expire", key))

            async def execute(self):
                results = []
                for op in self.ops:
                    if op[0] == "zcard":
                        results.append(len(client.zsets.get(op[1], {})))
                    elif op[0] == "zadd":
                        client.zsets.setdefault(op[1], {}).update(op[2])
                        results.append(1)
                    else:
                        results.append(0)
                return results

        return _Pipe()

    async def zrange(self, key, start, end, withscores=False):
        items = sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1])
        return items[start : end + 1]

    async def aclose(self):
        pass


def _install_async(monkeypatch, clients: list):
    """Each connect hands out the next client in `clients`."""

    handed = []

    def from_url(url, **kwargs):
        client = clients[len(handed)]
        handed.append(client)
        return client

    fake_async = types.SimpleNamespace(from_url=from_url)
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(asyncio=fake_async))
    monkeypatch.setitem(sys.modules, "redis.asyncio", fake_async)
    return handed


def test_the_rate_limiter_goes_back_to_redis_after_the_cooldown(monkeypatch):
    from app.services.auth.redis_rate_limit import RedisRateLimiter

    broken, healthy = _BrokenAsyncClient(), _HealthyAsyncClient()
    handed = _install_async(monkeypatch, [broken, healthy])
    limiter = RedisRateLimiter("redis://unit-test:6379/0")

    # The blip: served from memory rather than failing the request.
    assert asyncio.run(limiter.check_rate_limit_async("k", 5, 60)) == (True, None)
    assert broken.closed

    # Inside the cooldown it stays on memory without reconnecting...
    assert asyncio.run(limiter.check_rate_limit_async("k", 5, 60)) == (True, None)
    assert len(handed) == 1

    # ...and after it, Redis is used again. This is the step that never happened.
    monkeypatch.setattr(rc.time, "monotonic", lambda: limiter._redis._unavailable_until + 1)
    assert asyncio.run(limiter.check_rate_limit_async("k", 5, 60)) == (True, None)
    assert handed == [broken, healthy]
    assert healthy.zsets, "the request after the cooldown was not counted in Redis"


def test_the_rate_limiter_without_a_url_never_tries_redis(monkeypatch):
    from app.services.auth.redis_rate_limit import RedisRateLimiter

    handed = _install_async(monkeypatch, [])
    limiter = RedisRateLimiter(None)

    assert asyncio.run(limiter.check_rate_limit_async("k", 1, 60)) == (True, None)
    assert asyncio.run(limiter.check_rate_limit_async("k", 1, 60))[0] is False
    assert handed == []


def test_oauth_state_against_a_dead_redis_connects_once_and_still_works(monkeypatch):
    from app.services.auth.oauth_state import OAuthStateStore

    attempts = []

    def from_url(url, **kwargs):
        attempts.append(url)
        raise ConnectionError("connection refused")

    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(from_url=from_url))
    store = OAuthStateStore("redis://unit-test:6379/0")

    state = store.create({"ip": "203.0.113.7"})
    assert store.consume(state, "203.0.113.7") == (None, "203.0.113.7")
    assert store.consume(state, "203.0.113.7")[0] == "invalid_state", "state must be single-use"
    assert len(attempts) == 1, f"every operation reconnected: {len(attempts)} attempts"


def test_the_readiness_check_probes_the_whole_url(monkeypatch):
    import app.api.routes.operations.health as health

    seen = []
    monkeypatch.setattr(health, "probe", lambda url, **_: seen.append(url))

    class _Settings:
        retrieval_cache_backend = "redis"
        state_backend = "memory"
        redis_url = "redis://:s3cret@cache:6380/2"

    class _Runtime:
        settings = _Settings()

    monkeypatch.setattr(health.api_dependencies, "get_query_runtime", lambda: _Runtime())

    result = health._check_redis_ready()

    assert seen == ["redis://:s3cret@cache:6380/2"]
    assert result["ok"] is True
    assert result["required"] is True
    assert result["host"] == "cache:6380"
    assert "s3cret" not in str(result)


def test_shared_state_makes_redis_required_even_with_a_memory_cache(monkeypatch):
    import app.api.routes.operations.health as health

    monkeypatch.setattr(health, "probe", lambda url, **_: "ConnectionError: refused")

    class _Settings:
        retrieval_cache_backend = "memory"
        state_backend = "shared"
        redis_url = "redis://cache:6379/0"

    class _Runtime:
        settings = _Settings()

    monkeypatch.setattr(health.api_dependencies, "get_query_runtime", lambda: _Runtime())

    result = health._check_redis_ready()
    assert result["required"] is True
    assert result["ok"] is False


# ---- ARC-01 phase 2f: shared state refuses instead of falling back -----------


def test_oauth_state_with_shared_state_refuses_rather_than_remembering_locally(monkeypatch):
    """A state held in one worker's memory is a login callback that fails on the next worker."""

    import pytest

    from app.services.auth.oauth_state import OAuthStateStore
    from app.services.runtime.shared_state import SharedStateUnavailable

    def from_url(url, **kwargs):
        raise ConnectionError("connection refused")

    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(from_url=from_url))
    store = OAuthStateStore("redis://unit-test:6379/0", shared=True)

    with pytest.raises(SharedStateUnavailable):
        store.create({"ip": "203.0.113.7"})
    with pytest.raises(SharedStateUnavailable):
        store.consume("some-state", "203.0.113.7")
    assert store._memory == {}, "nothing may be kept in process memory"


def test_oauth_state_keeps_its_client_when_a_payload_does_not_parse(monkeypatch):
    """A corrupt value is not an outage; dropping the client for it sent logins to the fallback."""

    from app.services.auth.oauth_state import OAuthStateStore

    class _Client:
        def ping(self):
            return True

        def get(self, key):
            return "{not json"

    client = _Client()
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(from_url=lambda url, **kw: client))
    store = OAuthStateStore("redis://unit-test:6379/0")

    assert store.get("state") is None
    assert store._redis._client is client


def test_the_rate_limiter_with_shared_state_refuses_rather_than_counting_per_process(monkeypatch):
    import pytest

    from app.services.auth.redis_rate_limit import RedisRateLimiter
    from app.services.runtime.shared_state import SharedStateUnavailable

    _install_async(monkeypatch, [_BrokenAsyncClient()])
    limiter = RedisRateLimiter("redis://unit-test:6379/0", shared=True)

    first, second = limiter.check_rate_limit_async("k", 5, 60), limiter.check_rate_limit_async("k", 5, 60)
    with pytest.raises(SharedStateUnavailable):
        asyncio.run(first)
    with pytest.raises(SharedStateUnavailable):  # and inside the cooldown, without reconnecting
        asyncio.run(second)
    assert limiter._memory_store == {}


def test_the_rate_limit_middleware_answers_503_not_500(monkeypatch):
    """It sits outside the layer that runs exception handlers, so it has to answer itself."""

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.services.auth.redis_rate_limit as limiter_module
    from app.api.middleware.rate_limit import RateLimitMiddleware

    monkeypatch.setattr(limiter_module, "_rate_limiter", None)
    _install_async(monkeypatch, [_BrokenAsyncClient()])

    probe = FastAPI()
    probe.add_middleware(RateLimitMiddleware, redis_url="redis://unit-test:6379/0", shared=True)

    @probe.post("/auth/login")
    def login():
        return {"ok": True}

    response = TestClient(probe).post("/auth/login")

    assert response.status_code == 503
    assert response.json()["error_code"] == "SHARED_STATE_UNAVAILABLE"
    assert response.headers["Retry-After"] == str(int(rc.COOLDOWN_SECONDS))


def test_the_l2_cache_keeps_its_client_when_a_value_does_not_parse(monkeypatch):
    from app.services.caching.cache_manager import RedisCache

    class _Client:
        async def ping(self):
            return True

        async def get(self, key):
            return "{not json"

        async def aclose(self):
            pass

    client = _Client()
    fake_async = types.SimpleNamespace(from_url=lambda url, **kw: client)
    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(asyncio=fake_async))
    monkeypatch.setitem(sys.modules, "redis.asyncio", fake_async)
    cache = RedisCache("redis://unit-test:6379/0")

    assert asyncio.run(cache.get("k")) is None
    assert cache._redis._client is client
