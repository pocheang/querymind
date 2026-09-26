"""One-time initialisation: every schema migration, then the startup tasks that must run once.

    python -m app.init_app

The compose stack runs this as a one-shot `init` service that the backend and
the ingest-worker wait for (`deploy/compose/compose.yaml`), so no worker
process races another to create a table. There it also moves a single-worker
installation's data to where shared mode reads it (`migrate_legacy_data`). Every API process also
runs it from its lifespan, which is the backstop: once the databases are
current it amounts to one read per store, and a deployment that skipped the
init service still starts correctly.

Two kinds of work, deliberately handled differently:

- **Schema** goes through `app/services/runtime/sqlite_schema.py`: each store's
  pending migrations run in one `BEGIN IMMEDIATE` transaction, so any number of
  processes can call this at once and the database decides the order. A
  failure raises -- a server whose database cannot be brought up to date is a
  broken server, and the init service must exit non-zero so nothing starts on
  it.
- **Bootstrapping an administrator and clearing retired per-user model
  settings** are not single transactions, so they run under one cross-process
  file lock. Their failures are logged and do not stop startup, as before:
  an installation that cannot create an administrator still answers questions.

This replaced `deploy/scripts/init_app.py` as the thing that initialises a
database. That script imported a module that no longer existed, so the
deployment scripts' init step could not have run. It is a thin wrapper around
this now; `python -m app.init_app` is the form to use in a container.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings, get_settings
from app.services.runtime.file_locks import held
from app.services.runtime.sqlite_schema import Migration, ensure_schema

logger = logging.getLogger(__name__)

# The admin bootstrap waits for another process's at most this long.
_STARTUP_LOCK_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class SchemaTarget:
    component: str
    db_path: Path
    migrations: Sequence[Migration]
    wal: bool


def schema_targets(settings: Settings) -> list[SchemaTarget]:
    """Every SQLite store this deployment uses, in the order they are migrated.

    Authentication first: the connector and prompt tables reference `users`.
    """

    from app.agents.router.calibration import CALIBRATION_MIGRATIONS
    from app.mcp.approvals import APPROVAL_MIGRATIONS
    from app.services.auth.auth_service import AUTH_MIGRATIONS
    from app.services.connectors.metadata_repository import ConnectorMetadataRepository
    from app.services.connectors.repository import CredentialRepository
    from app.services.observability.stage_stats import STAGE_STATS_MIGRATIONS
    from app.services.prompts.store import PROMPT_MIGRATIONS
    from app.services.security.admin_token_tracker import ADMIN_TOKEN_MIGRATIONS
    from app.services.sessions.history import HISTORY_MIGRATIONS
    from app.services.sessions.metadata_db import SESSION_METADATA_MIGRATIONS, SessionMetadataDB
    from app.services.tables.store import TABLE_STORE_MIGRATIONS
    from app.wiki.store import WIKI_MIGRATIONS

    app_db = Path(settings.app_db_path)
    targets = [
        SchemaTarget("auth", app_db, AUTH_MIGRATIONS, True),
        SchemaTarget("tool_approvals", app_db, APPROVAL_MIGRATIONS, True),
        SchemaTarget("connector_metadata", app_db, ConnectorMetadataRepository.MIGRATIONS, True),
        SchemaTarget("connector_credentials", app_db, CredentialRepository.MIGRATIONS, True),
        SchemaTarget("admin_token_uses", app_db, ADMIN_TOKEN_MIGRATIONS, True),
        SchemaTarget("stage_stats", app_db, STAGE_STATS_MIGRATIONS, True),
        SchemaTarget("prompts", app_db, PROMPT_MIGRATIONS, True),
        SchemaTarget("structured_tables", app_db, TABLE_STORE_MIGRATIONS, True),
        SchemaTarget("router_calibration", app_db, CALIBRATION_MIGRATIONS, True),
        SchemaTarget("wiki", Path(settings.wiki_db_path).resolve(), WIKI_MIGRATIONS, False),
    ]
    if str(settings.history_backend).lower() == "sqlite":
        targets.append(SchemaTarget("history", Path(settings.history_sqlite_path), HISTORY_MIGRATIONS, True))
    if str(settings.session_metadata_backend).lower() == "database":
        targets.append(
            SchemaTarget(
                "session_metadata", SessionMetadataDB._get_db_path(settings), SESSION_METADATA_MIGRATIONS, True
            )
        )
    return targets


def migrate_all(settings: Settings | None = None) -> dict[str, int]:
    """Bring every store to its latest schema; return each component's version."""

    settings = settings or get_settings()
    versions: dict[str, int] = {}
    for target in schema_targets(settings):
        target.db_path.parent.mkdir(parents=True, exist_ok=True)
        versions[target.component] = ensure_schema(
            target.db_path,
            target.component,
            target.migrations,
            wal=target.wal,
            timeout_seconds=float(settings.sqlite_busy_timeout_seconds or 10),
        )
    return versions


def bootstrap_administrator() -> None:
    """Make sure a first run can open the admin console (`app/services/auth/bootstrap.py`)."""

    from app.services.auth.bootstrap import AdminBootstrapError, describe_bootstrap, ensure_admin_account

    try:
        created = ensure_admin_account()
    except AdminBootstrapError as exc:
        logger.exception("No administrator exists and one could not be created: %s", exc)
        return
    except Exception as exc:  # pragma: no cover - a broken database is its own problem
        logger.exception("Administrator bootstrap failed: %s", exc)
        return

    if created is not None:
        # stderr, not the logger: see `describe_bootstrap`.
        print(describe_bootstrap(created), file=sys.stderr, flush=True)


def purge_retired_user_model_settings() -> None:
    """Clear per-user model configurations left over from before 2026-09-08."""

    from app.services.models.config_store import purge_user_api_settings

    try:
        cleared = purge_user_api_settings()
    except Exception as exc:  # pragma: no cover - a broken database is its own problem
        logger.exception("Could not clear retired per-user model settings: %s", exc)
        return

    if cleared:
        logger.info("Cleared retired per-user model settings from %d account(s)", cleared)


def run(settings: Settings | None = None) -> dict[str, int]:
    """Migrate every store, then run the once-only tasks under one cross-process lock."""

    settings = settings or get_settings()
    versions = migrate_all(settings)
    lock_path = Path(settings.app_db_path).parent / ".startup.lock"
    with held(lock_path, timeout=_STARTUP_LOCK_TIMEOUT_SECONDS):
        bootstrap_administrator()
        purge_retired_user_model_settings()
    return versions


# Written next to the legacy data once it has been copied and verified, so a
# redeploy does not copy every vector again. Nothing writes the legacy stores in
# shared mode, so what was verified stays verified.
_SESSIONS_MARKER = ".migrated-to-sqlite"
_CHROMA_MARKER = ".migrated-to-chroma-server"
# One missing id per line; a failed copy of a whole collection would otherwise
# bury the first line of the log under thousands.
_PROBLEMS_SHOWN = 50


def migrate_legacy_data(settings: Settings | None = None) -> list[str]:
    """Move a single-worker installation's data to where shared mode reads it; return the problems.

    Shared state is the default topology since ARC-01 phase 9, so an existing
    deployment upgrades onto it with file-backed sessions and vectors in an
    embedded Chroma directory. Both copies are the existing migration tools --
    idempotent, never deleting the source, and read back to verify -- run here
    so an upgrade has no manual step. Only the init service calls this: it is a
    bulk copy, not something every worker should attempt at startup.
    """

    settings = settings or get_settings()
    if settings.state_backend != "shared":
        return []
    return [*_migrate_file_sessions(settings), *_migrate_embedded_vectors(settings)]


def _has_json(directory: Path) -> bool:
    return directory.is_dir() and any(directory.rglob("*.json"))


def _migrate_file_sessions(settings: Settings) -> list[str]:
    from app.services.sessions.history_migration import migrate_file_sessions

    root = Path(settings.sessions_path)
    cold = Path(settings.history_cold_path)
    marker = root / _SESSIONS_MARKER
    # The cold directory counts on its own: a user whose sessions were all moved
    # there has no hot files left, and the tool reads both.
    if marker.exists() or not (_has_json(root) or _has_json(cold)):
        return []
    report = migrate_file_sessions(root, cold, Path(settings.history_sqlite_path))
    print(f"sessions: {report.imported} imported, {report.already_present} already present, of {report.sessions}")
    problems = [f"unreadable session file {path}" for path in report.unreadable]
    problems += [f"session not found after import {key}" for key in report.missing_after]
    if not problems and not report.verified:
        accounted = report.imported + report.already_present
        problems.append(f"sessions: {accounted} accounted for of {report.sessions} found")
    if not problems:
        root.mkdir(parents=True, exist_ok=True)
        marker.write_text(f"{report.sessions} sessions verified in {settings.history_sqlite_path}\n", encoding="utf-8")
    return problems


def _migrate_embedded_vectors(settings: Settings) -> list[str]:
    source_dir = Path(settings.chroma_path)
    marker = source_dir / _CHROMA_MARKER
    server_url = str(settings.chroma_server_url or "").strip()
    if marker.exists() or not server_url or not (source_dir / "chroma.sqlite3").exists():
        return []

    import chromadb

    from app.retrievers.stores.chroma_migration import copy_collections
    from app.retrievers.stores.vector import chroma_http_client

    reports = copy_collections(chromadb.PersistentClient(path=str(source_dir)), chroma_http_client(server_url))
    problems = []
    for report in reports:
        print(f"vectors: {report.name} {report.copied}/{report.source_count}")
        problems += [
            f"vector {identifier} in {report.name} not found after copy" for identifier in report.missing_after
        ]
        if not report.missing_after and not report.verified:
            problems.append(f"vectors: {report.name} copied {report.copied} of {report.source_count}")
    if not problems:
        counts = ", ".join(f"{report.name}={report.copied}" for report in reports) or "no collections"
        marker.write_text(f"copied to {server_url}: {counts}\n", encoding="utf-8")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate every SQLite store and run the one-time startup tasks.")
    parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    versions = run()
    for component, version in versions.items():
        print(f"{component}: schema version {version}")
    problems = migrate_legacy_data()
    for problem in problems[:_PROBLEMS_SHOWN]:
        print(f"MIGRATION PROBLEM: {problem}", file=sys.stderr)
    if len(problems) > _PROBLEMS_SHOWN:
        print(f"MIGRATION PROBLEM: ... and {len(problems) - _PROBLEMS_SHOWN} more", file=sys.stderr)
    # Non-zero keeps the backend from starting on half-moved data (compose waits
    # for this service to complete successfully).
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
