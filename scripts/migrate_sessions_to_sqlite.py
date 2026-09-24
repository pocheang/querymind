#!/usr/bin/env python
"""Copy file-backend session history into the sqlite backend.

    conda run -n rag-local python scripts/migrate_sessions_to_sqlite.py --dry-run
    conda run -n rag-local python scripts/migrate_sessions_to_sqlite.py

Run it before setting `HISTORY_BACKEND=sqlite` (which `STATE_BACKEND=shared`
requires, ARC-01 phase 4). It reads `SESSIONS_DIR`, `HISTORY_COLD_DIR` and
`HISTORY_SQLITE_PATH` from the same configuration the server uses.

Safe to repeat: files are never deleted and an existing row is never
overwritten. Exit 0 only when every session read from disk is readable back
from sqlite under the key the server will look it up by; unreadable files are
listed and make the exit 1, because a session left behind silently is the
failure this exists to prevent. See `app/services/sessions/history_migration.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report what would be imported, write nothing")
    args = parser.parse_args(argv)

    from app.core.config import get_settings
    from app.services.sessions.history_migration import migrate_file_sessions

    settings = get_settings()
    report = migrate_file_sessions(
        settings.sessions_path, settings.history_cold_path, settings.history_sqlite_path, dry_run=args.dry_run
    )
    print(f"namespaces:       {report.namespaces}")
    print(f"sessions on disk: {report.sessions}")
    print(f"already in sqlite:{report.already_present:>5}")
    if args.dry_run:
        print(f"would import:     {report.sessions - report.already_present}")
    else:
        print(f"imported:         {report.imported}")
    for path in report.unreadable:
        print(f"UNREADABLE  {path}")
    for key in report.missing_after:
        print(f"NOT FOUND AFTER IMPORT  {key}")
    if report.unreadable or (not args.dry_run and not report.verified):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
