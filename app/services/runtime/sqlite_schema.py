"""Versioned schema migrations for the SQLite stores (ARC-01 phase 7, ARC-04).

Every store used to create its tables in its constructor, and add columns by
asking `PRAGMA table_info` and running `ALTER TABLE ... ADD COLUMN` when one was
missing. Two processes starting together both saw the column missing and both
added it; the second died with `duplicate column name`. Nothing recorded which
version a database was at, so there was no way to run a migration that did more
than add a column, or to tell which one had run.

Now each store names its component and an ordered list of migrations, and
`ensure_schema` brings the database up to the last one:

- the versions live in a `schema_versions` table, one row per component --
  several stores share `app.db`, so a single `PRAGMA user_version` cannot hold
  them (and the long-term memory store already uses `user_version` for itself);
- when the database is already current, which is every start but the first,
  this is one read and takes no write lock;
- otherwise the pending migrations run in one `BEGIN IMMEDIATE` transaction,
  which re-reads the version first: a second process waits for the first and
  then finds nothing to do. SQLite DDL is transactional, so a migration that
  fails leaves the database at the version it started from.

Migration 1 of every store is the setup it already had -- `CREATE ... IF NOT
EXISTS` and add-if-missing -- so a database created before this module existed
is brought to version 1 without being rebuilt. A migration must not commit:
`executescript` and `Connection.commit()` would end the transaction early.

WAL is set here rather than on every connection. `PRAGMA journal_mode=WAL` needs
an exclusive lock and SQLite answers it with `database is locked` at once
instead of waiting, so it is retried until the busy timeout runs out; it is a
persistent property of the file, so once is enough.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    apply: Callable[[sqlite3.Connection], None]


class SchemaVersionError(RuntimeError):
    """The database was migrated by a newer build than this one."""


def ensure_schema(
    db_path: Path | str,
    component: str,
    migrations: Sequence[Migration],
    *,
    wal: bool = False,
    timeout_seconds: float | None = None,
) -> int:
    """Bring `component` in the database at `db_path` up to its last migration; return that version."""

    target = _validated_target(component, migrations)
    timeout = _DEFAULT_TIMEOUT_SECONDS if timeout_seconds is None else float(timeout_seconds)
    conn = sqlite3.connect(str(db_path), timeout=timeout, isolation_level=None)
    conn.row_factory = sqlite3.Row
    with closing(conn):
        if wal:
            _ensure_wal(conn, timeout)
        if _current_version(conn, component) == target:
            return target
        return _migrate(conn, component, migrations, target)


def schema_version(db_path: Path | str, component: str) -> int:
    """The version `component` is at in `db_path`; 0 when it has never been migrated."""

    with closing(sqlite3.connect(str(db_path))) as conn:
        return _current_version(conn, component)


def _validated_target(component: str, migrations: Sequence[Migration]) -> int:
    versions = [migration.version for migration in migrations]
    if not component or not versions or versions != list(range(1, len(versions) + 1)):
        raise ValueError(f"{component!r}: migrations must be numbered 1..N in order, got {versions}")
    return len(versions)


def _current_version(conn: sqlite3.Connection, component: str) -> int:
    try:
        row = conn.execute("SELECT version FROM schema_versions WHERE component=?", (component,)).fetchone()
    except sqlite3.OperationalError as error:
        if "no such table" in str(error).lower():
            return 0
        raise
    return int(row[0]) if row else 0


def _migrate(conn: sqlite3.Connection, component: str, migrations: Sequence[Migration], target: int) -> int:
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_versions (component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        # Re-read under the write lock: another process may have finished while
        # this one waited for it.
        start = _current_version(conn, component)
        if start > target:
            raise SchemaVersionError(
                f"{component} is at schema version {start}; this build knows versions up to {target}"
            )
        for migration in migrations[start:]:
            migration.apply(conn)
        conn.execute(
            "INSERT INTO schema_versions(component, version) VALUES (?, ?) "
            "ON CONFLICT(component) DO UPDATE SET version=excluded.version",
            (component, target),
        )
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    if start < target:
        logger.info("schema_migrated component=%s from=%d to=%d", component, start, target)
    return target


def _ensure_wal(conn: sqlite3.Connection, timeout: float) -> None:
    if str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal":
        return
    deadline = time.monotonic() + timeout
    delay = 0.02
    while True:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError as error:
            if "locked" not in str(error).lower() or time.monotonic() + delay > deadline:
                raise
        time.sleep(delay)
        delay = min(delay * 2, 0.5)


__all__ = ["Migration", "SchemaVersionError", "ensure_schema", "schema_version"]
