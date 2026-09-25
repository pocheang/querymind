"""Log levels set from the admin console reach every worker (ARC-01 phase 8).

`POST /admin/ops/logging/level` called `logging.getLogger(name).setLevel`, which
changes one process: with several workers an administrator raising a logger to
DEBUG got DEBUG from whichever worker took the request and nothing from the
rest, and `GET /logging/levels` answered from a different worker at random.

With STATE_BACKEND=shared the desired levels live in one Redis hash, and a
change is announced through the phase 6 generation counters (`log_levels`): every
other worker re-applies the hash on its next request, and a worker that starts
later applies it at startup. Outside shared mode there is one process and this
is a no-op.

Redis is written before anything changes locally, so a Redis failure is a 503
with nothing applied anywhere -- not one worker at DEBUG and the rest unaware.
"""

from __future__ import annotations

import logging

from app.services.runtime.shared_state import is_shared, is_unavailable_error, report_failure, shared_client, state_key

logger = logging.getLogger(__name__)


def _key() -> str:
    return state_key("log_levels")


def _client():
    return shared_client()


def publish_level(logger_name: str, level: str) -> None:
    """Record `logger_name` at `level` for every worker, and announce it."""

    if not is_shared():
        return
    _write(lambda client: client.hset(_key(), logger_name, level))


def publish_reset() -> None:
    """Forget every stored level, and announce it."""

    if not is_shared():
        return
    _write(lambda client: client.delete(_key()))


def stored_levels() -> dict[str, str]:
    """The levels every worker is asked to run with; empty outside shared mode."""

    if not is_shared():
        return {}
    try:
        raw = _client().hgetall(_key())
    except Exception as error:
        if is_unavailable_error(error):
            raise report_failure(error) from error
        raise
    return {_text(name): _text(level) for name, level in raw.items()}


def apply_stored_levels(*, reset_first: bool = True) -> None:
    """Make this process's levels what the hash says: defaults, then each stored level.

    `reset_first=False` is for startup: with nothing stored, a process keeps the
    levels its own logging configuration chose instead of being reset to the
    console's defaults. An announced change always resets first -- that is how a
    reset published on one worker reaches the others.
    """

    from app.services.observability.log_buffer import reset_logger_levels, set_logger_level

    levels = stored_levels()
    if reset_first:
        reset_logger_levels()
    for name, level in levels.items():
        try:
            set_logger_level(logger_name=name, level=level)
        except ValueError:
            logger.warning("shared_log_level_ignored logger=%s level=%s", name, level)


def _write(operation) -> None:
    from app.services.runtime.invalidation import announce

    try:
        operation(_client())
    except Exception as error:
        if is_unavailable_error(error):
            raise report_failure(error) from error
        raise
    announce("log_levels")


def _text(value) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)
