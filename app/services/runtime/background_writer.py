"""A bounded queue and one daemon thread, for writes that must not run on the request path.

CLAUDE.md's rule for reporters that need I/O: push to an in-memory buffer and
return immediately. Three places need exactly that -- governed-tool audit rows,
the shared execution stream, and the stage statistics behind the quality
dashboard -- and each had grown its own copy of this class. One definition, so
"what happens when the writer cannot keep up" has one answer:

- `submit` never blocks and never raises. A full queue drops the write and logs
  it at ERROR with a running count, because the alternative is blocking the
  request whose observation this is.
- A write that raises is handed to `on_error` (logged by default) and the thread
  carries on with the next one.
- Writes run in the order they were submitted, on one thread.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


class BackgroundWriter:
    def __init__(
        self,
        name: str,
        *,
        max_pending: int = 1_000,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        self.name = name
        self.dropped = 0
        self._queue: queue.Queue[Callable[[], None]] = queue.Queue(maxsize=max(1, int(max_pending)))
        self._on_error = on_error
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def submit(self, write: Callable[[], None], *, label: str = "") -> bool:
        """Queue `write`; False (and an ERROR line) if it had to be dropped."""

        self._ensure_thread()
        try:
            self._queue.put_nowait(write)
        except queue.Full:
            self.dropped += 1
            logger.error(
                "%s_dropped %s dropped_total=%d -- the writer is not keeping up", self.name, label, self.dropped
            )
            return False
        return True

    def flush(self, timeout: float = 5.0) -> bool:
        """Wait until every queued write has run. True if it drained in time."""

        deadline = time.monotonic() + timeout
        while self._queue.unfinished_tasks:
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def _ensure_thread(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name=f"{self.name}-writer", daemon=True)
                self._thread.start()

    def _run(self) -> None:
        while True:
            write = self._queue.get()
            try:
                write()
            except Exception as exc:
                if self._on_error is not None:
                    self._on_error(exc)
                else:
                    logger.exception("%s_write_failed", self.name)
            finally:
                self._queue.task_done()


__all__ = ["BackgroundWriter"]
