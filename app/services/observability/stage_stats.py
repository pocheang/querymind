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
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.services.runtime.background_writer import BackgroundWriter

# Rows older than this are pruned. The dashboards read the tracker's own window
# (an hour); a day leaves room to widen that without losing history on the way.
RETENTION_SECONDS = 24 * 3600


class StageStatsStore:
    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            from app.core.config import get_settings

            db_path = get_settings().app_db_path
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = BackgroundWriter("stage_stats", max_pending=5_000)
        with self._connect() as conn:
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
        """Queue one finished stage. Returns at once; never raises into the request."""

        finished = _timestamp(finished_at)

        def write() -> None:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO execution_stage_stats
                      (execution_id, stage, status, duration_ms, finished_at, error_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (execution_id, stage, status, float(duration_ms), finished, error_type),
                )
                conn.execute("DELETE FROM execution_stage_stats WHERE finished_at < ?", (finished - RETENTION_SECONDS,))

        self._writer.submit(write, label=f"stage={stage}")

    def rows_since(self, cutoff: datetime) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM execution_stage_stats WHERE finished_at >= ? ORDER BY finished_at",
                (_timestamp(cutoff),),
            ).fetchall()

    def clear(self) -> int:
        self.flush()
        with self._connect() as conn:
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
