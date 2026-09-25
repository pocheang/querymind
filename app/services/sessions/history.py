"""Per-user chat session history.

Two backends. `file` keeps one JSON document per session and is correct only
inside one process: its lock is a `threading.RLock`. `sqlite` keeps the same
document in one row, and since ARC-01 phase 4 every change is one
read-modify-write inside a single `BEGIN IMMEDIATE` transaction, so SQLite's
write lock serializes it across processes as well as threads. Before that the
read and the write were separate connections, and two workers appending to one
session each wrote back the list they had read -- one of the two messages was
lost, on either backend.

The process lock stays on the sqlite path as an optimization only: threads in
one process queue on it instead of on SQLite's busy handler.
"""

import json
import logging
import re
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.domain.text import normalize_string
from app.services.runtime.sqlite_schema import Migration, ensure_schema

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "新会话"

# BUG-11 (docs/querymind-deep-dive/issues.html): a new or reset session records
# `max_rounds: 10`, while the cap that actually applies is derived per intent by
# `max_rounds_for` (0-4). Kept as it was -- ARC-01 moves where sessions are
# stored and changes nothing about what they hold -- but stated once rather
# than four times, so the fix is one line.
_LEGACY_MAX_ROUNDS = 10


_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_LOCK_REGISTRY_GUARD = threading.Lock()
_LOCK_REGISTRY: dict[str, threading.RLock] = {}
_SESSION_FILE_GLOB = "*.json"

# A change: edit the session in place and return True to write it back, or
# False to abandon it -- nothing is written and the caller gets None.
Change = Callable[[dict[str, Any]], bool]


def _shared_lock_for_namespace(namespace: str) -> threading.RLock:
    with _LOCK_REGISTRY_GUARD:
        lock = _LOCK_REGISTRY.get(namespace)
        if lock is None:
            lock = threading.RLock()
            _LOCK_REGISTRY[namespace] = lock
        return lock


def validate_session_id(session_id: str) -> str:
    value = str(session_id or "").strip()
    if not _SESSION_ID_RE.fullmatch(value):
        raise ValueError("invalid session_id format")
    return value


def namespace_for(base_dir: Path) -> str:
    """The key a user's sessions are stored under in the sqlite backend.

    One definition, because the migration script has to write rows the store
    will find: a namespace spelled differently there imports every session into
    a key nothing reads, and the counts would still look right.
    """

    return str(base_dir.resolve())


def default_clarification_context() -> dict[str, Any]:
    return {
        "collected_info": {},
        "asked_questions": [],
        "clarification_round": 0,
        "max_rounds": _LEGACY_MAX_ROUNDS,
        "intent": "",
        "original_query": "",
    }


def _decode(raw: object, session_id: str) -> dict[str, Any] | None:
    try:
        data = json.loads(str(raw or ""))
    except ValueError as e:
        logger.warning(f"Failed to parse session data for {session_id}: {e}")
        return None
    return data if isinstance(data, dict) else None


def upsert_session_row(conn: sqlite3.Connection, namespace: str, session_id: str, data: dict[str, Any]) -> None:
    """Write one session row. UPDATE-then-INSERT rather than `ON CONFLICT`,
    because a table upgraded by the baseline migration's ALTER keeps its original
    primary key, which does not name `namespace`."""

    now = datetime.now(UTC).isoformat()
    payload = json.dumps(data, ensure_ascii=False)
    updated_at = str(data.get("updated_at") or now)
    updated = conn.execute(
        "UPDATE sessions SET data_json=?, updated_at=? WHERE namespace=? AND session_id=?",
        (payload, updated_at, namespace, session_id),
    )
    if int(updated.rowcount or 0) == 0:
        conn.execute(
            "INSERT INTO sessions(namespace, session_id, data_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?)",
            (namespace, session_id, payload, str(data.get("created_at") or now), updated_at),
        )


class _Unit:
    """One session read for update: `data` as found (None if absent), and `save`."""

    __slots__ = ("data", "save")

    def __init__(self, data: dict[str, Any] | None, save: Callable[[dict[str, Any]], None]) -> None:
        self.data = data
        self.save = save


class HistoryStore:
    def __init__(self, base_dir: Path | None = None):
        settings = get_settings()
        self._backend = str(getattr(settings, "history_backend", "file") or "file").strip().lower()
        if self._backend not in {"file", "sqlite"}:
            self._backend = "file"
        self.base_dir = base_dir or settings.sessions_path
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._cold_dir = settings.history_cold_path / self.base_dir.name
        self._cold_dir.mkdir(parents=True, exist_ok=True)
        self._hot_days = max(1, int(getattr(settings, "history_hot_tier_days", 14) or 14))
        self._db_path = settings.history_sqlite_path
        self._namespace = namespace_for(self.base_dir)
        self._lock = _shared_lock_for_namespace(self._namespace)
        self._last_tier_ts = 0.0
        if self._backend == "sqlite":
            self._init_sqlite()

    # ---- the one write path -----------------------------------------------------

    @contextmanager
    def _unit(self, session_id: str) -> Iterator[_Unit]:
        """Read one session and hold the right to write it until the block ends."""

        with self._lock:
            if self._backend != "sqlite":
                yield _Unit(self._read(session_id), lambda data: self._write_file(session_id, data))
                return
            # An exception from the block skips the COMMIT, and closing a
            # connection with a transaction open rolls it back.
            with closing(self._connect()) as conn:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT data_json FROM sessions WHERE namespace=? AND session_id=?",
                    (self._namespace, session_id),
                ).fetchone()
                data = _decode(row[0], session_id) if row else None
                yield _Unit(data, lambda new: upsert_session_row(conn, self._namespace, session_id, new))
                conn.execute("COMMIT")

    def _mutate(self, session_id: str, change: Change, *, create: bool = False) -> dict[str, Any] | None:
        """Apply `change` to one session as a single read-modify-write.

        Every change to an existing session goes through here, which is what
        makes it one transaction: the version `change` sees is the version it
        replaces, whichever worker wrote last.
        """

        try:
            session_id = validate_session_id(session_id)
        except ValueError:
            return None
        with self._unit(session_id) as unit:
            data = unit.data
            if data is None:
                if not create:
                    return None
                data = self._new_session(session_id)
            self._ensure_message_ids(data)
            if not change(data):
                return None
            unit.save(data)
            return data

    def _new_session(self, session_id: str, title: str | None = None) -> dict[str, Any]:
        now = self._now()
        return {
            "session_id": session_id,
            "title": title or DEFAULT_TITLE,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "runtime_policy": {"strategy_lock": None},
            "clarification_context": default_clarification_context(),
        }

    def _touch(self, data: dict[str, Any]) -> None:
        data["updated_at"] = self._now()

    # ---- sessions ---------------------------------------------------------------

    def create_session(self, title: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        session_id = validate_session_id(session_id) if session_id else uuid.uuid4().hex
        data = self._new_session(session_id, title)
        with self._unit(session_id) as unit:
            unit.save(data)
        return data

    def get_or_create_session(self, session_id: str | None = None) -> dict[str, Any]:
        if not session_id:
            return self.create_session()
        session_id = validate_session_id(session_id)
        existing = self.get_session(session_id)
        if existing is not None:
            return existing
        created = self._mutate(session_id, lambda _data: True, create=True)
        assert created is not None  # the id was validated above
        return created

    def list_sessions(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for data in self._iter_sessions_data():
            items.append(
                {
                    "session_id": data.get("session_id", ""),
                    "title": data.get("title", DEFAULT_TITLE),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "message_count": len(data.get("messages", [])),
                    "pinned": data.get("pinned", False),
                }
            )
        items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return items

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        try:
            session_id = validate_session_id(session_id)
        except ValueError:
            return None
        data = self._read(session_id)
        if data is None:
            return None
        if any(not msg.get("message_id") for msg in data.get("messages", [])):
            # A message stored before ids existed gets one, and it is persisted
            # so the id a client was shown still names the message next time.
            return self._mutate(session_id, lambda _data: True)
        return data

    def get_session_strategy_lock(self, session_id: str) -> str | None:
        data = self.get_session(session_id)
        if data is None:
            return None
        policy = data.get("runtime_policy", {}) or {}
        value = str(policy.get("strategy_lock", "") or "").strip().lower()
        return value or None

    def set_session_strategy_lock(self, session_id: str, strategy: str | None) -> dict[str, Any] | None:
        def change(data: dict[str, Any]) -> bool:
            policy = dict(data.get("runtime_policy", {}) or {})
            policy["strategy_lock"] = normalize_string(strategy, lowercase=True) or None
            data["runtime_policy"] = policy
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def update_session_title(self, session_id: str, title: str) -> dict[str, Any] | None:
        """Update session title."""

        def change(data: dict[str, Any]) -> bool:
            data["title"] = str(title).strip()[:200] or DEFAULT_TITLE
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def update_session_pinned(self, session_id: str, pinned: bool) -> dict[str, Any] | None:
        """Update session pinned status."""

        def change(data: dict[str, Any]) -> bool:
            data["pinned"] = bool(pinned)
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def delete_session(self, session_id: str) -> bool:
        try:
            session_id = validate_session_id(session_id)
        except ValueError:
            return False
        if self._backend == "sqlite":
            with self._lock, closing(self._connect()) as conn:
                cur = conn.execute(
                    "DELETE FROM sessions WHERE namespace=? AND session_id=?", (self._namespace, session_id)
                )
                conn.commit()
                return int(cur.rowcount or 0) > 0
        with self._lock:
            path = self.base_dir / f"{session_id}.json"
            if not path.exists():
                return False
            path.unlink()
            return True

    # ---- messages ---------------------------------------------------------------

    def append_message(
        self, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        session_id = validate_session_id(session_id)

        def change(data: dict[str, Any]) -> bool:
            if not data.get("messages") and role == "user":
                title = (content or DEFAULT_TITLE).strip().replace("\n", " ")[:40]
                data["title"] = title or data.get("title", DEFAULT_TITLE)
            data.setdefault("messages", []).append(
                {
                    "message_id": uuid.uuid4().hex,
                    "role": role,
                    "content": content,
                    "metadata": metadata or {},
                    "created_at": self._now(),
                }
            )
            self._touch(data)
            return True

        updated = self._mutate(session_id, change, create=True)
        assert updated is not None  # the id was validated above
        return updated

    def update_message(self, session_id: str, message_id: str, content: str) -> dict[str, Any] | None:
        def change(data: dict[str, Any]) -> bool:
            if self._update_message_in_data(data, message_id, content) is None:
                return False
            self._touch(data)
            self._refresh_title(data)
            return True

        return self._mutate(session_id, change)

    def get_message(self, session_id: str, message_id: str) -> dict[str, Any] | None:
        data = self.get_session(session_id)
        if data is None:
            return None
        for msg in data.get("messages", []):
            if msg.get("message_id") == message_id:
                return msg
        return None

    def upsert_assistant_after_user(
        self,
        session_id: str,
        user_message_id: str,
        assistant_content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        def change(data: dict[str, Any]) -> bool:
            messages = data.get("messages", [])
            idx = next((i for i, m in enumerate(messages) if m.get("message_id") == user_message_id), None)
            if idx is None or messages[idx].get("role") != "user":
                return False
            following = idx + 1
            if following < len(messages) and messages[following].get("role") == "assistant":
                messages[following]["content"] = assistant_content
                messages[following]["metadata"] = metadata or {}
                messages[following]["updated_at"] = self._now()
            else:
                messages.insert(
                    following,
                    {
                        "message_id": uuid.uuid4().hex,
                        "role": "assistant",
                        "content": assistant_content,
                        "metadata": metadata or {},
                        "created_at": self._now(),
                    },
                )
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def delete_message(self, session_id: str, message_id: str) -> dict[str, Any] | None:
        def change(data: dict[str, Any]) -> bool:
            messages = data.get("messages", [])
            kept = [m for m in messages if m.get("message_id") != message_id]
            if len(kept) == len(messages):
                return False
            data["messages"] = kept
            self._touch(data)
            self._refresh_title(data)
            return True

        return self._mutate(session_id, change)

    def _refresh_title(self, data: dict[str, Any]) -> None:
        for msg in data.get("messages", []):
            if msg.get("role") == "user":
                title = (msg.get("content") or DEFAULT_TITLE).strip().replace("\n", " ")[:40]
                data["title"] = title or DEFAULT_TITLE
                return
        data["title"] = DEFAULT_TITLE

    def _update_message_in_data(self, data: dict[str, Any], message_id: str, content: str) -> dict[str, Any] | None:
        for msg in data.get("messages", []):
            if msg.get("message_id") != message_id:
                continue
            msg["content"] = content
            msg["updated_at"] = self._now()
            return msg
        return None

    def _ensure_message_ids(self, data: dict[str, Any]) -> bool:
        changed = False
        for msg in data.get("messages", []):
            if not msg.get("message_id"):
                msg["message_id"] = uuid.uuid4().hex
                changed = True
        return changed

    # ---- storage ----------------------------------------------------------------

    def _write_file(self, session_id: str, data: dict[str, Any]) -> None:
        path = self.base_dir / f"{session_id}.json"
        temp_path = path.with_suffix(".json.tmp")
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        with self._lock:
            for attempt in range(3):
                try:
                    temp_path.write_text(payload, encoding="utf-8")
                    temp_path.replace(path)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.05 * (attempt + 1))
            self._tier_cold_files_if_needed()

    def _read(self, session_id: str) -> dict[str, Any] | None:
        """Read one session without taking the write lock -- for reads only."""

        try:
            session_id = validate_session_id(session_id)
        except ValueError:
            return None
        if self._backend == "sqlite":
            with closing(self._connect()) as conn:
                row = conn.execute(
                    "SELECT data_json FROM sessions WHERE namespace=? AND session_id=?",
                    (self._namespace, session_id),
                ).fetchone()
            return _decode(row[0], session_id) if row else None
        with self._lock:
            path = self.base_dir / f"{session_id}.json"
            if not path.exists():
                cold_path = self._cold_dir / f"{session_id}.json"
                if cold_path.exists():
                    path = cold_path
                else:
                    return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read session file {session_id}: {e}")
                return None
            return data if isinstance(data, dict) else None

    def _rows_from_sqlite(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            out = conn.execute(
                "SELECT data_json FROM sessions WHERE namespace=? ORDER BY updated_at DESC",
                (self._namespace,),
            ).fetchall()
        rows: list[dict[str, Any]] = []
        for row in out:
            try:
                data = json.loads(str(row[0] or ""))
            except ValueError as e:
                logger.debug(f"Skipping invalid session data: {e}")
                continue
            if isinstance(data, dict):
                rows.append(data)
        return rows

    def _rows_from_json_files(self, directory: Path, *, log_label: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted(directory.glob(_SESSION_FILE_GLOB), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.debug(f"Skipping invalid {log_label} {path}: {e}")
                continue
            if isinstance(data, dict):
                rows.append(data)
        return rows

    def _iter_sessions_data(self) -> list[dict[str, Any]]:
        if self._backend == "sqlite":
            return self._rows_from_sqlite()
        with self._lock:
            rows = self._rows_from_json_files(self.base_dir, log_label="session file")
            rows.extend(self._rows_from_json_files(self._cold_dir, log_label="cold session file"))
            return rows

    def _parse_updated_at(self, data: dict[str, Any]) -> datetime:
        """This session's last-touched time, normalized to UTC; now() if missing or unreadable."""
        updated = str(data.get("updated_at", "") or "")
        try:
            dt = datetime.fromisoformat(updated) if updated else datetime.now(UTC)
        except (ValueError, TypeError) as e:
            logger.debug(f"Invalid timestamp, using current time: {e}")
            dt = datetime.now(UTC)
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

    def _tier_one_file_if_stale(self, path: Path, cutoff: datetime) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.debug(f"Skipping invalid session file during archival {path}: {e}")
            return
        if self._parse_updated_at(data) >= cutoff:
            return
        target = self._cold_dir / path.name
        try:
            path.replace(target)
        except OSError as e:
            logger.debug(f"Failed to move session to cold storage {path}: {e}")

    def _tier_cold_files_if_needed(self) -> None:
        if self._backend != "file":
            return
        with self._lock:
            now_ts = datetime.now(UTC).timestamp()
            if (now_ts - self._last_tier_ts) < 300:
                return
            self._last_tier_ts = now_ts
            cutoff = datetime.now(UTC) - timedelta(days=self._hot_days)
            # Snapshot the generator with `tuple()` to avoid modifying the directory during iteration
            for path in tuple(self.base_dir.glob(_SESSION_FILE_GLOB)):
                self._tier_one_file_if_stale(path, cutoff)

    def _connect(self) -> sqlite3.Connection:
        return connect_history_db(self._db_path)

    def _init_sqlite(self) -> None:
        ensure_history_schema(self._db_path)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    # ---- clarification context --------------------------------------------------

    def set_clarification_context(
        self,
        session_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Persist a normalized clarification context without advancing its round."""

        normalized = {
            "collected_info": dict(context.get("collected_info", {}) or {}),
            "asked_questions": list(context.get("asked_questions", []) or []),
            "clarification_round": max(0, int(context.get("clarification_round", 0) or 0)),
            "max_rounds": max(0, int(context.get("max_rounds", 0) or 0)),
            "intent": str(context.get("intent", "") or ""),
            "original_query": str(context.get("original_query", "") or ""),
        }

        def change(data: dict[str, Any]) -> bool:
            data["clarification_context"] = normalized
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def update_clarification_context(
        self,
        session_id: str,
        field_name: str,
        value: str,
    ) -> dict[str, Any] | None:
        """Record the user's answer for one clarification field.

        Returns the updated session data, or None if the session does not exist.
        """

        def change(data: dict[str, Any]) -> bool:
            ctx = data.get("clarification_context", {})
            if not isinstance(ctx, dict):
                ctx = default_clarification_context()
            ctx.setdefault("collected_info", {})[field_name] = value
            if field_name not in ctx.get("asked_questions", []):
                ctx.setdefault("asked_questions", []).append(field_name)
            # The round is advanced by *asking*, in ClarificationAgentService, and
            # this used to advance it again on the answer. One counter, one owner:
            # incrementing here as well double-counted every completed exchange
            # and made the cap fire at half the configured number of questions.
            data["clarification_context"] = ctx
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def reset_clarification_context(self, session_id: str) -> dict[str, Any] | None:
        """Reset clarification context for a session (information is sufficient)."""

        def change(data: dict[str, Any]) -> bool:
            data["clarification_context"] = default_clarification_context()
            self._touch(data)
            return True

        return self._mutate(session_id, change)

    def get_clarification_context(self, session_id: str) -> dict[str, Any] | None:
        """Clarification context for a session, or None if the session does not exist."""

        data = self.get_session(session_id)
        if data is None:
            return None
        ctx = data.get("clarification_context")
        return ctx if isinstance(ctx, dict) else default_clarification_context()


def connect_history_db(db_path: Path) -> sqlite3.Connection:
    timeout_s = _busy_timeout_seconds()
    timeout_ms = int(timeout_s * 1000)

    conn = sqlite3.connect(db_path, timeout=timeout_s)

    # PRAGMA statements do not accept bind parameters.
    # timeout_ms is strictly clamped to an integer in [1000, 3600000] by _busy_timeout_seconds.
    assert isinstance(timeout_ms, int) and 1000 <= timeout_ms <= 3600000, "timeout_ms validation failed"
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")
    # WAL is set once, by the migration (ensure_history_schema).
    return conn


def _busy_timeout_seconds() -> float:
    try:
        timeout_s = float(getattr(get_settings(), "sqlite_busy_timeout_seconds", 10) or 10)
    except (ValueError, TypeError):
        return 10.0
    return max(1.0, min(timeout_s, 3600.0))


def _history_baseline(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions(
            namespace TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(namespace, session_id)
        )
        """
    )
    cols = [str(r[1]) for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if "namespace" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN namespace TEXT NOT NULL DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_ns_updated_at ON sessions(namespace, updated_at)")


HISTORY_MIGRATIONS = (Migration(1, "baseline: sessions keyed by namespace and session id", _history_baseline),)


def ensure_history_schema(db_path: Path) -> int:
    """Create or upgrade the session-history tables; safe from any number of processes at once."""

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return ensure_schema(db_path, "history", HISTORY_MIGRATIONS, wal=True, timeout_seconds=_busy_timeout_seconds())
