"""Stage outcomes behind the quality dashboards, shared by every worker (ARC-01 phase 3).

`AgentExecutionTracker` aggregates the dashboards from trace steps held in its
own process, so with several workers each admin request saw one worker's slice
of the traffic -- whichever it happened to land on. With STATE_BACKEND=shared the
tracker also records every finished stage here and aggregates from this table.

A row carries the stage, its status, how long it took, when it finished and the
*type* of error -- never the error message, which can quote what a user asked,
and never the question itself. That is all the dashboards read.

Rows are written from the event publisher on the request path, so writes are
queued (`BackgroundWriter`). Reads come from admin endpoints and are ordinary
synchronous SQLite calls.

**Rows are written in batches, one transaction for whatever is waiting.** The
first version committed once per finished stage and pruned the table in the
same transaction, and `app.db` runs `synchronous=FULL`, so every stage paid an
fsync while holding the database's only write lock. Measured on a Docker
Desktop volume, one commit took 0.84s; a query finishes several stages, so the
writer held the lock almost continuously, fell behind, and `touch_session` --
which writes on every authenticated request -- waited out its 10s busy timeout
and failed the request with `database is locked`. The table is on the same file
as the sessions, so its write rate is the sessions' problem too.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from app.services.runtime.background_writer import BackgroundWriter

# Rows older than this are pruned. The dashboards read the tracker's own window
# (an hour); a day leaves room to widen that without losing history on the way.
RETENTION_SECONDS = 24 * 3600
# Pruning is a DELETE over the whole window; once in a while is enough for a day's retention.
PRUNE_INTERVAL_SECONDS = 300
_MAX_PENDING_ROWS = 5_000


class StageStatsStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            from app.core.config import get_settings

            db_path = get_settings().app_db_path
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = BackgroundWriter("stage_stats", max_pending=_MAX_PENDING_ROWS)
        self._lock = threading.Lock()
        self._pending: list[tuple] = []
        self._drain_queued = False
        self._last_prune = float("-inf")
        self.dropped = 0
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_stage_stats (
                  execution_id TEXT NOT NULL,
                  stage TEXT NOT NULL,
                  status TEXT NOT NULL,
                  duration_ms REAL NOT NULL,
                  finished_at REAL NOT NULL,
                  error_type TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_stage_stats_finished ON execution_stage_stats(finished_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def record(
        self,
        execution_id: str,
        stage: str,
        *,
        status: str,
        duration_ms: float,
        finished_at: datetime,
        error_type: str | None,
    ) -> None:
        """Buffer one finished stage. Returns at once; never raises into the request."""

        row = (execution_id, stage, status, float(duration_ms), _timestamp(finished_at), error_type)
        with self._lock:
            if len(self._pending) >= _MAX_PENDING_ROWS:
                self.dropped += 1
                return
            self._pending.append(row)
            if self._drain_queued:
                return
            self._drain_queued = True
        if not self._writer.submit(self._drain, label=f"stage={stage}"):
            with self._lock:
                self._drain_queued = False

    def _drain(self) -> None:
        """Write everything buffered so far in one transaction."""

        with self._lock:
            # Cleared before taking the rows: a row recorded from here on queues
            # its own drain rather than waiting behind one that already left.
            self._drain_queued = False
            rows, self._pending = self._pending, []
        if rows:
            self._write_rows(rows)

    def _write_rows(self, rows: list[tuple]) -> None:
        prune = time.monotonic() - self._last_prune >= PRUNE_INTERVAL_SECONDS
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                """
                INSERT INTO execution_stage_stats
                  (execution_id, stage, status, duration_ms, finished_at, error_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            if prune:
                newest = max(row[4] for row in rows)
                conn.execute("DELETE FROM execution_stage_stats WHERE finished_at < ?", (newest - RETENTION_SECONDS,))
        if prune:
            self._last_prune = time.monotonic()

    def rows_since(self, cutoff: datetime) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT * FROM execution_stage_stats WHERE finished_at >= ? ORDER BY finished_at",
                (_timestamp(cutoff),),
            ).fetchall()

    def clear(self) -> int:
        self.flush()
        with closing(self._connect()) as conn, conn:
            return conn.execute("DELETE FROM execution_stage_stats").rowcount

    def flush(self, timeout: float = 5.0) -> bool:
        return self._writer.flush(timeout)


def _timestamp(moment: datetime) -> float:
    """The tracker's datetimes are timezone-aware UTC; a naive one is read as UTC, never local time."""

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.timestamp()


def from_timestamp(value: float) -> datetime:
    """Back to the tracker's convention: timezone-aware UTC, so it compares with `utcnow()`."""

    return datetime.fromtimestamp(value, UTC)


__all__ = ["RETENTION_SECONDS", "StageStatsStore", "from_timestamp"]
