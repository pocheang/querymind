"""Two workers writing one session must not lose each other's messages (ARC-01 phase 4).

The sqlite backend used to read a session on one connection and write it back
on another, with only a `threading.RLock` between them. SQLite serialized the
two *writes*, never the read-modify-write, so a second process appending to
the same session wrote back the list it had read and dropped the other
worker's message. Every change is now one `BEGIN IMMEDIATE` transaction.

The first test is the deterministic one: a raw connection plays the other
worker, holds the write lock mid-change, and the store must wait for it rather
than read around it. The second is the plan's acceptance check, two real
processes and a hundred appends. The rest pin the startup rule that keeps the
file backend out of shared mode, and the migration that makes switching
possible without losing the sessions kept in files.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from app.core.config import Settings, get_settings, validate_shared_state_backends
from app.services.sessions.history import HistoryStore, namespace_for
from app.services.sessions.history_migration import migrate_file_sessions

REPO_ROOT = Path(__file__).resolve().parents[2]
_HOLD_SECONDS = 0.5


@pytest.fixture
def paths(tmp_path, monkeypatch):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    values = {
        "RUNTIME_ENV_FILE": str(empty_env),
        "NACOS_ENABLED": "false",
        "API_SETTINGS_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef0123456789abcdef",
        "HISTORY_BACKEND": "sqlite",
        "HISTORY_SQLITE_PATH": str(tmp_path / "history.db"),
        "SESSIONS_DIR": str(tmp_path / "sessions"),
        "HISTORY_COLD_DIR": str(tmp_path / "cold"),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _messages(store: HistoryStore, session_id: str) -> list[str]:
    data = store.get_session(session_id)
    assert data is not None
    return [m["content"] for m in data["messages"]]


# ---- the lost update ------------------------------------------------------------------


def test_an_append_waits_for_a_write_already_in_progress_and_keeps_it(paths):
    store = HistoryStore(base_dir=paths / "sessions" / "alice")
    store.append_message("s1", "user", "first")

    other = sqlite3.connect(paths / "history.db", isolation_level=None, check_same_thread=False)
    other.execute("BEGIN IMMEDIATE")
    raw = other.execute("SELECT data_json FROM sessions WHERE session_id='s1'").fetchone()[0]
    data = json.loads(raw)
    data["messages"].append({"message_id": "other", "role": "assistant", "content": "from the other worker"})
    other.execute("UPDATE sessions SET data_json=? WHERE session_id='s1'", (json.dumps(data),))

    def commit() -> None:
        other.execute("COMMIT")
        other.close()

    timer = threading.Timer(_HOLD_SECONDS, commit)
    timer.start()
    try:
        store.append_message("s1", "user", "second")
    finally:
        timer.join()

    assert _messages(store, "s1") == ["first", "from the other worker", "second"]


def test_two_processes_appending_to_one_session_lose_nothing(paths):
    """The plan's acceptance check: two workers, 100 appends, 100 messages."""

    per_worker = 50
    go = paths / "go"
    child = (
        "import sys, time\n"
        "from pathlib import Path\n"
        "from app.services.sessions.history import HistoryStore\n"
        "go = Path(sys.argv[1])\n"
        "store = HistoryStore(base_dir=Path(sys.argv[2]))\n"
        "while not go.exists():\n"
        "    time.sleep(0.01)\n"
        f"for i in range({per_worker}):\n"
        "    store.append_message('shared', 'user', f'{sys.argv[3]}-{i}')\n"
    )
    base = paths / "sessions" / "alice"
    HistoryStore(base_dir=base).create_session(session_id="shared")
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    workers = [
        subprocess.Popen([sys.executable, "-c", child, str(go), str(base), name], cwd=REPO_ROOT, env=env)
        for name in ("a", "b")
    ]
    time.sleep(3.0)  # both past their imports and spinning on the go file
    go.touch()
    for worker in workers:
        assert worker.wait(timeout=120) == 0

    contents = _messages(HistoryStore(base_dir=base), "shared")
    assert len(contents) == 2 * per_worker
    assert sorted(contents) == sorted(f"{w}-{i}" for w in ("a", "b") for i in range(per_worker))


def test_a_change_that_raises_after_writing_is_rolled_back_and_releases_the_lock(paths):
    store = HistoryStore(base_dir=paths / "sessions" / "alice")
    store.append_message("s1", "user", "kept")

    with pytest.raises(RuntimeError), store._unit("s1") as unit:
        unit.save({**unit.data, "messages": []})
        raise RuntimeError("boom")

    store.append_message("s1", "user", "after")  # would wait out the busy timeout if the lock leaked
    assert _messages(store, "s1") == ["kept", "after"]


def test_an_abandoned_change_writes_nothing(paths):
    store = HistoryStore(base_dir=paths / "sessions" / "alice")
    before = store.append_message("s1", "user", "kept")["updated_at"]

    assert store.update_message("s1", "no-such-message", "x") is None
    assert store.get_session("s1")["updated_at"] == before


# ---- the startup rule -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "named"),
    [
        ({"HISTORY_BACKEND": "file"}, "HISTORY_BACKEND=sqlite"),
        ({"SESSION_METADATA_BACKEND": "memory"}, "SESSION_METADATA_BACKEND=database"),
        ({"CHROMA_SERVER_URL": ""}, "CHROMA_SERVER_URL"),
    ],
)
def test_shared_state_refuses_a_store_that_is_per_process(paths, overrides, named):
    base = {"HISTORY_BACKEND": "sqlite", "CHROMA_SERVER_URL": "http://chroma:8000"}
    settings = Settings(STATE_BACKEND="shared", **{**base, **overrides})
    with pytest.raises(RuntimeError, match=named):
        validate_shared_state_backends(settings)


def test_shared_state_accepts_the_shareable_stores(paths):
    validate_shared_state_backends(
        Settings(
            STATE_BACKEND="shared",
            HISTORY_BACKEND="sqlite",
            SESSION_METADATA_BACKEND="database",
            CHROMA_SERVER_URL="http://chroma:8000",
        )
    )


def test_one_process_may_keep_its_files(paths):
    validate_shared_state_backends(Settings(STATE_BACKEND="memory", HISTORY_BACKEND="file"))


def test_the_rule_runs_at_startup(paths, monkeypatch):
    from fastapi.testclient import TestClient

    import app.api.application.lifespan as lifespan_module
    from app.api.main import app

    seen = []
    monkeypatch.setattr(lifespan_module, "validate_shared_state_backends", lambda s: seen.append(s))
    with TestClient(app):
        pass
    assert len(seen) == 1


# ---- the migration --------------------------------------------------------------------


def _write_session(directory: Path, session_id: str, content: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "title": content,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "messages": [{"message_id": f"m-{session_id}", "role": "user", "content": content}],
    }
    (directory / f"{session_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def _file_estate(root: Path) -> None:
    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    _write_session(root / "cold" / "alice", "cold1", "alice cold")
    _write_session(root / "cold" / "bob", "cold2", "bob only has cold files")
    _write_session(root / "sessions", "legacy", "a store built with no base_dir")
    # The same session hot and cold: the hot copy is the live one.
    _write_session(root / "cold" / "alice", "both", "stale cold copy")
    _write_session(root / "sessions" / "alice", "both", "live hot copy")


def _migrate(root: Path, **kwargs):
    return migrate_file_sessions(root / "sessions", root / "cold", root / "history.db", **kwargs)


def test_migrated_sessions_are_found_by_the_store(paths):
    _file_estate(paths)
    report = _migrate(paths)

    assert report.verified
    assert (report.sessions, report.imported, report.already_present) == (5, 5, 0)
    alice = HistoryStore(base_dir=paths / "sessions" / "alice")
    assert {s["session_id"] for s in alice.list_sessions()} == {"hot1", "cold1", "both"}
    assert _messages(alice, "both") == ["live hot copy"]
    assert _messages(HistoryStore(base_dir=paths / "sessions" / "bob"), "cold2") == ["bob only has cold files"]
    assert _messages(HistoryStore(base_dir=paths / "sessions"), "legacy") == ["a store built with no base_dir"]


def test_the_migration_can_be_repeated_and_never_overwrites(paths):
    _file_estate(paths)
    _migrate(paths)
    alice = HistoryStore(base_dir=paths / "sessions" / "alice")
    alice.append_message("hot1", "user", "written after the switch")

    again = _migrate(paths)

    assert again.verified
    assert (again.imported, again.already_present) == (0, 5)
    assert _messages(alice, "hot1") == ["alice hot", "written after the switch"]


def test_the_migration_deletes_no_file(paths):
    _file_estate(paths)
    before = sorted(p.relative_to(paths) for p in paths.rglob("*.json"))
    _migrate(paths)
    assert sorted(p.relative_to(paths) for p in paths.rglob("*.json")) == before


def test_a_dry_run_writes_nothing(paths):
    _file_estate(paths)
    report = _migrate(paths, dry_run=True)
    assert (report.sessions, report.imported) == (5, 0)
    with sqlite3.connect(paths / "history.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone() == (0,)


def test_an_unreadable_file_is_reported_and_fails_the_script(paths, capsys):
    _file_estate(paths)
    (paths / "sessions" / "alice" / "broken.json").write_text("{not json", encoding="utf-8")
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        import migrate_sessions_to_sqlite as script
    finally:
        sys.path.remove(str(REPO_ROOT / "scripts"))

    assert script.main([]) == 1
    out = capsys.readouterr().out
    assert "UNREADABLE" in out and "broken.json" in out
    (paths / "sessions" / "alice" / "broken.json").unlink()
    assert script.main([]) == 0


def test_the_namespace_is_the_one_the_store_uses(paths):
    base = paths / "sessions" / "alice"
    assert HistoryStore(base_dir=base)._namespace == namespace_for(base)
