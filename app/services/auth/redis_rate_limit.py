"""Redis-backed rate limiting.

Distributed sliding-window rate limiting with an in-memory fallback. The client
is created lazily on first use: connecting eagerly in ``__init__`` meant a
blocking network round trip during application startup, and the caller is ASGI
middleware, so every operation here is async.
"""

import logging
import time
import uuid

from app.services.runtime.redis_connector import AsyncRedisConnector
from app.services.runtime.shared_state import SharedStateUnavailable, is_unavailable_error

logger = logging.getLogger(__name__)

_MEMORY_STORE_MAX_KEYS = 10_000
_MEMORY_STORE_TTL_SECONDS = 3600


class RedisRateLimiter:
    """Sliding-window rate limiter over Redis, falling back to process memory.

    The in-memory fallback is per-process and therefore not a substitute for
    Redis in a multi-instance deployment; it exists so a Redis outage degrades
    the limiter instead of failing requests.
    """

    def __init__(self, redis_url: str | None = None, *, shared: bool = False):
        self._redis_url = redis_url
        # STATE_BACKEND=shared: counting per process would multiply every IP
        # limit by the number of workers, so Redis being gone is a refusal.
        self._shared = shared
        # No URL means this limiter was deliberately built without Redis; with
        # one, a failure is retried after the connector's cooldown. It used to
        # set "connection attempted" once and never clear it, so a single blip
        # moved this limiter to per-process counting until the process restarted.
        self._redis = AsyncRedisConnector("rate_limit_middleware", url=lambda: redis_url or "", decode_responses=False)
        self._memory_store: dict[str, list[float]] = {}

    async def _get_client(self):
        """The shared client, or None to take the in-memory path (never None when shared)."""
        client = await self._redis.client() if self._redis_url else None
        if client is None and self._shared:
            raise SharedStateUnavailable("rate limit store (Redis) is unavailable")
        return client

    async def check_rate_limit_async(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int | None]:
        """Return ``(is_allowed, retry_after_seconds)`` without blocking the loop."""
        client = await self._get_client()
        if client is None:
            return self._check_memory(key, max_requests, window_seconds)
        try:
            current_time = time.time()
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, current_time - window_seconds)
            pipe.zcard(key)
            # A unique member per attempt: keyed on the timestamp alone, two
            # attempts in the same instant -- a burst, or two workers -- were one
            # member and counted once.
            pipe.zadd(key, {f"{current_time}:{uuid.uuid4().hex}": current_time})
            pipe.expire(key, window_seconds + 1)
            results = await pipe.execute()

            if int(results[1]) < max_requests:
                return True, None
            oldest = await client.zrange(key, 0, 0, withscores=True)
            if oldest:
                return False, int(window_seconds - (current_time - oldest[0][1])) + 1
            return False, window_seconds
        except Exception as exc:
            if is_unavailable_error(exc):
                await self._redis.drop(exc)
                if self._shared:
                    raise SharedStateUnavailable("rate limit store (Redis) failed") from exc
            logger.warning("Redis rate limit check failed (%s); falling back to memory", exc)
            return self._check_memory(key, max_requests, window_seconds)

    def _check_memory(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int | None]:
        """In-memory fallback, with the Redis path's semantics. Pure CPU, so safe on the loop.

        The same sliding log as the pipeline above: every attempt is recorded,
        refused ones included, and an attempt is allowed while fewer than
        `max_requests` fall inside the window. It used to be a fixed window that
        ignored refused attempts, so a client that kept hammering through a
        refusal was let back in when the window rolled over here and kept out
        in Redis -- the same deployment answering differently depending on
        whether Redis was reachable (tests/contracts/test_middleware_limiter_contract.py).
        """
        current_time = time.time()
        cutoff = current_time - window_seconds

        if len(self._memory_store) > _MEMORY_STORE_MAX_KEYS:
            horizon = current_time - _MEMORY_STORE_TTL_SECONDS
            self._memory_store = {k: v for k, v in self._memory_store.items() if v and v[-1] > horizon}

        attempts = [stamp for stamp in self._memory_store.get(key, ()) if stamp > cutoff]
        allowed = len(attempts) < max_requests
        attempts.append(current_time)
        self._memory_store[key] = attempts
        if allowed:
            return True, None
        return False, int(window_seconds - (current_time - attempts[0])) + 1

    async def reset(self, key: str) -> None:
        """Clear one key's window."""
        client = await self._get_client()
        if client is not None:
            try:
                await client.delete(key)
                return
            except Exception as exc:
                logger.warning("Redis rate limit reset failed (%s)", exc)
                if is_unavailable_error(exc):
                    await self._redis.drop(exc)
        self._memory_store.pop(key, None)


_rate_limiter: RedisRateLimiter | None = None


def get_rate_limiter(redis_url: str | None = None, *, shared: bool = False) -> RedisRateLimiter:
    """Get or create the process-wide rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter(redis_url, shared=shared)
    return _rate_limiter
