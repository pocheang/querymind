"""The query guard admits and refuses the same way in memory and over Redis (ARC-01 phase 10).

In memory it is a semaphore and a per-process sliding window; over Redis, a
sorted set of slot leases and a Lua sliding window every worker shares. The
Redis side is pinned in detail in tests/services/test_query_guard_redis.py --
leases, expiry, degradation. What is pinned here is what a request can observe
and must not depend on the backend: how many run at once, how many wait and
for how long, when a user is over their window, and that a slot comes back.
"""

from __future__ import annotations

import threading
import time

import pytest

from app.services.query import guard as guard_module
from app.services.query.guard import QueryLoadGuard, QueryOverloadedError, QueryRateLimitedError


@pytest.fixture(params=["memory", "redis"])
def backend(request, sync_redis, monkeypatch) -> str:
    if request.param == "redis":
        monkeypatch.setattr(guard_module, "_get_redis_client", lambda: sync_redis)
    else:
        monkeypatch.setattr(guard_module, "_get_redis_client", lambda: None)
    return request.param


def _guard(backend: str, **overrides) -> QueryLoadGuard:
    kwargs = {
        "per_user_max_requests": 10,
        "per_user_window_seconds": 60,
        "max_concurrent": 2,
        "max_waiting": 0,
        "acquire_timeout_ms": 600,
        "backend": backend,
        **overrides,
    }
    return QueryLoadGuard(**kwargs)


def _counts(guard: QueryLoadGuard) -> tuple[int, int]:
    stats = guard.stats()
    return int(stats["inflight"]), int(stats["waiting"])


def test_a_slot_is_held_for_the_request_and_given_back(backend):
    guard = _guard(backend)

    with guard.acquire("alice"):
        assert _counts(guard) == (1, 0)

    assert _counts(guard) == (0, 0)


def test_a_request_that_raises_gives_its_slot_back(backend):
    guard = _guard(backend)

    with pytest.raises(RuntimeError), guard.acquire("alice"):
        raise RuntimeError("the answer failed")

    assert _counts(guard) == (0, 0)


def test_no_more_than_max_concurrent_run_at_once(backend):
    guard = _guard(backend, max_concurrent=2)

    with guard.acquire("alice"), guard.acquire("bob"):
        with pytest.raises(QueryOverloadedError, match="queue full"), guard.acquire("carol"):
            pass
        assert _counts(guard) == (2, 0)


def test_a_user_over_their_window_is_refused_and_others_are_not(backend):
    guard = _guard(backend, per_user_max_requests=2)
    for _ in range(2):
        with guard.acquire("alice"):
            pass

    with pytest.raises(QueryRateLimitedError), guard.acquire("alice"):
        pass
    with guard.acquire("bob"):
        pass
    assert _counts(guard) == (0, 0)


def test_a_refused_overload_still_spends_the_users_budget(backend):
    """The window counts attempts, so a user cannot retry an overloaded gate for free."""

    guard = _guard(backend, per_user_max_requests=2, max_concurrent=1)
    with guard.acquire("alice"):
        with pytest.raises(QueryOverloadedError), guard.acquire("alice"):
            pass
    with pytest.raises(QueryRateLimitedError), guard.acquire("alice"):
        pass


def test_a_waiter_times_out_and_leaves_the_queue(backend):
    guard = _guard(backend, max_concurrent=1, max_waiting=1, acquire_timeout_ms=400)
    seen_waiting = []

    def watch():
        time.sleep(0.2)
        seen_waiting.append(_counts(guard)[1])

    with guard.acquire("alice"):
        watcher = threading.Thread(target=watch)
        watcher.start()
        started = time.monotonic()
        with pytest.raises(QueryOverloadedError, match="timeout"), guard.acquire("bob"):
            pass
        waited = time.monotonic() - started
        watcher.join()

    assert seen_waiting == [1]
    assert 0.35 < waited < 2.0
    assert _counts(guard) == (0, 0)


def test_a_full_queue_refuses_at_once(backend):
    guard = _guard(backend, max_concurrent=1, max_waiting=1, acquire_timeout_ms=1500)
    results = []

    def wait_in_line():
        try:
            with guard.acquire("bob"):
                results.append("admitted")
        except QueryOverloadedError as refused:
            results.append(str(refused))

    with guard.acquire("alice"):
        waiter = threading.Thread(target=wait_in_line)
        waiter.start()
        deadline = time.monotonic() + 2
        while _counts(guard)[1] < 1 and time.monotonic() < deadline:
            time.sleep(0.02)
        started = time.monotonic()
        with pytest.raises(QueryOverloadedError, match="queue full"), guard.acquire("carol"):
            pass
        assert time.monotonic() - started < 0.3
    waiter.join()

    assert results == ["admitted"], "the waiter is admitted once the slot comes back"
    assert _counts(guard) == (0, 0)


def test_stats_report_the_same_limits(backend):
    stats = _guard(backend, max_concurrent=3, max_waiting=4).stats()

    assert {key: stats[key] for key in ("max_concurrent", "max_waiting")} == {"max_concurrent": 3, "max_waiting": 4}
    assert stats["backend"] == backend
