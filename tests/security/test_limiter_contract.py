"""The shared limiter keeps the per-process limiter's contract (ARC-01 phase 2a).

`make_limiter` hands the login, register and upload routes one or the other
depending on STATE_BACKEND, and the routes cannot tell which they hold. So every
behavioural assertion here runs against both: the per-process
`SlidingWindowLimiter` and `RedisSlidingWindowLimiter` over fakeredis, which
executes the real Lua. A property that holds for one and not the other is a
deployment that behaves differently depending on a switch nobody connects to
the difference.

The per-process limiter's internals (`_trim`, `_events`) stay pinned in
`test_sliding_window_limiter.py`. What only the Redis limiter has -- opaque key
names, a 503 when Redis is down, a script error that is not an outage -- is
pinned at the bottom.
"""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest

fakeredis = pytest.importorskip("fakeredis")

from app.core.config import get_settings  # noqa: E402
from app.services.runtime import shared_state  # noqa: E402
from app.services.security.rate_limiter import (  # noqa: E402
    RedisSlidingWindowLimiter,
    SlidingWindowLimiter,
    make_limiter,
)


@pytest.fixture
def redis_client(monkeypatch):
    """A fakeredis client installed as the shared-state connector's live client."""

    client = fakeredis.FakeRedis(server=fakeredis.FakeServer(), decode_responses=True)
    monkeypatch.setattr(shared_state._CONNECTOR, "_client", client)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", 0.0)
    return client


@pytest.fixture(params=["memory", "redis"])
def make(request, redis_client):
    def build(max_attempts: int = 3, window_seconds: int = 60):
        if request.param == "memory":
            return SlidingWindowLimiter(max_attempts, window_seconds)
        return RedisSlidingWindowLimiter(max_attempts, window_seconds, name="contract")

    build.kind = request.param
    return build


def _age(limiter, key: str, seconds: float, redis_client) -> None:
    """Move every recorded attempt for `key` `seconds` into the past."""

    if isinstance(limiter, SlidingWindowLimiter):
        limiter._events[key] = type(limiter._events[key])(
            stamp - timedelta(seconds=seconds) for stamp in limiter._events[key]
        )
        return
    name = limiter._key(key)
    for member, score in redis_client.zrange(name, 0, -1, withscores=True):
        redis_client.zadd(name, {member: score - seconds * 1_000_000})


# ---- the contract, both implementations -------------------------------------


def test_max_attempts_is_a_count_of_allowed_attempts(make):
    limiter = make(3)
    assert [limiter.try_acquire("k") for _ in range(5)] == [True, True, True, False, False]


def test_is_limited_agrees_with_try_acquire(make):
    limiter = make(3)
    for _ in range(2):
        limiter.record("k")
    assert limiter.is_limited("k") is False
    limiter.record("k")
    assert limiter.is_limited("k") is True


def test_a_key_is_its_own_budget(make):
    limiter = make(3)
    for _ in range(3):
        limiter.try_acquire("a")
    assert limiter.try_acquire("a") is False
    assert limiter.try_acquire("b") is True


def test_reset_returns_the_whole_budget(make):
    limiter = make(3)
    for _ in range(3):
        limiter.record("k")
    limiter.reset("k")
    assert limiter.is_limited("k") is False
    assert limiter.get_limit_info("k")["attempts_used"] == 0


def test_record_is_not_a_gate(make):
    limiter = make(3)
    for _ in range(5):
        assert limiter.record("k") is None
    info = limiter.get_limit_info("k")
    assert info["attempts_used"] == 5
    assert info["attempts_remaining"] == 0


def test_a_refused_acquire_does_not_spend_a_slot(make):
    limiter = make(2)
    limiter.try_acquire("k")
    limiter.try_acquire("k")
    for _ in range(3):
        assert limiter.try_acquire("k") is False
    assert limiter.get_limit_info("k")["attempts_used"] == 2


def test_an_empty_key_is_unlimited_and_reports_a_full_budget(make):
    limiter = make(3)
    assert limiter.is_limited("") is False
    assert [limiter.try_acquire("") for _ in range(5)] == [True] * 5
    assert limiter.record("") is None
    assert limiter.reset("") is None
    assert limiter.get_limit_info("") == {
        "attempts_used": 0,
        "attempts_remaining": 3,
        "max_attempts": 3,
        "window_seconds": 60,
        "retry_after": 0,
    }


@pytest.mark.parametrize("configured", [0, -5])
def test_a_non_positive_maximum_becomes_one(make, configured):
    limiter = make(configured)
    assert limiter.max_attempts == 1
    assert [limiter.try_acquire("k") for _ in range(3)] == [True, False, False]


@pytest.mark.parametrize("configured", [0, -5])
def test_a_non_positive_window_becomes_one_second(make, configured):
    assert make(3, configured).window.total_seconds() == 1


def test_an_attempt_older_than_the_window_stops_counting(make, redis_client):
    limiter = make(3, 60)
    for _ in range(3):
        limiter.record("k")
    assert limiter.is_limited("k") is True

    _age(limiter, "k", 61, redis_client)
    assert limiter.is_limited("k") is False


def test_an_attempt_just_inside_the_window_still_counts(make, redis_client):
    limiter = make(3, 60)
    for _ in range(3):
        limiter.record("k")

    _age(limiter, "k", 59, redis_client)
    assert limiter.is_limited("k") is True


def test_retry_after_counts_down_to_the_oldest_attempt_leaving(make, redis_client):
    limiter = make(3, 60)
    limiter.record("k")
    _age(limiter, "k", 50, redis_client)
    limiter.record("k")
    limiter.record("k")

    assert limiter.get_limit_info("k")["retry_after"] == pytest.approx(10, abs=1)


def test_retry_after_is_zero_while_the_budget_holds(make):
    limiter = make(3)
    limiter.record("k")
    assert limiter.get_limit_info("k")["retry_after"] == 0


def test_concurrent_callers_cannot_exceed_the_ceiling(make):
    """The property the shared limiter exists for: N workers, one budget."""

    limiter = make(50)
    granted: list[bool] = []
    lock = threading.Lock()

    def attempt():
        result = limiter.try_acquire("k")
        with lock:
            granted.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert granted.count(True) == 50


# ---- release: an attempt refused for a reason that was not the caller's --------
#
# The upload route answers 503 INDEX_BUSY -- "nothing was changed, retry
# shortly" -- after it has taken an attempt from the hourly budget, and before
# `release` existed every retry the response asked for cost the caller an upload
# (ARC-01 phase 10, scenario 5).


def test_release_gives_one_attempt_back(make):
    limiter = make(3)
    assert [limiter.try_acquire("k") for _ in range(3)] == [True, True, True]

    limiter.release("k")

    assert limiter.get_limit_info("k")["attempts_used"] == 2
    assert [limiter.try_acquire("k") for _ in range(2)] == [True, False]


def test_release_never_goes_below_nothing(make):
    limiter = make(2)

    limiter.release("k")
    limiter.release("k")

    assert limiter.get_limit_info("k")["attempts_used"] == 0
    assert [limiter.try_acquire("k") for _ in range(3)] == [True, True, False]


def test_a_release_after_the_window_has_passed_changes_nothing(make, redis_client):
    """No credit carried forward: a window that already emptied cannot be released into."""

    limiter = make(2, window_seconds=60)
    limiter.try_acquire("k")
    limiter.try_acquire("k")
    _age(limiter, "k", 61, redis_client)

    limiter.release("k")

    assert limiter.get_limit_info("k")["attempts_used"] == 0
    assert [limiter.try_acquire("k") for _ in range(3)] == [True, True, False]


def test_release_is_per_key(make):
    limiter = make(1)
    limiter.try_acquire("a")
    limiter.try_acquire("b")

    limiter.release("a")

    assert limiter.try_acquire("a") is True
    assert limiter.try_acquire("b") is False


# ---- only the shared limiter ------------------------------------------------


def test_asking_leaves_nothing_behind_in_redis(redis_client):
    """The login route asks with a username the caller typed, before auth runs."""

    limiter = RedisSlidingWindowLimiter(5, 60, name="login")
    for index in range(200):
        assert limiter.is_limited(f"login::1.2.3.4::user{index}") is False
        limiter.get_limit_info(f"login::1.2.3.4::other{index}")

    assert redis_client.dbsize() == 0


def test_key_names_carry_neither_usernames_nor_addresses(redis_client):
    limiter = RedisSlidingWindowLimiter(5, 60, name="login")
    limiter.record("login::203.0.113.7::alice")

    (name,) = redis_client.keys("*")
    assert name.startswith(get_settings().state_key_prefix + "rl:login:")
    assert "alice" not in name
    assert "203.0.113.7" not in name


def test_two_limiters_on_one_key_are_separate_budgets(redis_client):
    login = RedisSlidingWindowLimiter(1, 60, name="login")
    register = RedisSlidingWindowLimiter(1, 60, name="register")

    assert login.try_acquire("k") is True
    assert register.try_acquire("k") is True


def test_keys_expire_after_the_window(redis_client):
    """Without a TTL every key ever limited would stay in Redis for good."""

    limiter = RedisSlidingWindowLimiter(5, 60, name="login")
    limiter.record("k")

    ttl_ms = redis_client.pttl(limiter._key("k"))
    assert 60_000 < ttl_ms <= 61_000


@pytest.mark.parametrize("call", ["is_limited", "get_limit_info", "record", "try_acquire", "reset", "release"])
def test_an_unavailable_redis_is_a_refusal_not_a_per_process_count(monkeypatch, call):
    """Falling back to process memory here is the defect ARC-01 exists to remove."""

    monkeypatch.setattr(shared_state._CONNECTOR, "_client", None)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", float("inf"))
    limiter = RedisSlidingWindowLimiter(5, 60, name="login")

    with pytest.raises(shared_state.SharedStateUnavailable):
        getattr(limiter, call)("k")


def test_an_empty_key_never_touches_redis(monkeypatch):
    monkeypatch.setattr(shared_state._CONNECTOR, "_client", None)
    monkeypatch.setattr(shared_state._CONNECTOR, "_unavailable_until", float("inf"))
    limiter = RedisSlidingWindowLimiter(5, 60, name="login")

    assert limiter.try_acquire("") is True
    assert limiter.is_limited("") is False
    assert limiter.release("") is None


def test_a_command_that_fails_mid_flight_drops_the_client(redis_client, monkeypatch):
    redis_exceptions = pytest.importorskip("redis.exceptions")

    def boom(*_args, **_kwargs):
        raise redis_exceptions.ConnectionError("connection reset")

    monkeypatch.setattr(redis_client, "eval", boom)
    limiter = RedisSlidingWindowLimiter(5, 60, name="login")

    with pytest.raises(shared_state.SharedStateUnavailable):
        limiter.try_acquire("k")
    assert shared_state._CONNECTOR._client is None, "the next request would pay the timeout again"


def test_a_script_error_is_a_bug_not_an_outage(redis_client, monkeypatch):
    """Redis answering "your script is wrong" must not become a 503 about the infrastructure."""

    redis_exceptions = pytest.importorskip("redis.exceptions")

    def wrong(*_args, **_kwargs):
        raise redis_exceptions.ResponseError("ERR Error running script")

    monkeypatch.setattr(redis_client, "eval", wrong)
    limiter = RedisSlidingWindowLimiter(5, 60, name="login")

    with pytest.raises(redis_exceptions.ResponseError):
        limiter.try_acquire("k")
    assert shared_state._CONNECTOR._client is redis_client


# ---- which one a route gets -------------------------------------------------


@pytest.fixture
def backend(monkeypatch, tmp_path):
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty))

    def choose(value: str) -> None:
        monkeypatch.setenv("STATE_BACKEND", value)
        get_settings.cache_clear()

    yield choose
    get_settings.cache_clear()


def test_memory_hands_out_the_per_process_limiter(backend):
    backend("memory")
    assert type(make_limiter("login", max_attempts=3, window_seconds=60)) is SlidingWindowLimiter


def test_shared_hands_out_the_redis_limiter(backend):
    backend("shared")
    limiter = make_limiter("login", max_attempts=3, window_seconds=60)
    assert type(limiter) is RedisSlidingWindowLimiter
    assert limiter.max_attempts == 3


# ---- what the caller sees when Redis is down ----------------------------------


def test_the_application_answers_503_with_retry_after():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.application.factory import shared_state_unavailable
    from app.api.main import app as real_app

    assert real_app.exception_handlers.get(shared_state.SharedStateUnavailable) is shared_state_unavailable

    probe = FastAPI()
    probe.add_exception_handler(shared_state.SharedStateUnavailable, shared_state_unavailable)

    @probe.get("/login")
    def login():
        raise shared_state.SharedStateUnavailable("down")

    response = TestClient(probe).get("/login")
    assert response.status_code == 503
    assert response.json()["error_code"] == "SHARED_STATE_UNAVAILABLE"
    assert response.headers["Retry-After"] == "15"
