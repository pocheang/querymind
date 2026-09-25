"""The middleware's per-IP limiter answers the same with Redis and without it (ARC-01 phase 10).

`RedisRateLimiter` limits login, registration and the admin operations per
client address. It uses Redis when it can and its in-memory store when it
cannot (outside STATE_BACKEND=shared), and until this phase the two were
different algorithms: Redis a sliding log recording every attempt, memory a
fixed window that ignored refused ones. So a client that kept hammering through
a refusal was let back in when the window rolled over in one and kept out in
the other. And the Redis log keyed each attempt on its timestamp alone, so two
attempts in the same instant counted once.

Both paths read `time.time()` through the module, so one fake clock drives
both -- including the sorted-set scores, which the client computes.
"""

from __future__ import annotations

import pytest

from app.services.auth import redis_rate_limit
from app.services.auth.redis_rate_limit import RedisRateLimiter

WINDOW = 10


class _Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def time(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch):
    fake = _Clock()
    monkeypatch.setattr(redis_rate_limit, "time", fake)
    return fake


@pytest.fixture(params=["memory", "redis"])
def limiter(request, async_redis, install) -> RedisRateLimiter:
    if request.param == "memory":
        return RedisRateLimiter(None)
    built = RedisRateLimiter("redis://contract-test:6379/0")
    install(built._redis, async_redis)
    return built


async def _attempts(limiter, key: str, count: int, max_requests: int = 3) -> list[bool]:
    return [(await limiter.check_rate_limit_async(key, max_requests, WINDOW))[0] for _ in range(count)]


@pytest.mark.asyncio
async def test_the_limit_admits_exactly_max_requests_then_refuses(limiter, clock):
    allowed = []
    for _ in range(4):
        clock.now += 0.1
        allowed.append((await limiter.check_rate_limit_async("ip-a", 3, WINDOW))[0])

    assert allowed == [True, True, True, False]


@pytest.mark.asyncio
async def test_a_refusal_says_when_to_come_back(limiter, clock):
    await _attempts(limiter, "ip-a", 3)
    clock.now += 4

    ok, retry_after = await limiter.check_rate_limit_async("ip-a", 3, WINDOW)

    assert not ok
    assert retry_after == int(WINDOW - 4) + 1


@pytest.mark.asyncio
async def test_attempts_in_the_same_instant_each_count(limiter, clock):
    """Keyed on the timestamp alone, a burst was one member of the Redis set."""

    assert await _attempts(limiter, "ip-a", 4) == [True, True, True, False]


@pytest.mark.asyncio
async def test_addresses_do_not_share_a_bucket(limiter, clock):
    await _attempts(limiter, "ip-a", 3)

    assert await _attempts(limiter, "ip-b", 1) == [True]


@pytest.mark.asyncio
async def test_a_quiet_client_is_admitted_once_the_window_has_passed(limiter, clock):
    await _attempts(limiter, "ip-a", 3)
    clock.now += WINDOW + 0.5

    assert await _attempts(limiter, "ip-a", 1) == [True]


@pytest.mark.asyncio
async def test_hammering_through_a_refusal_keeps_the_client_out(limiter, clock):
    """Refused attempts count: the window rolling over is not a reset for a client that never stopped.

    This is where the two used to disagree. At WINDOW + 0.5 the three admitted
    attempts have left the window but the three refused ones have not.
    """

    await _attempts(limiter, "ip-a", 3)
    clock.now += WINDOW / 2
    assert await _attempts(limiter, "ip-a", 3) == [False, False, False]
    clock.now += WINDOW / 2 + 0.5

    ok, retry_after = await limiter.check_rate_limit_async("ip-a", 3, WINDOW)

    assert not ok
    assert 0 < retry_after <= WINDOW


@pytest.mark.asyncio
async def test_reset_forgets_an_address(limiter, clock):
    await _attempts(limiter, "ip-a", 3)

    await limiter.reset("ip-a")

    assert await _attempts(limiter, "ip-a", 1) == [True]
