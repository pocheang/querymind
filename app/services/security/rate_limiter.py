from __future__ import annotations

import threading
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SlidingWindowLimiter:
    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max(1, int(max_attempts))
        self.window = timedelta(seconds=max(1, int(window_seconds)))
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_limited(self, key: str) -> bool:
        if not key:
            return False
        now = _utcnow()
        with self._lock:
            # `.get`, not `self._events[key]`: this is a question, and on a
            # defaultdict asking it inserts. The login route asks it with a
            # key carrying the username the caller typed, before the auth
            # service is touched at all, so an unauthenticated caller varying
            # that name grew this dict by one entry per name, permanently --
            # nothing sweeps it and `reset` only runs on a successful login.
            queue = self._events.get(key)
            if queue is None:
                return False
            self._trim(queue, now)
            if not queue:
                # Nothing left in the window: the key carries no information,
                # so do not keep paying for it.
                del self._events[key]
                return False
            return len(queue) >= self.max_attempts

    def get_limit_info(self, key: str) -> dict[str, int]:
        """
        获取限流详细信息

        Returns:
            dict with keys:
            - attempts_used: 当前窗口内的尝试次数
            - attempts_remaining: 剩余可用次数
            - max_attempts: 最大允许次数
            - window_seconds: 时间窗口（秒）
            - retry_after: 如果被限流，多久后可重试（秒）
        """
        if not key:
            return {
                "attempts_used": 0,
                "attempts_remaining": self.max_attempts,
                "max_attempts": self.max_attempts,
                "window_seconds": int(self.window.total_seconds()),
                "retry_after": 0,
            }

        now = _utcnow()
        with self._lock:
            # Read-only, so it must not allocate either -- see `is_limited`.
            queue = self._events.get(key)
            if queue is not None:
                self._trim(queue, now)
                if not queue:
                    del self._events[key]
                    queue = None
            used = len(queue) if queue else 0
            remaining = max(0, self.max_attempts - used)

            # 计算retry_after：如果被限流，需要等待最老的事件过期
            retry_after = 0
            if queue and used >= self.max_attempts:
                oldest = queue[0]
                expires_at = oldest + self.window
                retry_after = max(0, int((expires_at - now).total_seconds()))

            return {
                "attempts_used": used,
                "attempts_remaining": remaining,
                "max_attempts": self.max_attempts,
                "window_seconds": int(self.window.total_seconds()),
                "retry_after": retry_after,
            }

    def record(self, key: str) -> None:
        if not key:
            return
        now = _utcnow()
        with self._lock:
            queue = self._events[key]
            self._trim(queue, now)
            queue.append(now)

    def try_acquire(self, key: str) -> bool:
        """Atomically check and record an attempt. Returns True if allowed, False if rate limited."""
        if not key:
            return True
        now = _utcnow()
        with self._lock:
            queue = self._events[key]
            self._trim(queue, now)
            if len(queue) >= self.max_attempts:
                return False
            queue.append(now)
            return True

    def reset(self, key: str) -> None:
        if not key:
            return
        with self._lock:
            self._events.pop(key, None)

    def _trim(self, queue: deque[datetime], now: datetime) -> None:
        cutoff = now - self.window
        while queue and queue[0] < cutoff:
            queue.popleft()


# One sorted set per key: member = one attempt, score = when (microseconds, from
# Redis's own clock so workers whose clocks disagree still share one window).
# Trimming is `score < cutoff`, i.e. an attempt exactly `window` old still
# counts -- the same inclusive edge as `SlidingWindowLimiter._trim`.
_TRIM = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000000 + tonumber(t[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', '(' .. (now - tonumber(ARGV[1])))
"""

# Read-only in effect: trimming an absent key creates nothing, so asking about a
# thousand usernames leaves nothing behind -- the property `is_limited` has.
_INSPECT = (
    _TRIM
    + """
local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
return {redis.call('ZCARD', KEYS[1]), oldest[2] or -1, now}
"""
)

# Appends past the ceiling, like `record` does in memory: it is not a gate.
_RECORD = (
    _TRIM
    + """
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('PEXPIRE', KEYS[1], math.floor(tonumber(ARGV[1]) / 1000) + 1000)
return 1
"""
)

# Check and record as one step, so concurrent workers cannot both take the last slot.
_ACQUIRE = (
    _TRIM
    + """
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[3]) then return 0 end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('PEXPIRE', KEYS[1], math.floor(tonumber(ARGV[1]) / 1000) + 1000)
return 1
"""
)


class RedisSlidingWindowLimiter:
    """`SlidingWindowLimiter`'s contract, counted in Redis so every worker shares it (ARC-01).

    Same public surface and the same edge cases -- an empty key is unlimited, a
    non-positive maximum becomes one, asking allocates nothing, `record` is not
    a gate -- so a caller cannot tell which one it holds. What it cannot share is
    the memory limiter's answer to Redis being down: this raises
    `SharedStateUnavailable` (a 503) instead of counting per process.
    """

    def __init__(self, max_attempts: int, window_seconds: int, *, name: str):
        self.max_attempts = max(1, int(max_attempts))
        self.window = timedelta(seconds=max(1, int(window_seconds)))
        self._name = name
        self._window_us = int(self.window.total_seconds() * 1_000_000)

    def _key(self, key: str) -> str:
        from app.services.runtime.shared_state import opaque, state_key

        return state_key("rl", self._name, opaque(key))

    def _eval(self, script: str, key: str, *args):
        from app.services.runtime.shared_state import is_unavailable_error, report_failure, shared_client

        client = shared_client()
        try:
            return client.eval(script, 1, self._key(key), self._window_us, *args)
        except Exception as exc:
            if is_unavailable_error(exc):
                raise report_failure(exc) from exc
            raise

    def is_limited(self, key: str) -> bool:
        if not key:
            return False
        count, _oldest, _now = self._eval(_INSPECT, key)
        return int(count) >= self.max_attempts

    def get_limit_info(self, key: str) -> dict[str, int]:
        info = {
            "attempts_used": 0,
            "attempts_remaining": self.max_attempts,
            "max_attempts": self.max_attempts,
            "window_seconds": int(self.window.total_seconds()),
            "retry_after": 0,
        }
        if not key:
            return info
        count, oldest, now = (int(float(value)) for value in self._eval(_INSPECT, key))
        info["attempts_used"] = count
        info["attempts_remaining"] = max(0, self.max_attempts - count)
        if count >= self.max_attempts and oldest >= 0:
            info["retry_after"] = max(0, (oldest + self._window_us - now) // 1_000_000)
        return info

    def record(self, key: str) -> None:
        if not key:
            return
        self._eval(_RECORD, key, uuid.uuid4().hex)

    def try_acquire(self, key: str) -> bool:
        if not key:
            return True
        return int(self._eval(_ACQUIRE, key, uuid.uuid4().hex, self.max_attempts)) == 1

    def reset(self, key: str) -> None:
        if not key:
            return
        from app.services.runtime.shared_state import is_unavailable_error, report_failure, shared_client

        client = shared_client()
        try:
            client.delete(self._key(key))
        except Exception as exc:
            if is_unavailable_error(exc):
                raise report_failure(exc) from exc
            raise


def make_limiter(name: str, *, max_attempts: int, window_seconds: int):
    """The limiter STATE_BACKEND asks for: per process (`memory`) or shared (`shared`).

    `name` separates limiters in Redis, so the login and register counters for
    one key are different budgets there as they are in memory.
    """

    from app.services.runtime.shared_state import is_shared

    if is_shared():
        return RedisSlidingWindowLimiter(max_attempts, window_seconds, name=name)
    return SlidingWindowLimiter(max_attempts, window_seconds)
