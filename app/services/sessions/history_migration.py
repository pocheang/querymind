"""Copy file-backend session history into the sqlite backend (ARC-01 phase 4).

`STATE_BACKEND=shared` refuses `HISTORY_BACKEND=file`, because the file
backend's lock is a `threading.RLock` and cannot serialize two workers. An
installation switching over keeps its sessions only if they are copied first;
this is that copy.

Three properties, each the answer to a way a migration usually goes wrong:

- **It never deletes a file.** The JSON files stay where they are, so the
  switch can be undone by setting `HISTORY_BACKEND=file` again.
- **It never overwrites a row.** A session already present in sqlite may have
  been written by the running application after the switch, and is newer than
  the file it came from. So a second run imports only what is missing, which
  is what makes it safe to repeat.
- **It verifies by reading back**, not by counting its own inserts: a session
  counts as migrated when a row for it exists under the namespace
  `HistoryStore` will look it up by. A namespace spelled differently would
  import every session into a key nothing reads, and a count of inserts would
  still look perfect.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.services.sessions.history import (
    connect_history_db,
    ensure_history_schema,
    namespace_for,
    upsert_session_row,
    validate_session_id,
)

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    namespaces: int = 0
    sessions: int = 0
    imported: int = 0
    already_present: int = 0
    unreadable: list[str] = field(default_factory=list)
    missing_after: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return not self.missing_after and self.imported + self.already_present == self.sessions


def _session_bases(sessions_root: Path, cold_root: Path) -> list[Path]:
    """Every `base_dir` a `HistoryStore` may have been built with.

    The root itself (a store built with no `base_dir`) and one directory per
    user. A user may have only cold files left, so the cold root's directory
    names count too.
    """

    names = {p.name for p in sessions_root.iterdir() if p.is_dir()} if sessions_root.is_dir() else set()
    if cold_root.is_dir():
        # The root's own cold files live at cold_root/<root name>; that is not a user.
        names |= {p.name for p in cold_root.iterdir() if p.is_dir() and p.name != sessions_root.name}
    return [sessions_root, *(sessions_root / name for name in sorted(names))]


def _session_files(base: Path, cold_root: Path, report: MigrationReport) -> dict[str, dict[str, Any]]:
    """Sessions under one base, by id. Hot wins over cold: cold files are the older copies."""

    found: dict[str, dict[str, Any]] = {}
    for directory in (cold_root / base.name, base):
        for path in sorted(directory.glob("*.json")) if directory.is_dir() else ():
            data = _load(path, report)
            if data is not None:
                found[path.stem] = data
    return found


def _load(path: Path, report: MigrationReport) -> dict[str, Any] | None:
    try:
        session_id = validate_session_id(path.stem)
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        logger.warning("session_migration_unreadable path=%s error=%s", path, e)
        report.unreadable.append(str(path))
        return None
    if not isinstance(data, dict):
        report.unreadable.append(str(path))
        return None
    data.setdefault("session_id", session_id)
    return data


def _present(conn, namespace: str, session_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM sessions WHERE namespace=? AND session_id=?", (namespace, session_id)).fetchone()
    return row is not None


def _import_base(conn, namespace: str, sessions: dict[str, dict[str, Any]], report: MigrationReport) -> None:
    # One transaction per user. A failure propagates out of
    # `migrate_file_sessions`, whose `closing()` rolls the open one back.
    conn.execute("BEGIN IMMEDIATE")
    for session_id, data in sessions.items():
        if _present(conn, namespace, session_id):
            report.already_present += 1
        else:
            upsert_session_row(conn, namespace, session_id, data)
            report.imported += 1
    conn.execute("COMMIT")


def _bases_with_sessions(sessions_root: Path, cold_root: Path, report: MigrationReport) -> Iterator[tuple[str, dict]]:
    for base in _session_bases(sessions_root, cold_root):
        sessions = _session_files(base, cold_root, report)
        if sessions:
            yield namespace_for(base), sessions


def migrate_file_sessions(
    sessions_root: Path, cold_root: Path, db_path: Path, *, dry_run: bool = False
) -> MigrationReport:
    report = MigrationReport()
    with closing(connect_history_db(db_path)) as conn:
        ensure_history_schema(conn)
        conn.isolation_level = None
        for namespace, sessions in _bases_with_sessions(sessions_root, cold_root, report):
            report.namespaces += 1
            report.sessions += len(sessions)
            if dry_run:
                report.already_present += sum(_present(conn, namespace, sid) for sid in sessions)
                continue
            _import_base(conn, namespace, sessions, report)
            report.missing_after.extend(f"{namespace}::{sid}" for sid in sessions if not _present(conn, namespace, sid))
    return report
