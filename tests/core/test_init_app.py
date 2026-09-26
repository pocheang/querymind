"""One-time initialisation, and the startup race it closes (ARC-01 phase 7).

Two workers starting together crashed on `database is locked` (WAL switched on
every connection) or `duplicate column name` (both adding the same column).
`app/init_app.py` migrates every store and runs the once-only tasks; the
shared-state deployment runs it as an `init` service before any worker, and
every API process runs it again as a backstop.

The guards here are what keep that true as stores are added: a store the init
does not know about is migrated by whichever worker constructs it first, which
is the race again.
"""

from __future__ import annotations

import ast
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.core.config import Settings
from app.init_app import migrate_all, schema_targets
from app.services.runtime.sqlite_schema import schema_version

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"

# Modules that create tables without going through a migration, and why.
UNMIGRATED_TABLES = {
    # One file per user, its own `user_version` import marker and a rollback
    # journal (see its docstring); created when the user's store first opens.
    "app/services/sessions/memory_store.py",
    # An in-memory SQLite engine rebuilt from stored rows, never a file.
    "app/services/tables/engine.py",
    # Repairs Chroma's own database, which this application does not own.
    "app/retrievers/stores/vector.py",
}


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        _env_file=None,
        APP_DB_PATH=str(tmp_path / "app.db"),
        WIKI_DB_PATH=str(tmp_path / "wiki" / "wiki.db"),
        HISTORY_BACKEND="sqlite",
        HISTORY_SQLITE_PATH=str(tmp_path / "history.db"),
        SESSION_METADATA_BACKEND="database",
        DATABASE_URL=f"sqlite:///{(tmp_path / 'querymind.db').as_posix()}",
    )
    # Every target must be inside tmp_path. The first version of this helper let
    # session metadata resolve through the process's settings, so a test run
    # migrated the developer's data/querymind.db -- asserted here, not assumed.
    for target in schema_targets(settings):
        assert target.db_path.resolve().is_relative_to(tmp_path.resolve()), target
    return settings


def _python_files() -> list[Path]:
    return sorted(path for path in APP.rglob("*.py") if "__pycache__" not in path.parts)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _components_in_source() -> set[str]:
    components: set[str] = set()
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "ensure_schema"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
            ):
                components.add(node.args[1].value)
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "SCHEMA_COMPONENT" for t in node.targets
            ):
                if isinstance(node.value, ast.Constant) and node.value.value:
                    components.add(node.value.value)
    return components


def test_the_init_migrates_every_store_the_application_has(tmp_path):
    in_source = _components_in_source()
    in_init = {target.component for target in schema_targets(_settings(tmp_path))}

    assert in_source, "the scan found no stores -- it has stopped matching"
    assert in_source == in_init


def test_only_the_migration_module_switches_a_database_to_wal():
    offenders = [
        _relative(path)
        for path in _python_files()
        if "journal_mode=wal" in path.read_text(encoding="utf-8").lower().replace(" ", "")
        and path.name != "sqlite_schema.py"
    ]

    assert offenders == []


def test_every_module_that_creates_a_table_does_it_through_a_migration():
    offenders = [
        _relative(path)
        for path in _python_files()
        if "CREATE TABLE" in (text := path.read_text(encoding="utf-8"))
        and "ensure_schema" not in text
        and "Migration(" not in text
        and _relative(path) not in UNMIGRATED_TABLES
        and path.name != "sqlite_schema.py"
    ]

    assert offenders == []


def test_the_allowlist_names_only_files_that_still_create_tables():
    for rel in UNMIGRATED_TABLES:
        assert "CREATE TABLE" in (ROOT / rel).read_text(encoding="utf-8"), f"{rel} no longer needs an entry"


def test_a_fresh_deployment_is_brought_to_every_latest_version(tmp_path):
    settings = _settings(tmp_path)

    versions = migrate_all(settings)

    for target in schema_targets(settings):
        assert versions[target.component] == len(target.migrations)
        assert schema_version(target.db_path, target.component) == len(target.migrations)


def test_a_second_run_takes_no_write_lock(tmp_path):
    settings = _settings(tmp_path)
    migrate_all(settings)
    holder = sqlite3.connect(tmp_path / "app.db", isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        started = time.perf_counter()
        migrate_all(settings)
        elapsed = time.perf_counter() - started
    finally:
        holder.execute("ROLLBACK")
        holder.close()

    assert elapsed < 1.0, f"took {elapsed:.2f}s -- a current database should need only reads"


def test_a_database_from_before_migrations_keeps_its_rows(tmp_path):
    """Migration 1 is each store's old setup, so an existing app.db upgrades in place."""

    db = tmp_path / "app.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE users (user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, "
            "salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO users VALUES ('u1', 'alice', 's', 'h', '2026-01-01T00:00:00+00:00')")

    migrate_all(_settings(tmp_path))

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT username, role, credit_balance FROM users").fetchall()[0][0] == "alice"


def test_the_administrator_is_bootstrapped_while_the_startup_lock_is_held(tmp_path, monkeypatch):
    """Two processes both finding no administrator would both try to create one."""

    import threading

    from filelock import FileLock

    from app import init_app

    settings = _settings(tmp_path)
    observed: list[bool] = []

    def lock_is_taken_elsewhere() -> bool:
        # Asked from another thread with its own FileLock: the lock is held by
        # this process's run(), so the attempt must fail.
        result: list[bool] = []

        def attempt() -> None:
            other = FileLock(str(tmp_path / ".startup.lock"), thread_local=True)
            try:
                other.acquire(timeout=0)
            except Exception:
                result.append(True)
            else:
                other.release()
                result.append(False)

        worker = threading.Thread(target=attempt)
        worker.start()
        worker.join()
        return result[0]

    monkeypatch.setattr(init_app, "bootstrap_administrator", lambda: observed.append(lock_is_taken_elsewhere()))
    monkeypatch.setattr(init_app, "purge_retired_user_model_settings", lambda: None)

    init_app.run(settings)

    assert observed == [True]


def _child_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    env.update(
        RUNTIME_ENV_FILE=str(empty),
        NACOS_ENABLED="false",
        APP_DB_PATH=str(tmp_path / "app.db"),
        WIKI_DB_PATH=str(tmp_path / "wiki" / "wiki.db"),
        HISTORY_BACKEND="sqlite",
        HISTORY_SQLITE_PATH=str(tmp_path / "history.db"),
        DATABASE_URL=f"sqlite:///{(tmp_path / 'querymind.db').as_posix()}",
        PYTHONPATH=str(ROOT),
        PYTHONUTF8="1",
    )
    env.update(extra)
    return env


def test_importing_the_auth_dependency_does_not_open_the_database(tmp_path):
    """ARC-09: importing a module must not write a database."""

    result = subprocess.run(
        [sys.executable, "-c", "import app.api.deps.auth, app.api.utils.auth_helpers"],
        cwd=ROOT,
        env=_child_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr[-2000:]
    assert not (tmp_path / "app.db").exists()


@pytest.mark.timeout(300)
def test_three_inits_started_together_all_succeed_and_create_one_administrator(tmp_path):
    env = _child_env(tmp_path, ADMIN_USERNAME="initadmin", ADMIN_PASSWORD="Init-Race-Passw0rd-2026")
    runs = [
        subprocess.Popen(
            [sys.executable, "-m", "app.init_app"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(3)
    ]
    outputs = [run.communicate(timeout=240) for run in runs]

    assert [run.returncode for run in runs] == [0, 0, 0], [err[-2000:] for _, err in outputs]
    assert all("auth: schema version 1" in out for out, _ in outputs)
    with sqlite3.connect(tmp_path / "app.db") as conn:
        admins = conn.execute("SELECT username FROM users WHERE role='admin'").fetchall()
    assert admins == [("initadmin",)]
