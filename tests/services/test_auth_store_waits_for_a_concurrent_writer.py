"""A second worker must wait for the first one's write, not crash on it.

Two workers started together both construct `AuthDBService` at import time
(`app/api/deps/auth.py`), and the one that arrives while the other holds a
write lock dies with `database is locked` -- in milliseconds, although
`_connect` sets a 10 second `busy_timeout` the line before. `PRAGMA
journal_mode=WAL` needs an exclusive lock, and SQLite answers a connection
that would have to wait behind a RESERVED writer with SQLITE_BUSY at once
rather than invoking the busy handler, because waiting there can deadlock.

Two uvicorn processes racing each other reproduce this only sometimes
(measured: one attempt in two on Windows), so a strict xfail built on them
would XPASS by luck. Holding the lock ourselves makes it certain: 10 of 10 on
both lock kinds, measured before this file was written.

The exclusive-lock case is the control. It proves the harness really holds a
lock, really releases it, and that the store really waits -- so the xfail
below could only be failing for the reason it named.

ARC-01 phase 7 fixed it, and the strict xfail turned red the moment it did:
the schema is created by `app/services/runtime/sqlite_schema.py`, which asks
for WAL only when the file is not already in WAL mode and retries while it is
locked, and runs the rest in a `BEGIN IMMEDIATE` transaction that waits.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.auth.auth_service import AuthDBService

_HOLD_SECONDS = 0.5


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _construct_while_another_connection_holds(lock_statement: str, db_path: Path) -> float:
    """Hold `lock_statement` on another connection for `_HOLD_SECONDS`, construct meanwhile.

    Returns how long the constructor took. The holder is released from a timer
    thread, so it needs `check_same_thread=False`; without it the release
    raises in that thread, the lock is never dropped, and the constructor
    waits out its whole busy timeout instead.
    """

    holder = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    # The file exists before the lock is taken, still in the default DELETE
    # journal mode -- the state a second worker finds the first one in.
    holder.execute("CREATE TABLE warmup(x)")
    holder.execute(lock_statement)
    holder.execute("INSERT INTO warmup VALUES (1)")

    def release() -> None:
        holder.execute("COMMIT")
        holder.close()

    timer = threading.Timer(_HOLD_SECONDS, release)
    timer.start()
    started = time.perf_counter()
    try:
        AuthDBService(db_path=db_path)
        return time.perf_counter() - started
    finally:
        # Whatever the constructor did, the lock is released and the
        # connection closed before the next test runs.
        timer.join()


def test_the_store_waits_for_an_exclusive_lock_to_clear(tmp_path):
    elapsed = _construct_while_another_connection_holds("BEGIN EXCLUSIVE", tmp_path / "app.db")

    assert elapsed >= _HOLD_SECONDS * 0.8, f"returned after {elapsed:.3f}s -- it did not wait for the lock"


def test_the_store_waits_for_a_concurrent_writer(tmp_path):
    elapsed = _construct_while_another_connection_holds("BEGIN IMMEDIATE", tmp_path / "app.db")

    assert elapsed >= _HOLD_SECONDS * 0.8, f"returned after {elapsed:.3f}s -- it did not wait for the lock"
