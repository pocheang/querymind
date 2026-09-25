"""Versioned SQLite migrations (ARC-01 phase 7, ARC-04): `app/services/runtime/sqlite_schema.py`.

The defect these replace: every store created its tables in its constructor and
added columns by checking `PRAGMA table_info` first. Two processes starting
together both found a column missing and both added it, and the second died --
the same shape as `PRAGMA journal_mode=WAL`, which fails at once rather than
waiting while another connection writes.

The race is tested with real processes, because a thread shares the module and
the connection-level behaviour that matters here is between processes.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from app.services.runtime.sqlite_schema import Migration, SchemaVersionError, ensure_schema, schema_version

ROOT = Path(__file__).resolve().parents[2]


def _create_items(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")


def _add_colour(conn: sqlite3.Connection) -> None:
    # Deliberately not add-if-missing: a migration runs once, so it need not be.
    conn.execute("ALTER TABLE items ADD COLUMN colour TEXT")


V1 = (Migration(1, "items", _create_items),)
V2 = (*V1, Migration(2, "colour", _add_colour))


def _columns(db: Path, table: str) -> list[str]:
    with sqlite3.connect(db) as conn:
        return [str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")]


def test_a_fresh_database_is_created_and_versioned(tmp_path):
    db = tmp_path / "app.db"

    assert ensure_schema(db, "demo", V2) == 2

    assert _columns(db, "items") == ["id", "name", "colour"]
    assert schema_version(db, "demo") == 2


def test_each_component_keeps_its_own_version_in_one_file(tmp_path):
    db = tmp_path / "app.db"
    ensure_schema(db, "demo", V1)
    ensure_schema(db, "other", (Migration(1, "t", lambda c: c.execute("CREATE TABLE t (x)")),))

    assert (schema_version(db, "demo"), schema_version(db, "other")) == (1, 1)


def test_only_pending_migrations_run(tmp_path):
    db = tmp_path / "app.db"
    ensure_schema(db, "demo", V1)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO items(name) VALUES ('kept')")

    def create_once(conn: sqlite3.Connection) -> None:
        # Fails if run twice: version 1 is already applied and must be skipped.
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")

    assert ensure_schema(db, "demo", (Migration(1, "items", create_once), V2[1])) == 2

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name, colour FROM items").fetchall() == [("kept", None)]


def test_a_current_database_does_not_ask_for_the_write_lock(tmp_path):
    db = tmp_path / "app.db"
    ensure_schema(db, "demo", V2)
    holder = sqlite3.connect(db, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        started = time.perf_counter()
        ensure_schema(db, "demo", V2, timeout_seconds=2)
        elapsed = time.perf_counter() - started
    finally:
        holder.execute("ROLLBACK")
        holder.close()

    assert elapsed < 0.5, f"waited {elapsed:.2f}s on a database that needed nothing"


def test_a_failing_migration_leaves_the_database_where_it_was(tmp_path):
    db = tmp_path / "app.db"
    ensure_schema(db, "demo", V1)

    def half_done(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE half (x)")
        raise RuntimeError("migration 2 failed")

    with pytest.raises(RuntimeError, match="migration 2 failed"):
        ensure_schema(db, "demo", (*V1, Migration(2, "half", half_done)))

    assert schema_version(db, "demo") == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='half'").fetchone() is None


def test_a_database_from_a_newer_build_is_refused(tmp_path):
    db = tmp_path / "app.db"
    ensure_schema(db, "demo", V2)

    with pytest.raises(SchemaVersionError, match="version 2"):
        ensure_schema(db, "demo", V1)


@pytest.mark.parametrize("versions", [(2,), (1, 3), (1, 1), ()])
def test_migrations_must_be_numbered_from_one_without_gaps(tmp_path, versions):
    migrations = tuple(Migration(v, "x", _create_items) for v in versions)

    with pytest.raises(ValueError, match="numbered 1..N"):
        ensure_schema(tmp_path / "app.db", "demo", migrations)


def test_wal_is_set_once_and_waits_for_a_writer_rather_than_failing(tmp_path):
    db = tmp_path / "app.db"
    holder = sqlite3.connect(db, isolation_level=None, check_same_thread=False)
    holder.execute("CREATE TABLE warmup (x)")
    holder.execute("BEGIN IMMEDIATE")
    holder.execute("INSERT INTO warmup VALUES (1)")

    def release() -> None:
        holder.execute("COMMIT")
        holder.close()

    timer = threading.Timer(0.5, release)
    timer.start()
    try:
        started = time.perf_counter()
        ensure_schema(db, "demo", V1, wal=True, timeout_seconds=5)
        elapsed = time.perf_counter() - started
    finally:
        timer.join()

    assert elapsed >= 0.4, "returned before the writer let go"
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


# Each racer imports first and then waits for a shared "go" file, and the second
# migration holds its transaction a moment: started one after another, Python's
# import time alone spreads the processes about a second apart, so the first
# version of this test never had two of them in the database at once -- and a
# deferred BEGIN, or re-running every migration, passed it.
_RACER = textwrap.dedent(
    """
    import os, sqlite3, sys, time
    sys.path.insert(0, sys.argv[2])
    from app.services.runtime.sqlite_schema import Migration, ensure_schema

    def items(conn):
        conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)")

    def colour(conn):
        conn.execute("ALTER TABLE items ADD COLUMN colour TEXT")
        time.sleep(0.3)

    go = sys.argv[3]
    while not os.path.exists(go):
        time.sleep(0.005)
    print(ensure_schema(sys.argv[1], "demo", (Migration(1, "i", items), Migration(2, "c", colour)), wal=True))
    """
)


def test_processes_migrating_at_once_all_succeed_and_each_step_runs_once(tmp_path):
    db = tmp_path / "app.db"
    script = tmp_path / "racer.py"
    script.write_text(_RACER, encoding="utf-8")

    go = tmp_path / "go"
    racers = [
        subprocess.Popen(
            [sys.executable, str(script), str(db), str(ROOT), str(go)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    time.sleep(3)  # every racer has imported and is polling for the file
    go.write_text("", encoding="utf-8")
    results = [racer.communicate(timeout=60) for racer in racers]

    assert [racer.returncode for racer in racers] == [0, 0, 0, 0], [err for _, err in results]
    assert [out.strip() for out, _ in results] == ["2"] * 4
    assert _columns(db, "items") == ["id", "name", "colour"]
