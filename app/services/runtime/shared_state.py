"""The Redis that state shared between workers lives in (ARC-01 phase 2 onwards).

Everything that must agree across workers -- rate limits, query-guard slots,
execution streams -- reaches Redis through here, and treats an unavailable Redis
in one way: `SharedStateUnavailable`, which the API answers with 503.

That is deliberately not what the per-purpose connectors do. A retrieval cache
that falls back to memory still returns correct answers; a rate limiter that
falls back to memory silently multiplies every limit by the number of workers,
which is the defect ARC-01 exists to remove. So with STATE_BACKEND=shared the
answer to "Redis is down" is to refuse, and say so.
"""

from __future__ import annotations

import hashlib

from app.services.runtime.redis_connector import RedisConnector

# Short timeouts: these calls sit in front of logins, uploads and queries, and a
# Redis that is slow to answer must fail fast into a 503 rather than hold the
# request for seconds first.
_CONNECTOR = RedisConnector(
    "shared_state",
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
    retry_on_timeout=False,
    health_check_interval=30,
)


class SharedStateUnavailable(RuntimeError):
    """Redis holds state every worker must agree on, and it is not answering.

    Answered with 503 by the application's exception handler. Never caught to
    fall back to process memory: that fallback is the ARC-01 defect.
    """


def is_shared() -> bool:
    """Whether this process keeps cross-worker state in Redis (STATE_BACKEND=shared)."""

    from app.core.config import get_settings

    return get_settings().state_backend == "shared"


def shared_client():
    """The shared-state client, or `SharedStateUnavailable`."""

    client = _CONNECTOR.client()
    if client is None:
        raise SharedStateUnavailable("shared state store (Redis) is unavailable")
    return client


def report_failure(error: BaseException) -> SharedStateUnavailable:
    """Record a failed command and return the exception to raise from it.

    Dropping the client starts the connector's cooldown, so the requests behind
    this one get their 503 at once instead of each waiting out the timeout.
    """

    _CONNECTOR.drop(error)
    return SharedStateUnavailable(f"shared state store (Redis) failed: {type(error).__name__}")


def is_unavailable_error(error: BaseException) -> bool:
    """Whether `error` means "Redis is not answering" rather than "something else went wrong".

    Narrower than `redis_unavailable_errors()`, deliberately. That tuple carries
    `ValueError` and `TypeError` from the query guard's history, and a payload
    that fails `json.loads` is a `ValueError` -- counting it as an outage dropped
    a healthy client and sent fifteen seconds of traffic to the fallback. A
    `ResponseError` is Redis *answering* (a script with a bug, a wrong arity),
    and reporting it as an outage would turn a defect into a 503 that points
    operators at the infrastructure.
    """

    if isinstance(error, OSError):  # includes the builtin ConnectionError and socket timeouts
        return True
    try:
        from redis.exceptions import RedisError, ResponseError  # type: ignore
    except ImportError:
        return False
    return isinstance(error, RedisError) and not isinstance(error, ResponseError)


def state_key(*parts: str) -> str:
    """A key under STATE_KEY_PREFIX, so every worker -- and nothing else -- names the same thing."""

    from app.core.config import get_settings

    return get_settings().state_key_prefix + ":".join(parts)


def opaque(value: str) -> str:
    """A stable, bounded stand-in for a caller-supplied value used in a key.

    Limiter keys carry usernames and client addresses. Redis key names are
    visible to anyone who can run SCAN or read a slow log, so they hold a digest
    rather than the value -- the same rule `question_ref` applies to logs.
    """

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


__all__ = [
    "SharedStateUnavailable",
    "is_shared",
    "is_unavailable_error",
    "opaque",
    "report_failure",
    "shared_client",
    "state_key",
]
