"""The query guard must degrade when Redis fails, not 500.

Three concurrent chat queries against a Redis that timed out returned 500 each
on 2026-09-07. The guard has a memory backend for exactly this, and five
handlers documented as "Redis is not answering, degrade" -- every one of them
read ``except (ValueError, TypeError, OSError)``.

None could fire. ``redis.exceptions.TimeoutError`` and ``...ConnectionError``
derive from ``RedisError(Exception)``; neither is an ``OSError``. The trap is
that redis-py's ``ConnectionError`` SHADOWS the builtin, and the builtin *is*
an ``OSError`` -- so checking "does ``except OSError`` cover a connection
error?" answers yes for the wrong class.

These tests are written against the exception TYPES rather than against a live
Redis, because the defect was never about Redis's behaviour: it was about which
exceptions the handler names.
"""

from __future__ import annotations

import pytest

from app.services.query import guard as guard_module
from app.services.query.guard import QueryLoadGuard, _redis_unavailable_errors


def _install(monkeypatch: pytest.MonkeyPatch, client: object) -> None:
    """Put the fake in as the module's real client.

    Patching `_get_redis_client` wholesale would hide the thing under test:
    the fix drops the module-global client, and a stubbed getter would keep
    handing it back regardless.
    """

    monkeypatch.setattr(guard_module, "_REDIS_CLIENT", client, raising=False)
    monkeypatch.setattr(guard_module, "_REDIS_UNAVAILABLE_UNTIL", 0.0, raising=False)


def _guard(**overrides) -> QueryLoadGuard:
    """A guard whose limits are irrelevant to what is being tested."""

    settings = dict(
        per_user_max_requests=100,
        per_user_window_seconds=60,
        max_concurrent=8,
        max_waiting=8,
        acquire_timeout_ms=500,
        backend="redis",
    )
    settings.update(overrides)
    return QueryLoadGuard(**settings)


redis_exceptions = pytest.importorskip("redis.exceptions")


class _TimingOutClient:
    """A client that fails the way a real one does when Redis is unreachable."""

    def __init__(self, error: BaseException) -> None:
        self._error = error
        self.calls = 0

    def _boom(self, *_args, **_kwargs):
        self.calls += 1
        raise self._error

    incr = _boom
    decr = _boom
    expire = _boom
    get = _boom


REDIS_FAILURES = [
    redis_exceptions.TimeoutError("Timeout connecting to server"),
    redis_exceptions.ConnectionError("Connection refused"),
    redis_exceptions.BusyLoadingError("Redis is loading the dataset in memory"),
]


@pytest.mark.parametrize("error", REDIS_FAILURES, ids=lambda e: type(e).__name__)
def test_the_fallback_tuple_names_what_redis_actually_raises(error: BaseException) -> None:
    """The assertion that would have failed before the fix."""

    assert isinstance(error, _redis_unavailable_errors())


@pytest.mark.parametrize("error", REDIS_FAILURES, ids=lambda e: type(e).__name__)
def test_a_failing_redis_does_not_reach_the_caller(monkeypatch: pytest.MonkeyPatch, error: BaseException) -> None:
    """The request is served instead of turning into a 500."""

    client = _TimingOutClient(error)
    _install(monkeypatch, client)

    with _guard().acquire("user-1") as stats:
        assert stats["max_concurrent"] == 8

    assert client.calls > 0, "the redis path was never entered, so this proves nothing"


@pytest.mark.parametrize("error", REDIS_FAILURES, ids=lambda e: type(e).__name__)
def test_a_failing_command_drops_the_client(monkeypatch: pytest.MonkeyPatch, error: BaseException) -> None:
    """One failure is enough; the next request must not pay the timeout again.

    Without this the client survives its own unusability -- `_effective_backend`
    only asks whether a client exists -- so every later request repeats the
    socket timeout, and `/health` goes on reporting `backend: redis` through an
    outage the guard is silently absorbing.
    """

    client = _TimingOutClient(error)
    _install(monkeypatch, client)

    with _guard().acquire("user-1"):
        pass

    calls_after_first = client.calls
    assert guard_module._REDIS_CLIENT is None, "a failing command left the client in place"

    # The second request takes the memory path and does not touch redis again.
    with _guard().acquire("user-1") as stats:
        assert stats["backend"] == "memory"
    assert client.calls == calls_after_first


def test_a_rate_limit_is_still_a_refusal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Degrading must not swallow the answers that are decisions.

    "Redis is unreachable" and "you are over your limit" arrive at the same
    handler; widening the first must not start absorbing the second, which is
    a refusal the caller has to see.
    """

    from app.services.query.guard import QueryRateLimitedError

    class _OverLimit:
        def incr(self, *_a, **_k):
            return 10_000

        def expire(self, *_a, **_k):
            return True

        def get(self, *_a, **_k):
            return 0

        def decr(self, *_a, **_k):
            return 0

    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: _OverLimit())
    guard = _guard(per_user_max_requests=1)
    with pytest.raises(QueryRateLimitedError):
        with guard.acquire("user-2"):
            pass


def test_no_handler_still_names_the_builtin_set_alone() -> None:
    """The five sites are fixed together or the fix is half-applied.

    Four of five would have looked like a complete change; the first sweep of
    this file found three by reading and missed two, which is why this counts
    rather than trusting the edit.
    """

    from pathlib import Path

    source = Path(guard_module.__file__).read_text(encoding="utf-8")
    assert "except (ValueError, TypeError, OSError) as e:" not in source
    assert source.count("except _redis_unavailable_errors() as e:") == 5
