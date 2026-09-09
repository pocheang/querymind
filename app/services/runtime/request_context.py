from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_REQUEST_DEADLINE_TS: ContextVar[float] = ContextVar("request_deadline_ts", default=0.0)
_REQUEST_OVERLOAD: ContextVar[bool] = ContextVar("request_overload_mode", default=False)


def get_deadline_ts() -> float:
    return float(_REQUEST_DEADLINE_TS.get() or 0.0)


def remaining_seconds() -> float | None:
    deadline = get_deadline_ts()
    if deadline <= 0:
        return None
    return max(0.0, deadline - time.monotonic())


def deadline_exceeded() -> bool:
    deadline = get_deadline_ts()
    return bool(deadline > 0 and time.monotonic() > deadline)


def overload_mode_enabled() -> bool:
    return bool(_REQUEST_OVERLOAD.get())


@contextmanager
def request_context(*, timeout_ms: int, overload_mode: bool) -> Iterator[None]:
    """Carry the caller's deadline and overload flag across a request.

    It used to carry a model configuration too, so that a request could be
    answered with the asking user's own provider and key. Nothing on the answer
    path ever set it, and per-user model configuration was removed on
    2026-09-08: models are configured by an administrator, for everyone.
    """
    deadline = time.monotonic() + (max(1, int(timeout_ms)) / 1000.0)
    token_deadline: Token = _REQUEST_DEADLINE_TS.set(deadline)
    token_overload: Token = _REQUEST_OVERLOAD.set(bool(overload_mode))
    try:
        yield
    finally:
        _REQUEST_DEADLINE_TS.reset(token_deadline)
        _REQUEST_OVERLOAD.reset(token_overload)
