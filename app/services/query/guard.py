from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field

from app.services.observability.log_safety import key_ref
from app.services.runtime.redis_connector import RedisConnector, redis_unavailable_errors
from app.services.runtime.shared_state import SharedStateUnavailable, is_unavailable_error, opaque, state_key
from app.services.security.rate_limiter import _ACQUIRE as _RATE_ACQUIRE
from app.services.security.rate_limiter import SlidingWindowLimiter

logger = logging.getLogger(__name__)

# What "Redis is not answering" is raised as -- see `redis_unavailable_errors`
# for why `OSError` alone is the wrong answer that looks right. Kept under this
# name because it is the guard's public vocabulary for the question.
_redis_unavailable_errors = redis_unavailable_errors


class QueryRateLimitedError(RuntimeError):
    pass


class QueryOverloadedError(RuntimeError):
    pass


_QUERY_QUEUE_FULL = "query queue full"

# Short timeouts on purpose: this client sits in front of every query, and a
# Redis that is slow to answer must cost 0.2s once rather than a second each.
_REDIS = RedisConnector(
    "query_guard",
    decode_responses=True,
    socket_connect_timeout=0.2,
    socket_timeout=0.2,
    retry_on_timeout=False,
    max_connections=50,
    health_check_interval=30,
)

# A slot is a lease, not a counter. Each holder is a member of a sorted set
# scored by when its lease runs out, and taking a slot first discards expired
# leases. The counters this replaced (INCR on take, DECR on give-back) leaked:
# a worker that died holding a slot never gave it back, and the cluster ran one
# slot short until the shared key expired -- which it did only when nobody had
# incremented it for a whole window, i.e. never under load.
_TAKE = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[2]), ARGV[3])
redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[2]) + 1000)
return 1
"""

_COUNT = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
return redis.call('ZCARD', KEYS[1])
"""

# How long a queued request may wait past its own deadline before its place is
# presumed abandoned. The waiter removes itself; this only covers a worker that
# died while waiting.
_WAIT_LEASE_SLACK_MS = 5_000


def _redis_command_failed(where: str, error: BaseException) -> None:
    """Treat a failed command exactly as a failed connection.

    Without this the client survives its own unusability: `_effective_backend`
    only asks whether a client exists, so every later request pays the socket
    timeout again and `/health` goes on reporting `backend: redis` through an
    outage the guard is silently absorbing.
    """

    logger.debug("query_guard_redis_%s_failed error=%s", where, str(error))
    _REDIS.drop(error)


def _get_redis_client():
    """The process-wide client, or None while Redis is unavailable or cooling down."""

    return _REDIS.client()


class _RedisUnusable(Exception):
    """Internal: Redis stopped answering partway through; the caller picks the fallback."""


def _call(client, where: str, script: str, key: str, *args):
    """Run one guard script, turning "Redis is not answering" into `_RedisUnusable`.

    The only place a guard command meets Redis, so there is one handler that
    decides what counts as unavailable -- the guard used to have five, and they
    were fixed together or not at all. A script error is Redis *answering*, and
    propagates as the bug it is.
    """

    try:
        return client.eval(script, 1, key, *args)
    except Exception as e:
        if is_unavailable_error(e):
            _redis_command_failed(where, e)
            raise _RedisUnusable(where) from e
        raise


@dataclass
class _RedisSlot:
    """What one acquisition holds in Redis, so the release gives back exactly that."""

    member: str = field(default_factory=lambda: uuid.uuid4().hex)
    acquired: bool = False
    queued: bool = False


def _queue_backoff_seconds(elapsed: float) -> float:
    """Widen the poll interval as a wait lengthens, so a full queue does not spin."""

    if elapsed < 0.5:
        return 0.05
    if elapsed < 2.0:
        return 0.1
    if elapsed < 5.0:
        return 0.2
    return 0.5


class QueryLoadGuard:
    def __init__(
        self,
        *,
        per_user_max_requests: int,
        per_user_window_seconds: int,
        max_concurrent: int,
        max_waiting: int,
        acquire_timeout_ms: int,
        backend: str = "auto",
        shared: bool = False,
        slot_lease_ms: int = 150_000,
    ):
        """`shared` is STATE_BACKEND=shared: Redis is the only guard, and its absence a 503.

        Otherwise Redis is used when it answers and the in-memory guard when it
        does not -- which is the right trade for one worker and the ARC-01
        defect for several, because each worker then admits `max_concurrent`.

        `slot_lease_ms` bounds how long a slot survives a worker that died
        holding it. It must outlast the slowest legitimate query, or a slow
        query's slot expires under it and the gate admits one too many.
        """

        self._user_limiter = SlidingWindowLimiter(
            max_attempts=max(1, int(per_user_max_requests)),
            window_seconds=max(1, int(per_user_window_seconds)),
        )
        self._semaphore = threading.BoundedSemaphore(value=max(1, int(max_concurrent)))
        self._max_waiting = max(0, int(max_waiting))
        self._acquire_timeout_s = max(1, int(acquire_timeout_ms)) / 1000.0
        self._state_lock = threading.Lock()
        self._waiting = 0
        self._inflight = 0
        self._max_concurrent = max(1, int(max_concurrent))
        self._max_per_user = max(1, int(per_user_max_requests))
        self._window_seconds = max(1, int(per_user_window_seconds))
        self._shared = bool(shared)
        self._slot_lease_ms = max(1_000, int(slot_lease_ms))
        self._wait_lease_ms = int(self._acquire_timeout_s * 1000) + _WAIT_LEASE_SLACK_MS
        b = str(backend or "auto").strip().lower()
        if b not in {"auto", "memory", "redis"}:
            b = "auto"
        # Shared state has one home; a per-guard "memory" preference cannot
        # override it without splitting the gate by the number of workers.
        self._backend = "redis" if self._shared else b

    def _effective_backend(self) -> str:
        if self._backend == "memory":
            return "memory"
        if self._shared:
            return "redis"
        return "redis" if _get_redis_client() is not None else "memory"

    def stats(self) -> dict[str, int | str]:
        if self._effective_backend() == "redis":
            return self._redis_stats()
        with self._state_lock:
            return {
                "backend": "memory",
                "inflight": self._inflight,
                "waiting": self._waiting,
                "max_concurrent": self._max_concurrent,
                "max_waiting": self._max_waiting,
            }

    def _redis_stats(self) -> dict[str, int | str]:
        """Counts across every worker. Never raises: /metrics and /ready read this."""

        client = _get_redis_client()
        inflight = waiting = 0
        backend = "redis"
        if client is None:
            backend = "redis_unavailable"
        else:
            try:
                inflight = int(_call(client, "stats", _COUNT, state_key("qguard", "inflight")))
                waiting = int(_call(client, "stats", _COUNT, state_key("qguard", "waiting")))
            except _RedisUnusable:
                backend = "redis_unavailable"
        return {
            "backend": backend,
            "inflight": inflight,
            "waiting": waiting,
            "max_concurrent": self._max_concurrent,
            "max_waiting": self._max_waiting,
        }

    @contextmanager
    def acquire(self, user_key: str) -> Iterator[dict[str, int | str]]:
        if self._effective_backend() == "redis":
            with self._acquire_redis(user_key):
                yield self.stats()
            return
        with self._acquire_memory(user_key):
            yield self.stats()

    @asynccontextmanager
    async def acquire_async(self, user_key: str) -> AsyncIterator[dict[str, int | str]]:
        """Acquire a slot without blocking the event loop.

        ``acquire`` waits on a threading semaphore for up to
        ``acquire_timeout_ms``, and the redis backend does blocking I/O.  Running
        either inline in an async handler freezes every other task on the loop
        precisely when the server is overloaded, so both the blocking enter and
        the blocking exit run in worker threads.
        """
        manager = self.acquire(user_key)
        stats = await asyncio.to_thread(manager.__enter__)
        exc_info: tuple = (None, None, None)
        try:
            yield stats
        except BaseException:
            exc_info = sys.exc_info()
            raise
        finally:
            await asyncio.to_thread(manager.__exit__, *exc_info)

    @contextmanager
    def _acquire_memory(self, user_key: str) -> Iterator[None]:
        if self._user_limiter.is_limited(user_key):
            raise QueryRateLimitedError("query rate limit exceeded")
        self._user_limiter.record(user_key)

        acquired = False
        queued = False
        try:
            acquired = self._semaphore.acquire(blocking=False)
            if not acquired:
                with self._state_lock:
                    if self._waiting >= self._max_waiting:
                        raise QueryOverloadedError(_QUERY_QUEUE_FULL)
                    self._waiting += 1
                    queued = True
                acquired = self._semaphore.acquire(timeout=self._acquire_timeout_s)
            if not acquired:
                raise QueryOverloadedError("query queue timeout")
            with self._state_lock:
                if queued:
                    self._waiting -= 1
                self._inflight += 1
            yield
        finally:
            if acquired:
                with self._state_lock:
                    self._inflight = max(0, self._inflight - 1)
                self._semaphore.release()
            elif queued:
                with self._state_lock:
                    self._waiting = max(0, self._waiting - 1)

    def _redis_unusable(self, user_key: str):
        """Redis cannot be used for this request: a 503 when shared, the memory guard otherwise."""

        if self._shared:
            raise SharedStateUnavailable("query guard: shared state store (Redis) is unavailable")
        return self._acquire_memory(user_key)

    @contextmanager
    def _acquire_redis(self, user_key: str) -> Iterator[None]:
        client = _get_redis_client()
        if client is None:
            with self._redis_unusable(user_key):
                yield
            return

        slot = _RedisSlot()
        try:
            try:
                self._reserve_redis_slot(client, slot, user_key)
            except _RedisUnusable:
                fallback = self._redis_unusable(user_key)
            else:
                fallback = None
            if fallback is None:
                yield
            else:
                with fallback:
                    yield
        finally:
            self._release_redis_slot(client, slot, user_key)

    def _reserve_redis_slot(self, client, slot: _RedisSlot, user_key: str) -> None:
        """Take a slot, or raise: a refusal, an overload, or `_RedisUnusable`."""

        self._check_user_rate(client, user_key)
        started = time.monotonic()
        while not self._take_slot(client, slot, user_key):
            if not slot.queued:
                self._join_queue(client, slot)
            if (time.monotonic() - started) > self._acquire_timeout_s:
                raise QueryOverloadedError("query queue timeout")
            time.sleep(_queue_backoff_seconds(time.monotonic() - started))

    def _check_user_rate(self, client, user_key: str) -> None:
        """The per-user sliding window, shared by every worker; the key carries a digest, not the id."""

        rate_key = state_key("rl", "query", opaque(user_key))
        window_us = self._window_seconds * 1_000_000
        allowed = _call(client, "rate_check", _RATE_ACQUIRE, rate_key, window_us, uuid.uuid4().hex, self._max_per_user)
        if int(allowed) == 0:
            raise QueryRateLimitedError("query rate limit exceeded")

    def _take_slot(self, client, slot: _RedisSlot, user_key: str) -> bool:
        taken = _call(
            client,
            "take",
            _TAKE,
            state_key("qguard", "inflight"),
            self._max_concurrent,
            self._slot_lease_ms,
            slot.member,
        )
        if not int(taken):
            return False
        slot.acquired = True
        if slot.queued:
            # Leave the queue now rather than at release: otherwise a request
            # that waited is counted as waiting for its whole run.
            self._release_redis_slot(client, _RedisSlot(member=slot.member, queued=True), user_key)
            slot.queued = False
        return True

    def _join_queue(self, client, slot: _RedisSlot) -> None:
        """Claim a place in the bounded queue, or raise because there is none."""

        if self._max_waiting <= 0:
            raise QueryOverloadedError(_QUERY_QUEUE_FULL)
        joined = _call(
            client, "queue", _TAKE, state_key("qguard", "waiting"), self._max_waiting, self._wait_lease_ms, slot.member
        )
        if not int(joined):
            raise QueryOverloadedError(_QUERY_QUEUE_FULL)
        slot.queued = True

    def _release_redis_slot(self, client, slot: _RedisSlot, user_key: str) -> None:
        """Give back what this acquisition holds.

        A failure here costs nothing lasting: the lease expires on its own,
        which is exactly what the counters this replaced could not do.
        """

        held = [
            (state_key("qguard", "waiting"), slot.queued),
            (state_key("qguard", "inflight"), slot.acquired),
        ]
        for key, holds in held:
            if not holds:
                continue
            try:
                client.zrem(key, slot.member)
            except Exception as e:
                if not is_unavailable_error(e):
                    raise
                logger.warning(
                    "query_guard_release_failed user=%s key=%s error=%s -- the lease expires on its own",
                    key_ref(user_key),
                    key.rsplit(":", 1)[-1],
                    str(e),
                )
                _redis_command_failed("release", e)
