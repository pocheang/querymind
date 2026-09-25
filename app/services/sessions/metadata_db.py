"""
Database models and persistence layer for session metadata.

Provides SQLite-backed storage with LRU cache for performance.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.runtime.sqlite_schema import Migration, ensure_schema
from app.services.sessions.metadata import (
    MetadataUpdate,
    SessionCategory,
    SessionMetadata,
    as_utc,
    normalize_description,
    normalize_tags,
    utc_now,
)

__all__ = [
    "SessionMetadataDB",
    "get_metadata_db",
]

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "./data/querymind.db"


# ============================================================================
# Database Schema
# ============================================================================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS session_metadata (
    session_id TEXT PRIMARY KEY,
    tags TEXT NOT NULL,  -- JSON array
    category TEXT,
    description TEXT,
    auto_tags TEXT NOT NULL,  -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    query_count INTEGER NOT NULL DEFAULT 0,
    last_query_at TEXT
)
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_session_updated_at ON session_metadata(updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_session_category ON session_metadata(category)",
    "CREATE INDEX IF NOT EXISTS idx_session_query_count ON session_metadata(query_count)",
    # 安全修复：添加复合索引以优化常见查询模式
    "CREATE INDEX IF NOT EXISTS idx_session_category_updated ON session_metadata(category, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_session_last_query ON session_metadata(last_query_at DESC) WHERE last_query_at IS NOT NULL",
]


# ============================================================================
# Database-Backed Metadata Service
# ============================================================================


def _metadata_baseline(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    for index_sql in CREATE_INDEXES_SQL:
        conn.execute(index_sql)


SESSION_METADATA_MIGRATIONS = (Migration(1, "baseline: session_metadata and its indexes", _metadata_baseline),)


def ensure_session_metadata_schema(db_path: Path | None = None) -> int:
    """Create or upgrade the session-metadata table; safe from any number of processes at once."""

    path = Path(db_path or SessionMetadataDB._get_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    return ensure_schema(path, "session_metadata", SESSION_METADATA_MIGRATIONS, wal=True)


class SessionMetadataDB:
    """
    Database-backed session metadata service.

    Architecture:
    - L2 Storage: SQLite (persistent, survives restarts)

    No in-process cache (ARC-01 phase 6). It had one -- an LRU read first,
    with no expiry, per database file for the life of the process -- so with two
    workers, tags edited on one were never seen by the other, and `update`
    read the stale copy and wrote all of it back, undoing the other worker's
    edits and losing its query counts. These are small per-user SQLite files;
    every read goes to the file, and each read-modify-write is one
    `BEGIN IMMEDIATE` transaction.
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize database-backed metadata service.

        Args:
            db_path: Path to SQLite database (defaults to querymind.db)
        """
        get_settings()
        self.db_path = db_path or self._get_db_path()
        ensure_session_metadata_schema(self.db_path)

    @staticmethod
    def _get_db_path(settings=None) -> Path:
        """The database DATABASE_URL names -- in `settings` when given, else the process's."""
        settings = settings or get_settings()
        # Parse DATABASE_URL (e.g. "sqlite:///./data/querymind.db")
        db_url = getattr(settings, "database_url", "sqlite:///./data/querymind.db")
        if db_url.startswith("sqlite:///"):
            path_str = db_url[10:]  # Remove "sqlite:///"
            return Path(path_str).resolve()
        # Anything else is not supported -- this store is SQLite only -- and the
        # fallback used to be silent. A deployment once set
        # DATABASE_URL=postgresql+asyncpg://... in compose and nothing said that
        # the application had ignored it and written a local file instead.
        logger.warning(
            "DATABASE_URL is not a sqlite:/// URL; this store is SQLite only and is using %s",
            _DEFAULT_DB_PATH,
        )
        return Path(_DEFAULT_DB_PATH).resolve()

    def _connect(self) -> sqlite3.Connection:
        """Create database connection."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL is set once, by the migration (ensure_session_metadata_schema).
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        """One write transaction; an exception rolls it back when the connection closes."""
        with closing(self._connect()) as conn:
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")

    def _row(self, conn: sqlite3.Connection, session_id: str) -> SessionMetadata | None:
        row = conn.execute("SELECT * FROM session_metadata WHERE session_id = ?", (session_id,)).fetchone()
        return self._deserialize_row(row) if row else None

    def _serialize_metadata(self, metadata: SessionMetadata) -> dict[str, Any]:
        """Serialize SessionMetadata to database row."""
        return {
            "session_id": metadata.session_id,
            "tags": json.dumps(metadata.tags),
            "category": metadata.category,
            "description": metadata.description,
            "auto_tags": json.dumps(metadata.auto_tags),
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "query_count": metadata.query_count,
            "last_query_at": metadata.last_query_at.isoformat() if metadata.last_query_at else None,
        }

    def _deserialize_row(self, row: sqlite3.Row) -> SessionMetadata:
        """Deserialize database row to SessionMetadata."""
        return SessionMetadata(
            session_id=row["session_id"],
            tags=json.loads(row["tags"]),
            category=row["category"],
            description=row["description"],
            auto_tags=json.loads(row["auto_tags"]),
            # as_utc, not fromisoformat alone: rows written before 2026-09-02 are
            # naive, and one of those beside an aware one is a TypeError the
            # moment search.py sorts on it.
            created_at=as_utc(datetime.fromisoformat(row["created_at"])),
            updated_at=as_utc(datetime.fromisoformat(row["updated_at"])),
            query_count=row["query_count"],
            last_query_at=as_utc(datetime.fromisoformat(row["last_query_at"])) if row["last_query_at"] else None,
        )

    def create(self, metadata: SessionMetadata) -> SessionMetadata:
        """Create new session metadata; ValueError if the session already has some."""
        with self._write() as conn:
            if self._row(conn, metadata.session_id) is not None:
                raise ValueError(f"Metadata already exists for session {metadata.session_id}")
            conn.execute(
                """
                INSERT INTO session_metadata
                (session_id, tags, category, description, auto_tags, created_at, updated_at, query_count, last_query_at)
                VALUES (:session_id, :tags, :category, :description, :auto_tags, :created_at, :updated_at, :query_count, :last_query_at)
                """,
                self._serialize_metadata(metadata),
            )
        return metadata

    def get(self, session_id: str) -> SessionMetadata | None:
        """Session metadata, read from the database, or None."""
        with closing(self._connect()) as conn:
            return self._row(conn, session_id)

    def get_metadata(self, session_id: str) -> SessionMetadata | None:
        """
        Get session metadata (alias for get).

        Args:
            session_id: Session identifier

        Returns:
            Metadata or None if not found
        """
        return self.get(session_id)

    def create_metadata(
        self,
        session_id: str,
        tags: list[str] | None = None,
        category: SessionCategory | None = None,
        description: str | None = None,
    ) -> SessionMetadata:
        """
        Create new session metadata (alias for create).

        Args:
            session_id: Unique session identifier
            tags: User-defined tags
            category: Session category
            description: Session description

        Returns:
            Created metadata

        Raises:
            ValueError: If session already exists
        """
        metadata = SessionMetadata(
            session_id=session_id,
            tags=normalize_tags(tags or []),
            category=category,
            description=normalize_description(description),
        )
        return self.create(metadata)

    def update_metadata(
        self,
        session_id: str,
        update: MetadataUpdate,
    ) -> SessionMetadata:
        """
        Update existing session metadata (alias for update).

        Args:
            session_id: Session to update
            update: Update specification

        Returns:
            Updated metadata

        Raises:
            KeyError: If session not found
        """
        return self.update(session_id, update)

    def delete_metadata(self, session_id: str) -> bool:
        """
        Delete session metadata (alias for delete).

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        return self.delete(session_id)

    def list_all_metadata(self) -> list[SessionMetadata]:
        """
        List all session metadata (alias for list_all).

        Returns:
            List of all metadata (most recently updated first)
        """
        return self.list_all()

    def extract_and_update_auto_tags(
        self,
        session_id: str,
        messages: list[dict],
        max_tags: int = 5,
    ) -> list[str]:
        """Extract automatic tags from messages and store them; KeyError if the session has no metadata."""
        from app.services.sessions.metadata import TagExtractor

        auto_tags = TagExtractor().extract_tags(messages, max_tags=max_tags)
        with self._write() as conn:
            metadata = self._row(conn, session_id)
            if not metadata:
                raise KeyError(f"Session not found: {session_id}")
            metadata.auto_tags = auto_tags
            metadata.updated_at = utc_now()
            conn.execute(
                "UPDATE session_metadata SET auto_tags = :auto_tags, updated_at = :updated_at WHERE session_id = :session_id",
                self._serialize_metadata(metadata),
            )
        return auto_tags

    def update(self, session_id: str, update: MetadataUpdate) -> SessionMetadata:
        """Apply `update` to the stored row in one transaction; KeyError if there is none."""
        with self._write() as conn:
            metadata = self._row(conn, session_id)
            if not metadata:
                raise KeyError(f"Session not found: {session_id}")
            if update.tags is not None:
                metadata.tags = normalize_tags(update.tags)
            if update.category is not None:
                metadata.category = update.category
            if update.description is not None:
                metadata.description = normalize_description(update.description)
            if update.increment_query_count:
                metadata.query_count += 1
                metadata.last_query_at = utc_now()
            metadata.updated_at = utc_now()
            conn.execute(
                """
                UPDATE session_metadata
                SET tags = :tags,
                    category = :category,
                    description = :description,
                    auto_tags = :auto_tags,
                    updated_at = :updated_at,
                    query_count = :query_count,
                    last_query_at = :last_query_at
                WHERE session_id = :session_id
                """,
                self._serialize_metadata(metadata),
            )
        return metadata

    def delete(self, session_id: str) -> bool:
        """Delete session metadata; True if there was any."""
        with self._write() as conn:
            return conn.execute("DELETE FROM session_metadata WHERE session_id = ?", (session_id,)).rowcount > 0

    def list_all(self, limit: int | None = None, offset: int = 0) -> list[SessionMetadata]:
        """
        List all session metadata from database.

        Args:
            limit: Maximum number of results (None = all)
            offset: Number of results to skip

        Returns:
            List of metadata (most recently updated first)
        """
        with closing(self._connect()) as conn:
            sql = "SELECT * FROM session_metadata ORDER BY updated_at DESC"
            params: list[Any] = []

            if limit is not None:
                sql += " LIMIT ? OFFSET ?"
                params = [limit, offset]

            cursor = conn.execute(sql, params)
            return [self._deserialize_row(row) for row in cursor.fetchall()]

    def get_all_tags(self) -> list[str]:
        """
        Get all unique tags across all sessions.

        Returns:
            Sorted list of unique tags
        """
        all_tags = set()

        with closing(self._connect()) as conn:
            cursor = conn.execute("SELECT tags, auto_tags FROM session_metadata")
            for row in cursor.fetchall():
                all_tags.update(json.loads(row["tags"]))
                all_tags.update(json.loads(row["auto_tags"]))

        return sorted(all_tags)

    def count(self) -> int:
        """
        Count total sessions in database.

        Returns:
            Total session count
        """
        with closing(self._connect()) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM session_metadata")
            return cursor.fetchone()["count"]

    def get_stats(self) -> dict:
        """
        Get service statistics.

        Returns:
            Dictionary with stats
        """
        return {"total_sessions": self.count(), "total_tags": len(self.get_all_tags())}


# ============================================================================
# Singleton Instance
# ============================================================================

_metadata_db_instances: dict[Path, SessionMetadataDB] = {}


def get_metadata_db(db_path: Path | None = None) -> SessionMetadataDB:
    """
    Get singleton instance of SessionMetadataDB.

    Returns:
        Singleton database service instance
    """
    resolved_path = (db_path or SessionMetadataDB().db_path).resolve()
    if resolved_path not in _metadata_db_instances:
        _metadata_db_instances[resolved_path] = SessionMetadataDB(db_path=resolved_path)
    return _metadata_db_instances[resolved_path]
