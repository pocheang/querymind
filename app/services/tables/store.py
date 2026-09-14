"""Owner-scoped TableStore: parsed tables, persisted, and the SQL run against them."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
from collections import OrderedDict
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.retrievers.stores.vector import SHARED_CORPUS_TENANT
from app.services.multimodal.models import TableContent
from app.services.tables.engine import TableEngine, TableQueryResult, TableSchema

logger = logging.getLogger(__name__)

# In-memory engines kept warm. The rows themselves live in SQLite, so an evicted
# engine is rebuilt on its next read rather than lost.
_MAX_CACHED_ENGINES = 64
# SQLite's default bound on host parameters in one statement.
_SQLITE_MAX_PARAMS = 900


@dataclass(frozen=True)
class _Record:
    """Who may read a table, and which version of it this is."""

    table_id: str
    tenant_id: str
    owner_user_id: str
    visibility: str
    source: str
    updated_at: int


@dataclass(frozen=True)
class _Loaded:
    record: _Record
    content: TableContent
    engine: TableEngine
    schema: TableSchema


def _may_read(record: _Record, user_id: str) -> bool:
    """The vector store's `_owner_clause`, for tables: owner, public, or shared corpus."""
    return record.owner_user_id == user_id or record.visibility == "public" or record.tenant_id == SHARED_CORPUS_TENANT


class _MemoryBackend:
    """Rows held in this process only. What tests use, and nothing else."""

    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], tuple[_Record, TableContent]] = {}
        self._lock = threading.Lock()

    def put(self, record: _Record, content: TableContent) -> None:
        with self._lock:
            self._rows[(record.table_id, record.tenant_id)] = (record, content)

    def records(self, table_id: str) -> list[_Record]:
        with self._lock:
            return [record for (tid, _), (record, _) in self._rows.items() if tid == table_id]

    def all_records(self) -> list[_Record]:
        with self._lock:
            return [record for record, _ in self._rows.values()]

    def content(self, record: _Record) -> TableContent | None:
        with self._lock:
            entry = self._rows.get((record.table_id, record.tenant_id))
        if entry is None or entry[0].updated_at != record.updated_at:
            return None
        return entry[1]

    def delete_sources(self, sources: set[str]) -> int:
        with self._lock:
            doomed = [key for key, (record, _) in self._rows.items() if record.source in sources]
            for key in doomed:
                del self._rows[key]
        return len(doomed)


class _SqliteBackend:
    """Rows in the application database, so a table outlives the process that
    ingested it and every worker reads the same one.

    Follows the store pattern the rest of the app uses -- own connection per
    call, schema created on construction -- and closes each connection rather
    than leaving it to the garbage collector.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS structured_tables (
                  table_id TEXT NOT NULL,
                  tenant_id TEXT NOT NULL,
                  owner_user_id TEXT NOT NULL,
                  visibility TEXT NOT NULL,
                  source TEXT NOT NULL,
                  updated_at INTEGER NOT NULL,
                  content_json TEXT NOT NULL,
                  PRIMARY KEY (table_id, tenant_id)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS structured_tables_source ON structured_tables (source)")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def put(self, record: _Record, content: TableContent) -> None:
        payload = {
            "doc_id": content.doc_id,
            "page_number": content.page_number,
            "headers": content.headers,
            "rows": content.rows,
            "summary": content.summary,
            "metadata": content.metadata,
        }
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO structured_tables
                  (table_id, tenant_id, owner_user_id, visibility, source, updated_at, content_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (table_id, tenant_id) DO UPDATE SET
                  owner_user_id = excluded.owner_user_id,
                  visibility = excluded.visibility,
                  source = excluded.source,
                  updated_at = excluded.updated_at,
                  content_json = excluded.content_json
                """,
                (
                    record.table_id,
                    record.tenant_id,
                    record.owner_user_id,
                    record.visibility,
                    record.source,
                    record.updated_at,
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )

    def records(self, table_id: str) -> list[_Record]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT table_id, tenant_id, owner_user_id, visibility, source, updated_at "
                "FROM structured_tables WHERE table_id = ?",
                (table_id,),
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def all_records(self) -> list[_Record]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT table_id, tenant_id, owner_user_id, visibility, source, updated_at FROM structured_tables"
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def content(self, record: _Record) -> TableContent | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT content_json FROM structured_tables WHERE table_id = ? AND tenant_id = ? AND updated_at = ?",
                (record.table_id, record.tenant_id, record.updated_at),
            ).fetchone()
        if row is None:
            return None
        payload: dict[str, Any] = json.loads(row["content_json"])
        return TableContent(
            table_id=record.table_id,
            doc_id=str(payload.get("doc_id", "")),
            page_number=int(payload.get("page_number") or 0),
            headers=list(payload.get("headers") or []),
            rows=[list(r) for r in payload.get("rows") or []],
            summary=str(payload.get("summary", "")),
            metadata=dict(payload.get("metadata") or {}),
        )

    def delete_sources(self, sources: set[str]) -> int:
        ordered = sorted(sources)
        removed = 0
        with self._connection() as conn:
            for start in range(0, len(ordered), _SQLITE_MAX_PARAMS):
                batch = ordered[start : start + _SQLITE_MAX_PARAMS]
                placeholders = ", ".join("?" for _ in batch)
                removed += conn.execute(
                    f"DELETE FROM structured_tables WHERE source IN ({placeholders})",  # noqa: S608 - placeholders only
                    batch,
                ).rowcount
        return removed


def _record_from_row(row: sqlite3.Row) -> _Record:
    return _Record(
        table_id=row["table_id"],
        tenant_id=row["tenant_id"],
        owner_user_id=row["owner_user_id"],
        visibility=row["visibility"],
        source=row["source"],
        updated_at=int(row["updated_at"]),
    )


class TableStore:
    """Structured tables for SQL analytics, readable only by who may read the document.

    Three properties carry it:

    - **Every table has its own in-memory engine.** A statement against one table
      cannot name another. A shared per-tenant engine let `SELECT * FROM a, b`
      read a colleague's table through a table the caller could legitimately see.
    - **Every read takes the reader's `user_id`**, keyword-only with no default,
      and applies the vector store's owner rule (`_owner_clause`): the owner, a
      public document, or the shared corpus. A table the reader may not see
      answers "not found", the same as one that does not exist -- distinguishing
      them would disclose that someone else holds it.
    - **Ownership is read from the backend on every call, never from the engine
      cache.** With `db_path` set the rows live in SQLite, so a table survives a
      restart and every worker reads the same one; a table deleted or re-ingested
      by another worker is seen as such on the next read here, because the cached
      engine is only used when its version matches the stored one.

    With no `db_path` the rows stay in this process -- what tests use.
    """

    def __init__(
        self,
        prefer_duckdb: bool = True,
        db_path: Path | None = None,
        *,
        max_cached_engines: int = _MAX_CACHED_ENGINES,
    ) -> None:
        self.prefer_duckdb = prefer_duckdb
        self._backend: _MemoryBackend | _SqliteBackend = (
            _SqliteBackend(db_path) if db_path is not None else _MemoryBackend()
        )
        self._engines: OrderedDict[tuple[str, str], _Loaded] = OrderedDict()
        self._max_cached = max(1, int(max_cached_engines))
        self._lock = threading.Lock()

    @property
    def persistent(self) -> bool:
        return isinstance(self._backend, _SqliteBackend)

    def save_table(
        self,
        tenant_id: str,
        table: TableContent,
        *,
        owner_user_id: str,
        visibility: str = "private",
        source: str = "",
    ) -> TableSchema:
        """Register a table, recording who may read it."""
        record = _Record(
            table_id=table.table_id,
            tenant_id=tenant_id or SHARED_CORPUS_TENANT,
            owner_user_id=str(owner_user_id or ""),
            visibility=str(visibility or "private"),
            source=str(source or ""),
            updated_at=time.time_ns(),
        )
        # Built before it is stored, so a table the engine cannot register is
        # never persisted for every later read to fail on.
        loaded = self._build(record, table)
        self._backend.put(record, table)
        self._remember(loaded)
        logger.info(f"Saved table '{table.table_id}' ({loaded.schema.table_name}) with {len(table.rows)} rows")
        return loaded.schema

    def _build(self, record: _Record, content: TableContent) -> _Loaded:
        engine = TableEngine(prefer_duckdb=self.prefer_duckdb)
        schema = engine.register_table(table_id=content.table_id, headers=content.headers, rows=content.rows)
        return _Loaded(record=record, content=content, engine=engine, schema=schema)

    def _remember(self, loaded: _Loaded) -> None:
        key = (loaded.record.table_id, loaded.record.tenant_id)
        with self._lock:
            self._engines[key] = loaded
            self._engines.move_to_end(key)
            while len(self._engines) > self._max_cached:
                self._engines.popitem(last=False)

    def _load(self, record: _Record) -> _Loaded | None:
        key = (record.table_id, record.tenant_id)
        with self._lock:
            cached = self._engines.get(key)
            if cached is not None and cached.record.updated_at == record.updated_at:
                self._engines.move_to_end(key)
                return cached
        content = self._backend.content(record)
        if content is None:
            # Replaced or deleted between the two reads; the next call sees the new state.
            return None
        loaded = self._build(record, content)
        self._remember(loaded)
        return loaded

    def _readable(self, tenant_id: str, table_id: str, user_id: str | None) -> _Loaded | None:
        if not user_id:
            return None
        preferred = tenant_id or SHARED_CORPUS_TENANT
        records = sorted(self._backend.records(table_id), key=lambda record: record.tenant_id != preferred)
        for record in records:
            if _may_read(record, user_id):
                return self._load(record)
        return None

    def get_table(self, tenant_id: str, table_id: str, *, user_id: str | None) -> TableContent | None:
        loaded = self._readable(tenant_id, table_id, user_id)
        return loaded.content if loaded else None

    def get_schema(self, tenant_id: str, table_id: str, *, user_id: str | None) -> TableSchema | None:
        loaded = self._readable(tenant_id, table_id, user_id)
        return loaded.schema if loaded else None

    def list_tables(self, tenant_id: str, *, user_id: str | None, doc_id: str | None = None) -> list[TableContent]:
        results: list[TableContent] = []
        for table_id in sorted({record.table_id for record in self._backend.all_records()}):
            loaded = self._readable(tenant_id, table_id, user_id)
            if loaded and (doc_id is None or loaded.content.doc_id == doc_id):
                results.append(loaded.content)
        return results

    def delete_by_sources(self, sources: Iterable[str]) -> int:
        """Forget every table ingested from one of `sources`; returns how many."""
        wanted = {str(source) for source in sources if source}
        if not wanted:
            return 0
        removed = self._backend.delete_sources(wanted)
        with self._lock:
            for key in [key for key, loaded in self._engines.items() if loaded.record.source in wanted]:
                del self._engines[key]
        return removed

    def query_table(
        self,
        tenant_id: str,
        table_id: str,
        sql: str,
        *,
        user_id: str | None,
        max_rows: int = 100,
    ) -> TableQueryResult:
        """Execute a SQL query on one table the reader may see."""
        loaded = self._readable(tenant_id, table_id, user_id)
        if loaded is None:
            return TableQueryResult(
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=0.0,
                markdown_table="",
                engine_used="none",
                error=f"Table '{table_id}' not found",
            )
        schema = loaded.schema

        # A statement names its table by id or by a placeholder ("FROM table");
        # either becomes the engine's safe name. Only the table position after
        # FROM / JOIN is rewritten: matching the id anywhere turned a column that
        # shares the table's name (`SUM(sales)` on table "sales") into the table.
        # The engine holds this one table, so no other name could resolve anyway.
        adjusted_sql = sql
        if schema.table_name not in adjusted_sql:
            adjusted_sql = re.sub(
                rf"\b(FROM|JOIN)\s+(?:{re.escape(table_id)}|[a-zA-Z0-9_\-]+)\b",
                lambda match: f'{match.group(1)} "{schema.table_name}"',
                adjusted_sql,
                flags=re.IGNORECASE,
            )

        return loaded.engine.execute_query(adjusted_sql, max_rows=max_rows)


_GLOBAL_TABLE_STORE: TableStore | None = None
_GLOBAL_LOCK = threading.Lock()


def _default_db_path() -> Path | None:
    """`APP_DB_PATH`, or no persistence at all while pytest is running.

    A test run must not write into the developer's `data/app.db` -- the rule the
    administrator bootstrap and the API-settings purge already follow in the
    lifespan. Tests that exercise persistence construct `TableStore(db_path=...)`
    against a temporary file instead.
    """
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    from app.core.config import get_settings

    return get_settings().app_db_path


def get_table_store() -> TableStore:
    """Get or initialize the process-wide TableStore."""
    global _GLOBAL_TABLE_STORE
    if _GLOBAL_TABLE_STORE is None:
        with _GLOBAL_LOCK:
            if _GLOBAL_TABLE_STORE is None:
                _GLOBAL_TABLE_STORE = TableStore(db_path=_default_db_path())
    return _GLOBAL_TABLE_STORE
