"""What the distributed query guard does, now that its slots are leases (ARC-01 phase 2b).

The guard used to count slots with INCR on take and DECR on give-back, and this
file pinned that, including a release path that "repaired" counters it could not
decrement. Counters leak: a worker that dies holding a slot never gives it back.
Slots are now members of a sorted set scored by lease expiry, so an abandoned
slot expires on its own and there is nothing to repair -- the two repair tests
became `test_a_slot_abandoned_by_a_dead_worker_is_taken_back`.

Everything else this file pinned still holds and is still pinned, now against
fakeredis running the real Lua: slots come back on exit and on error, a user over
the window is refused before a slot is taken, a full gate and a full queue refuse
without disturbing what others hold, and -- without STATE_BACKEND=shared -- Redis
going away mid-acquire degrades to the in-memory guard instead of failing.

With STATE_BACKEND=shared that last property is deliberately inverted: the
in-memory guard admits `max_concurrent` per worker, which is the ARC-01 defect,
so the answer is a 503.
"""

from __future__ import annotations

import time

import pytest

fakeredis = pytest.importorskip("fakeredis")
redis_exceptions = pytest.importorskip("redis.exceptions")

from app.services.query import guard as guard_module  # noqa: E402
from app.services.query.guard import QueryLoadGuard, QueryOverloadedError, QueryRateLimitedError  # noqa: E402
from app.services.runtime.shared_state import SharedStateUnavailable, state_key  # noqa: E402

INFLIGHT = state_key("qguard", "inflight")
WAITING = state_key("qguard", "waiting")


class _Failing:
    """A fakeredis client whose `eval` / `zrem` fail for keys containing a marker."""

    def __init__(self, client, *, fail_eval_on: str = "", fail_zrem: bool = False) -> None:
        self._client = client
        self._fail_eval_on = fail_eval_on
        self._fail_zrem = fail_zrem
        self.evals: list[tuple[str, str]] = []

    def eval(self, script, numkeys, key, *args):
        self.evals.append((key, script))
        if self._fail_eval_on and self._fail_eval_on in key:
            raise redis_exceptions.ConnectionError("connection reset by peer")
        return self._client.eval(script, numkeys, key, *args)

    def zrem(self, key, member):
        if self._fail_zrem:
            raise redis_exceptions.TimeoutError("timed out")
        return self._client.zrem(key, member)


@pytest.fixture
def redis(monkeypatch):
    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: client)
    return client


def _guard(**overrides) -> QueryLoadGuard:
    kwargs = {
        "per_user_max_requests": 10,
        "per_user_window_seconds": 60,
        "max_concurrent": 2,
        "max_waiting": 2,
        "acquire_timeout_ms": 50,
        "backend": "redis",
    }
    kwargs.update(overrides)
    return QueryLoadGuard(**kwargs)


def _use(guard: QueryLoadGuard, user: str = "user-1") -> dict:
    with guard.acquire(user) as stats:
        return dict(stats)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _held_by_other_workers(redis, key: str, count: int, *, expires_in_ms: int = 60_000, tag: str = "other") -> None:
    redis.zadd(key, {f"{tag}-{index}": _now_ms() + expires_in_ms for index in range(count)})


# ---- what was pinned before, still true ------------------------------------


def test_a_slot_is_taken_and_given_back(redis):
    guard = _guard()
    with guard.acquire("user-1") as stats:
        assert stats["backend"] == "redis"
        assert redis.zcard(INFLIGHT) == 1

    assert redis.zcard(INFLIGHT) == 0
    assert redis.zcard(WAITING) == 0  # never queued, so never counted


def test_the_slot_comes_back_even_when_the_body_raises(redis):
    guard = _guard()

    # The raise inside is the assertion, not a second thing that might throw.
    with pytest.raises(ValueError):  # NOSONAR
        with guard.acquire("user-1"):
            raise ValueError("boom")

    assert redis.zcard(INFLIGHT) == 0


def test_a_user_over_the_window_is_rate_limited_before_a_slot_is_taken(redis):
    guard = _guard(per_user_max_requests=2)

    _use(guard)
    _use(guard)
    with pytest.raises(QueryRateLimitedError):  # admitted, `_use` returns and this fails
        _use(guard)

    assert redis.zcard(INFLIGHT) == 0


def test_the_user_window_is_shared_and_the_key_carries_no_user_id(redis):
    """Two guards are two workers; the window is one."""

    _use(_guard(per_user_max_requests=2), "alice@example.com")
    _use(_guard(per_user_max_requests=2), "alice@example.com")
    third_worker = _guard(per_user_max_requests=2)
    with pytest.raises(QueryRateLimitedError):
        _use(third_worker, "alice@example.com")

    assert not [key for key in redis.keys("*") if "alice" in key]


def test_a_full_gate_with_no_queue_is_refused_without_touching_other_slots(redis):
    _held_by_other_workers(redis, INFLIGHT, 2)
    guard = _guard(max_concurrent=2, max_waiting=0)

    with pytest.raises(QueryOverloadedError, match="queue full"):
        _use(guard)

    assert sorted(redis.zrange(INFLIGHT, 0, -1)) == ["other-0", "other-1"]


def test_a_full_queue_is_refused_and_leaves_the_queue_as_it_found_it(redis):
    _held_by_other_workers(redis, INFLIGHT, 2)
    _held_by_other_workers(redis, WAITING, 2)
    guard = _guard(max_concurrent=2, max_waiting=2)

    with pytest.raises(QueryOverloadedError, match="queue full"):
        _use(guard)

    assert redis.zcard(WAITING) == 2


def test_waiting_past_the_deadline_is_refused_and_its_place_in_the_queue_comes_back(redis):
    _held_by_other_workers(redis, INFLIGHT, 2)
    guard = _guard(max_concurrent=2, max_waiting=2, acquire_timeout_ms=1)

    with pytest.raises(QueryOverloadedError, match="queue timeout"):
        _use(guard)

    assert redis.zcard(WAITING) == 0
    assert redis.zcard(INFLIGHT) == 2


def test_redis_failing_the_rate_check_degrades_to_the_in_memory_guard(redis, monkeypatch):
    """Without shared state, a dead Redis costs the distributed gate, never the request."""

    failing = _Failing(redis, fail_eval_on=":rl:")
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: failing)

    _use(_guard())

    assert (INFLIGHT, guard_module._TAKE) not in failing.evals  # never tried to take a slot
    assert redis.zcard(INFLIGHT) == 0


def test_redis_failing_the_gate_degrades_to_the_in_memory_guard(redis, monkeypatch):
    failing = _Failing(redis, fail_eval_on=INFLIGHT)
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: failing)

    _use(_guard())  # yields rather than raising

    assert redis.zcard(INFLIGHT) == 0


def test_no_client_at_all_uses_the_in_memory_guard(monkeypatch):
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: None)

    stats = _use(_guard())

    assert stats["backend"] == "memory"


# ---- what leases add ---------------------------------------------------------


def test_a_slot_abandoned_by_a_dead_worker_is_taken_back(redis):
    """The failure the counters could not recover from without waiting for a key to expire."""

    _held_by_other_workers(redis, INFLIGHT, 2, expires_in_ms=-1)  # both leases ran out
    guard = _guard(max_concurrent=2, max_waiting=0)

    with guard.acquire("user-1"):
        assert redis.zcard(INFLIGHT) == 1, "the expired leases were not discarded"


def test_a_slot_is_leased_for_as_long_as_the_guard_was_told(redis):
    guard = _guard(slot_lease_ms=150_000)

    with guard.acquire("user-1"):
        ((_member, expires_at),) = redis.zrange(INFLIGHT, 0, -1, withscores=True)
        assert 149_000 <= expires_at - _now_ms() <= 150_500


def test_a_request_that_waited_leaves_the_queue_once_it_is_admitted(redis):
    """Otherwise it is counted as waiting for its whole run."""

    _held_by_other_workers(redis, INFLIGHT, 1, expires_in_ms=150)
    guard = _guard(max_concurrent=1, max_waiting=2, acquire_timeout_ms=2_000)

    with guard.acquire("user-1"):
        assert redis.zcard(INFLIGHT) == 1
        assert redis.zcard(WAITING) == 0


def test_a_release_that_fails_does_not_fail_the_request(redis, monkeypatch):
    """The lease expires on its own; the request must not pay for the blip."""

    failing = _Failing(redis, fail_zrem=True)
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: failing)

    _use(_guard())

    assert redis.zcard(INFLIGHT) == 1  # left to expire


def test_stats_count_every_worker_and_skip_expired_leases(redis):
    _held_by_other_workers(redis, INFLIGHT, 2)
    _held_by_other_workers(redis, INFLIGHT, 3, expires_in_ms=-1, tag="dead")
    _held_by_other_workers(redis, WAITING, 1)

    stats = _guard(max_concurrent=10).stats()

    assert (stats["backend"], stats["inflight"], stats["waiting"]) == ("redis", 2, 1)


# ---- STATE_BACKEND=shared ------------------------------------------------------


def test_shared_without_redis_is_a_503_not_a_per_worker_gate(monkeypatch):
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: None)
    guard = _guard(shared=True)

    with pytest.raises(SharedStateUnavailable):
        _use(guard)


def test_shared_with_redis_failing_mid_acquire_is_a_503(redis, monkeypatch):
    failing = _Failing(redis, fail_eval_on=INFLIGHT)
    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: failing)

    guard = _guard(shared=True)
    with pytest.raises(SharedStateUnavailable):
        _use(guard)


def test_shared_overrides_a_memory_preference(redis):
    """QUERY_GUARD_BACKEND=memory beside STATE_BACKEND=shared would split the gate by worker."""

    guard = _guard(backend="memory", shared=True)
    with guard.acquire("user-1") as stats:
        assert stats["backend"] == "redis"
        assert redis.zcard(INFLIGHT) == 1


def test_shared_stats_never_raise(monkeypatch):
    """/metrics and /ready read stats; an outage must show there, not break them."""

    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: None)

    assert _guard(shared=True).stats()["backend"] == "redis_unavailable"


def test_a_script_error_is_a_bug_not_a_fallback(redis, monkeypatch):
    class _WrongScript:
        def eval(self, *_args):
            raise redis_exceptions.ResponseError("ERR Error running script")

        def zrem(self, *_args):
            return 0

    monkeypatch.setattr(guard_module, "_get_redis_client", lambda: _WrongScript())

    guard = _guard()
    with pytest.raises(redis_exceptions.ResponseError):
        _use(guard)
