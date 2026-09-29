"""Wake an SSE subscriber when its execution has something new (memory mode).

The in-process stream used to poll three stores and the tracker every 50 ms per
subscriber. Writers now say "something changed for this execution" and the
subscriber sleeps until told, with a slow heartbeat as the safety net for any
writer that does not (or cannot) announce.

Writers run on worker threads (`asyncio.to_thread`) and readers on the event
loop, so `notify` hands the wake-up to each waiter's own loop with
`call_soon_threadsafe`; an `asyncio.Condition` would not be safe to touch from a
thread.

Usage on the reader side: subscribe, then loop as "clear, look, wait" so a
change that lands between the look and the wait is never missed.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import Iterator

_lock = threading.Lock()
_waiters: dict[str, set[Waiter]] = {}


class Waiter:
    """One subscriber's wake-up flag, bound to the loop it waits on."""

    __slots__ = ("_event", "_loop")

    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._event = asyncio.Event()

    def _set(self) -> None:
        self._loop.call_soon_threadsafe(self._event.set)

    def clear(self) -> None:
        self._event.clear()

    async def wait(self, timeout: float) -> bool:
        """True if woken, False on timeout (the heartbeat)."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
        except TimeoutError:
            return False
        return True


@contextlib.contextmanager
def subscribe(execution_id: str) -> Iterator[Waiter]:
    waiter = Waiter()
    with _lock:
        _waiters.setdefault(execution_id, set()).add(waiter)
    try:
        yield waiter
    finally:
        with _lock:
            group = _waiters.get(execution_id)
            if group is not None:
                group.discard(waiter)
                if not group:
                    del _waiters[execution_id]


def notify(execution_id: str) -> None:
    """Announce a change; cheap when nobody is listening."""
    with _lock:
        group = tuple(_waiters.get(execution_id, ()))
    for waiter in group:
        with contextlib.suppress(RuntimeError):  # the subscriber's loop already closed
            waiter._set()  # noqa: SLF001 - the module owns its waiters
