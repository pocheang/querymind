"""Bookkeeping writes to app.db must not be able to fail a request (ARC-01 phase 6).

Found running two uvicorn workers against the real stack: a query came back
500 `database is locked` from `touch_session`, the UPDATE of `last_seen_at`
that ran on every authenticated request. Nothing else was running. The holder,
located by instrumenting the container, was the stage-statistics writer: one
commit per finished stage, plus a prune each time, on a file running
`synchronous=FULL` -- 0.84s per commit on a Docker Desktop volume, several per
query, so it held the database's only write lock almost continuously and the
session touch waited out its 10s busy timeout.

Two defects, one on each side, and both are pinned here:

- the statistics writer commits once per *batch* and prunes once per interval;
- the session touch writes at most once a minute, decided by a read (which in
  WAL mode never waits for a writer), and a touch that still meets contention
  is skipped rather than raised.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import get_settings
from app.services.auth import session_manager as sessions
from app.services.auth.auth_service import AuthDBService
from app.services.auth.utils import iso, now
from app.services.observability import stage_stats
from app.services.observability.stage_stats import StageStatsStore


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("SQLITE_BUSY_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _record(store: StageStatsStore, n: int, *, at: datetime | None = None) -> None:
    moment = at or datetime.now(UTC)
    for i in range(n):
        store.record(f"exec-{i}", "knowledge", status="completed", duration_ms=1.0, finished_at=moment, error_type=None)


def _count(db_path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT COUNT(*) FROM execution_stage_stats").fetchone()[0]
    finally:
        conn.close()


# ---- the statistics writer ------------------------------------------------------


def test_stages_recorded_while_a_write_is_running_share_the_next_transaction(tmp_path, monkeypatch):
    store = StageStatsStore(db_path=tmp_path / "app.db")
    batches: list[int] = []
    first_started, release = threading.Event(), threading.Event()
    real = store._write_rows

    def gated(rows):
        batches.append(len(rows))
        if len(batches) == 1:
            first_started.set()
            release.wait(5)
        real(rows)

    monkeypatch.setattr(store, "_write_rows", gated)
    _record(store, 1)
    assert first_started.wait(5)
    _record(store, 49)
    release.set()
    assert store.flush()

    assert batches == [1, 49]
    assert _count(tmp_path / "app.db") == 50


class _Closable(sqlite3.Connection):
    closed = False

    def close(self):
        self.closed = True
        super().close()


def test_the_writer_closes_every_connection_it_opens(tmp_path, monkeypatch):
    # Recorded by the connection itself: the write connection belongs to the
    # writer thread, so probing it from here raises ProgrammingError whether or
    # not it is closed -- the first version of this test passed on a leak.
    store = StageStatsStore(db_path=tmp_path / "app.db")
    opened: list[_Closable] = []

    def tracking():
        conn = sqlite3.connect(store.db_path, timeout=10.0, factory=_Closable)
        conn.row_factory = sqlite3.Row
        opened.append(conn)
        return conn

    monkeypatch.setattr(store, "_connect", tracking)
    _record(store, 5)
    assert store.flush()
    store.rows_since(datetime.now(UTC) - timedelta(hours=1))
    store.clear()

    assert len(opened) == 3
    assert [conn.closed for conn in opened] == [True, True, True]


def test_old_rows_are_pruned_once_per_interval_not_on_every_write(tmp_path):
    db = tmp_path / "app.db"
    store = StageStatsStore(db_path=db)
    _record(store, 1)
    assert store.flush()

    stale = datetime.now(UTC) - timedelta(seconds=stage_stats.RETENTION_SECONDS + 60)
    conn = sqlite3.connect(db)
    with conn:
        conn.execute(
            "INSERT INTO execution_stage_stats VALUES ('old', 'router', 'completed', 1.0, ?, NULL)",
            (stale.timestamp(),),
        )
    conn.close()

    _record(store, 1)
    assert store.flush()
    assert _count(db) == 3, "pruned again inside the interval"

    store._last_prune -= stage_stats.PRUNE_INTERVAL_SECONDS
    _record(store, 1)
    assert store.flush()
    assert _count(db) == 3, "the stale row should be gone and the new one added"
    rows = store.rows_since(stale - timedelta(seconds=1))
    assert all(row["execution_id"] != "old" for row in rows)


# ---- the session touch --------------------------------------------------------


@pytest.fixture
def auth(tmp_path):
    service = AuthDBService(db_path=tmp_path / "auth.db", token_ttl_hours=1)
    service.register("alice", "Correct-Horse-Battery-9")
    token = service.login("alice", "Correct-Horse-Battery-9")["token"]
    return service, token, tmp_path / "auth.db"


def _set_last_seen(db_path, token: str, when: datetime) -> None:
    conn = sqlite3.connect(db_path)
    with conn:
        conn.execute("UPDATE auth_sessions SET last_seen_at=? WHERE token=?", (iso(when), token))
    conn.close()


def _last_seen(db_path, token: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT last_seen_at FROM auth_sessions WHERE token=?", (token,)).fetchone()[0]
    finally:
        conn.close()


class _WriteLockHeld:
    """Another connection holding the write lock for the duration of the block."""

    def __init__(self, db_path):
        self._conn = sqlite3.connect(db_path, isolation_level=None)

    def __enter__(self):
        self._conn.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, *exc):
        self._conn.execute("ROLLBACK")
        self._conn.close()


def test_a_recent_touch_does_not_ask_for_the_write_lock(auth):
    service, token, db = auth
    _set_last_seen(db, token, now() - timedelta(seconds=5))

    with _WriteLockHeld(db):
        started = time.perf_counter()
        service.touch_session(token)
        elapsed = time.perf_counter() - started

    assert elapsed < 0.5, f"waited {elapsed:.2f}s -- it tried to write"


def test_a_touch_that_meets_a_held_lock_is_skipped_not_raised(auth, caplog):
    service, token, db = auth
    stale = now() - timedelta(seconds=sessions.TOUCH_INTERVAL_SECONDS + 30)
    _set_last_seen(db, token, stale)

    with _WriteLockHeld(db), caplog.at_level(logging.WARNING, logger=sessions.__name__):
        service.touch_session(token)

    assert _last_seen(db, token) == iso(stale)
    assert "session_touch_skipped" in caplog.text
    assert token not in caplog.text


def test_a_stale_touch_still_records_when_nothing_is_in_the_way(auth):
    service, token, db = auth
    stale = now() - timedelta(seconds=sessions.TOUCH_INTERVAL_SECONDS + 30)
    _set_last_seen(db, token, stale)

    service.touch_session(token)

    assert _last_seen(db, token) != iso(stale)


def test_only_lock_contention_is_forgiven():
    assert sessions._is_contention(sqlite3.OperationalError("database is locked"))
    assert sessions._is_contention(sqlite3.OperationalError("database table is locked"))
    assert not sessions._is_contention(sqlite3.OperationalError("no such table: auth_sessions"))
    assert not sessions._is_contention(sqlite3.OperationalError("disk I/O error"))
