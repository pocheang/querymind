"""One way to hold a Redis client: opened lazily, dropped on failure, retried after a cooldown.

Six modules used to do this for themselves, and they disagreed in ways that
mattered only when Redis was down -- which is exactly when nobody is reading
code:

- the retrieval cache set no cooldown after a failed connect, so with Redis
  unreachable every query paid its 5 second connect timeout again;
- OAuth state built a new connection pool on every call and never pinged, so an
  unreachable Redis cost each OAuth callback several 0.5 second timeouts;
- the async rate limiter marked the connection as attempted and never reset
  the flag, so a single blip moved it to per-process counting until restart;
- the async cache manager never pinged and never dropped a broken client.

A connector answers "is there a working client?" with a client or with None, and
every caller treats None as "take your fallback". A failed command is reported
with `drop`, which discards the client and starts the cooldown, so an outage
costs one connection attempt per cooldown rather than one per request, and
`status()` stops reporting a client that is not working.

Which fallback a caller takes is still the caller's decision. ARC-01 phase 2
changes that for the security-relevant callers; this module deliberately does
not.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 15.0
"""How long a connector stops trying after a failure.

Every caller used `getattr(settings, "redis_retry_cooldown_seconds", 15)`, and no
such field exists on `Settings`, so the value was always 15. It is a constant
here rather than a new setting: nobody has needed to tune it, and a setting that
only ever held its default is configuration surface without a reason.
"""

_ERRORS: tuple[type[BaseException], ...] | None = None


def redis_unavailable_errors() -> tuple[type[BaseException], ...]:
    """What "Redis is not answering" is actually raised as.

    `redis.exceptions.TimeoutError` and `...ConnectionError` derive from
    `RedisError(Exception)`, NOT from `OSError` -- and redis-py's
    `ConnectionError` shadows the builtin, which is an `OSError`, so reading
    `except OSError` as covering a connection failure is wrong in exactly the way
    that looks right. Resolved once: callers are on the request path, and redis
    is an optional install, so this must neither import per call nor require it.
    """

    global _ERRORS
    if _ERRORS is None:
        base: tuple[type[BaseException], ...] = (ValueError, TypeError, OSError)
        try:
            # The submodule, not `redis.RedisError`: it resolves the same class
            # and does not depend on what the top-level package object exposes.
            from redis.exceptions import RedisError  # type: ignore

            _ERRORS = (*base, RedisError)
        except ImportError:
            _ERRORS = base
    return _ERRORS


def _settings_redis_url() -> str:
    from app.core.config import get_settings

    return str(getattr(get_settings(), "redis_url", "") or "")


def probe(url: str, *, timeout: float = 3.0) -> str | None:
    """Ping `url` once with a throwaway client; None when it answered, else why not.

    Uses the whole URL. The admin readiness check used to rebuild a client from
    host and port alone, dropping the password and the database number, so
    against the production compose file -- whose REDIS_URL carries a password --
    it reported Redis as down however healthy Redis was.
    """

    client = None
    try:
        import redis  # type: ignore

        client = redis.from_url(url, socket_connect_timeout=timeout, socket_timeout=timeout)
        client.ping()
        return None
    except ImportError:
        return "redis package not installed"
    except Exception as exc:  # noqa: BLE001 -- any failure is the answer to "is it reachable?"
        return f"{type(exc).__name__}: {exc}"[:200]
    finally:
        RedisConnector._discard(client)


_REGISTRY: dict[str, _ConnectorBase] = {}
_REGISTRY_LOCK = threading.Lock()


def connector_status() -> list[dict[str, Any]]:
    """Every connector this process has created, and what state each is in.

    For the admin readiness probe. It reports without connecting: a status page
    that opens connections to find out is a status page that can hang.
    """

    with _REGISTRY_LOCK:
        connectors = list(_REGISTRY.values())
    return [connector.status() for connector in sorted(connectors, key=lambda c: c.name)]


class _ConnectorBase:
    """Cooldown bookkeeping shared by the sync and async connectors."""

    def __init__(self, name: str, *, url: Callable[[], str] | None, options: dict[str, Any]) -> None:
        self.name = name
        self._url = url or _settings_redis_url
        self._options = dict(options)
        self._client: Any | None = None
        self._unavailable_until = 0.0
        self._last_error = ""
        with _REGISTRY_LOCK:
            # Keyed by name: a later connector of the same name (a test, or a
            # store rebuilt by a config reload) replaces the earlier one in the
            # report instead of accumulating beside it.
            _REGISTRY[name] = self

    def _cooling_down(self) -> bool:
        return bool(self._unavailable_until and time.monotonic() < self._unavailable_until)

    def _start_cooldown(self, error: BaseException | str) -> None:
        self._unavailable_until = time.monotonic() + COOLDOWN_SECONDS
        self._last_error = str(error)[:200]

    def status(self) -> dict[str, Any]:
        if self._client is not None:
            state = "connected"
        elif self._cooling_down():
            state = "cooling_down"
        elif self._unavailable_until:
            state = "retry_pending"
        else:
            state = "not_connected"
        return {
            "name": self.name,
            "state": state,
            "cooldown_remaining_s": round(max(0.0, self._unavailable_until - time.monotonic()), 1)
            if self._cooling_down()
            else 0.0,
            "last_error": self._last_error,
        }


class RedisConnector(_ConnectorBase):
    """A lazily opened synchronous client, shared by every thread of one process."""

    def __init__(self, name: str, *, url: Callable[[], str] | None = None, **options: Any) -> None:
        super().__init__(name, url=url, options=options)
        self._lock = threading.Lock()

    def client(self):
        """The working client, or None while Redis is unavailable or cooling down.

        Checked before and again inside the lock: the wait for the lock is exactly
        as long as another thread's connection attempt, which is the case worth
        not repeating.
        """

        if self._client is not None:
            return self._client
        if self._cooling_down():
            return None
        with self._lock:
            if self._client is not None:
                return self._client
            if self._cooling_down():
                return None
            return self._connect()

    def _connect(self):
        """Open and ping a client, or start a cooldown. Call under the lock."""

        client = None
        try:
            import redis  # type: ignore

            client = redis.from_url(self._url(), **self._options)
            client.ping()
        except ImportError as exc:
            # Not installed: routine, and not worth a warning.
            logger.debug("redis_connector_unavailable name=%s error=%s", self.name, exc)
            self._discard(client)
            self._start_cooldown(exc)
            return None
        except Exception as exc:
            # `from_url` can succeed and `ping` still fail, so there may be a
            # client to close even though the connection never worked.
            logger.warning("redis_connector_connect_failed name=%s error=%s", self.name, exc)
            self._discard(client)
            self._start_cooldown(exc)
            return None
        self._client = client
        self._unavailable_until = 0.0
        self._last_error = ""
        return client

    def drop(self, error: BaseException | str = "") -> None:
        """A command failed: discard the client and stop trying until the cooldown ends.

        Without this a client survives its own unusability -- `client()` only asks
        whether one exists -- so every later request pays the socket timeout again.
        """

        logger.debug("redis_connector_dropped name=%s error=%s", self.name, error)
        with self._lock:
            client, self._client = self._client, None
            self._start_cooldown(error)
        self._discard(client)

    @staticmethod
    def _discard(client) -> None:
        if client is None:
            return
        try:
            client.close()
        except Exception as exc:  # noqa: BLE001 -- cleanup of a client already judged broken
            logger.debug("redis_connector_close_failed error=%s", exc)


class AsyncRedisConnector(_ConnectorBase):
    """The same contract for `redis.asyncio`, for callers on the event loop.

    An asyncio client belongs to the loop it was created on, so this is only for
    callers that always run on the application's loop (ASGI middleware, the
    async cache manager) -- never for code reached through `asyncio.to_thread`.
    """

    def __init__(self, name: str, *, url: Callable[[], str] | None = None, **options: Any) -> None:
        super().__init__(name, url=url, options=options)
        self._lock: asyncio.Lock | None = None

    async def client(self):
        if self._client is not None:
            return self._client
        if self._cooling_down():
            return None
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._client is not None:
                return self._client
            if self._cooling_down():
                return None
            return await self._connect()

    async def _connect(self):
        client = None
        try:
            import redis.asyncio as aioredis  # type: ignore

            client = aioredis.from_url(self._url(), **self._options)
            await client.ping()
        except ImportError as exc:
            logger.debug("redis_connector_unavailable name=%s error=%s", self.name, exc)
            await self._discard(client)
            self._start_cooldown(exc)
            return None
        except Exception as exc:
            logger.warning("redis_connector_connect_failed name=%s error=%s", self.name, exc)
            await self._discard(client)
            self._start_cooldown(exc)
            return None
        self._client = client
        self._unavailable_until = 0.0
        self._last_error = ""
        return client

    async def drop(self, error: BaseException | str = "") -> None:
        logger.debug("redis_connector_dropped name=%s error=%s", self.name, error)
        client, self._client = self._client, None
        self._start_cooldown(error)
        await self._discard(client)

    async def close(self) -> None:
        """Release the client at shutdown without starting a cooldown."""

        client, self._client = self._client, None
        await self._discard(client)

    @staticmethod
    async def _discard(client) -> None:
        if client is None:
            return
        try:
            await client.aclose()
        except Exception as exc:  # noqa: BLE001 -- cleanup of a client already judged broken
            logger.debug("redis_connector_close_failed error=%s", exc)


__all__ = [
    "COOLDOWN_SECONDS",
    "AsyncRedisConnector",
    "RedisConnector",
    "connector_status",
    "probe",
    "redis_unavailable_errors",
]
