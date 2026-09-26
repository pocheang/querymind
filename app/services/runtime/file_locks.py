"""Cross-process file locks and atomic rewrites for the index files (ARC-01 phase 5).

The index is a set of files that are read whole and rewritten whole --
`chunks.jsonl`, `parents.jsonl`, `documents.jsonl` -- plus a Chroma collection
kept in step with them. Their locks were `threading` locks or nothing at all,
and the rewrite truncated the file first (`open("w")`), so:

- two ingests, even the two threads of one process's ingest pool, each wrote
  back the corpus they had read and one document's chunks were lost (BUG-05);
- a reader such as BM25 could open the file between the truncate and the last
  line and index half the corpus.

A `FileLock` is what serializes processes on one host, and `write_lines`
writes a temporary file beside the target and `os.replace`s it in, so a reader
sees the old file or the new one and never a prefix of either.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

# One FileLock per lock file per process. FileLock is reentrant per thread
# (`thread_local=True`), so a function holding the index lock can call another
# that takes it again; a second thread opens its own handle and waits on the OS
# lock like another process would.
_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[str, FileLock] = {}


class LockBusy(RuntimeError):
    """The lock was not free within the time the caller could wait."""


def _lock_for(lock_path: Path) -> FileLock:
    key = str(lock_path.resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock = FileLock(key, thread_local=True)
            _LOCKS[key] = lock
        return lock


@contextmanager
def held(lock_path: Path, *, timeout: float | None = None) -> Iterator[None]:
    """Hold the lock at `lock_path` for the block. `timeout=None` waits as long as it takes."""

    lock = _lock_for(lock_path)
    try:
        lock.acquire(timeout=-1 if timeout is None else timeout)
    except Timeout as error:
        raise LockBusy(f"{lock_path.name} is held by another writer") from error
    try:
        yield
    finally:
        lock.release()


def write_lines(target: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Replace `target` with one JSON object per line, atomically."""

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent, prefix=f".{target.name}.", delete=False, buffering=65536
        ) as handle:
            temporary = Path(handle.name)
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _replace(source: Path, target: Path) -> None:
    # Windows refuses to replace a file another handle has open, which a reader
    # of the index briefly does; POSIX never raises here.
    for attempt in range(5):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))
