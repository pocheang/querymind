"""The init service moves a single-worker installation's data before shared mode reads it (ARC-01 phase 9).

Shared state became the default, so an existing deployment upgrades onto it
holding file sessions and vectors in an embedded Chroma directory -- neither of
which shared mode reads. `migrate_legacy_data` runs the two existing migration
tools from the init service, and three things about it are the point:

- **It reports rather than raises.** A problem goes to the returned list and
  `main()` exits non-zero, which compose turns into a backend that does not
  start (`service_completed_successfully`). Starting on half-moved data would
  show every user an empty history and an empty index, and look healthy.
- **A marker is written only after verification.** The marker is what lets the
  next deploy skip a bulk copy; written after a partial copy, it would make the
  gap permanent.
- **It does nothing outside shared mode**, where the legacy stores are still
  the live ones.

Every path is under tmp_path, and the "server" is a second local Chroma client:
the copy only speaks the client API (tests/retrievers/test_chroma_migration.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
import pytest

from app import init_app
from app.core.config import Settings, get_settings
from app.retrievers.stores import chroma_migration
from app.retrievers.stores.chroma_migration import CollectionCopy
from app.services.sessions import history_migration
from app.services.sessions.history import HistoryStore
from app.services.sessions.history_migration import MigrationReport


@pytest.fixture
def root(tmp_path, monkeypatch):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    values = {
        "RUNTIME_ENV_FILE": str(empty_env),
        "NACOS_ENABLED": "false",
        "API_SETTINGS_ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef0123456789abcdef",
        "STATE_BACKEND": "shared",
        "HISTORY_BACKEND": "sqlite",
        "SESSION_METADATA_BACKEND": "database",
        "CHROMA_SERVER_URL": "http://chroma-test:8000",
        "CHROMA_PERSIST_DIR": str(tmp_path / "chroma"),
        "SESSIONS_DIR": str(tmp_path / "sessions"),
        "HISTORY_COLD_DIR": str(tmp_path / "cold"),
        "HISTORY_SQLITE_PATH": str(tmp_path / "history.db"),
        "APP_DB_PATH": str(tmp_path / "app.db"),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


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


def _chroma(path: Path) -> chromadb.ClientAPI:
    # Default settings, as init_app opens the source: Chroma refuses a second
    # client on one path whose settings differ.
    return chromadb.PersistentClient(path=str(path))


@pytest.fixture
def server(root, monkeypatch):
    """A local client standing in for the Chroma server init would reach over HTTP."""

    target = _chroma(root / "server")
    monkeypatch.setattr("app.retrievers.stores.vector.chroma_http_client", lambda url: target)
    return target


def _embedded_store(root: Path, count: int = 6) -> None:
    docs = _chroma(root / "chroma").get_or_create_collection("local_rag_collection")
    docs.upsert(
        ids=[f"chunk-{i}" for i in range(count)],
        embeddings=[[float(i), 1.0, 0.5] for i in range(count)],
        documents=[f"text {i}" for i in range(count)],
        metadatas=[{"source": f"s{i}", "owner_user_id": "alice"} for i in range(count)],
    )


def _sessions_marker(root: Path) -> Path:
    return root / "sessions" / init_app._SESSIONS_MARKER


def _chroma_marker(root: Path) -> Path:
    return root / "chroma" / init_app._CHROMA_MARKER


def _forbid(monkeypatch, target: str) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError(f"{target} ran")

    monkeypatch.setattr(target, refuse)


# ---- sessions -------------------------------------------------------------------------


def test_file_sessions_are_imported_verified_and_marked(root, server):
    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    _write_session(root / "cold" / "alice", "cold1", "alice cold")

    assert init_app.migrate_legacy_data(Settings()) == []

    alice = HistoryStore(base_dir=root / "sessions" / "alice")
    assert {s["session_id"] for s in alice.list_sessions()} == {"hot1", "cold1"}
    assert "2 sessions verified" in _sessions_marker(root).read_text(encoding="utf-8")
    assert (root / "sessions" / "alice" / "hot1.json").exists(), "the source is never deleted"


def test_a_user_with_only_cold_sessions_is_still_migrated(root, server):
    """Checking only the hot directory for work to do would skip this user and write no problem at all."""

    _write_session(root / "cold" / "bob", "cold2", "bob only has cold files")

    assert init_app.migrate_legacy_data(Settings()) == []

    bob = HistoryStore(base_dir=root / "sessions" / "bob")
    assert [s["session_id"] for s in bob.list_sessions()] == ["cold2"]
    assert _sessions_marker(root).exists()


def test_a_marked_installation_is_not_copied_again(root, server, monkeypatch):
    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    _sessions_marker(root).write_text("verified earlier\n", encoding="utf-8")
    _forbid(monkeypatch, "app.services.sessions.history_migration.migrate_file_sessions")

    assert init_app.migrate_legacy_data(Settings()) == []


def test_an_unreadable_session_is_a_problem_and_leaves_no_marker(root, server):
    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    (root / "sessions" / "alice" / "broken.json").write_text("{not json", encoding="utf-8")

    problems = init_app.migrate_legacy_data(Settings())

    assert any("unreadable session file" in problem and "broken.json" in problem for problem in problems)
    assert not _sessions_marker(root).exists()


def test_a_session_missing_after_import_is_a_problem(root, server, monkeypatch):
    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    monkeypatch.setattr(
        history_migration,
        "migrate_file_sessions",
        lambda *a, **k: MigrationReport(sessions=1, imported=1, missing_after=["alice/hot1"]),
    )

    problems = init_app.migrate_legacy_data(Settings())

    assert problems == ["session not found after import alice/hot1"]
    assert not _sessions_marker(root).exists()


def test_sessions_the_tool_did_not_account_for_are_a_problem(root, server, monkeypatch):
    """No id missing and no file unreadable, and still one session short: the report's own `verified`."""

    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    monkeypatch.setattr(
        history_migration, "migrate_file_sessions", lambda *a, **k: MigrationReport(sessions=3, imported=2)
    )

    problems = init_app.migrate_legacy_data(Settings())

    assert problems == ["sessions: 2 accounted for of 3 found"]
    assert not _sessions_marker(root).exists()


# ---- vectors --------------------------------------------------------------------------


def test_embedded_vectors_are_copied_verified_and_marked(root, server):
    _embedded_store(root)

    assert init_app.migrate_legacy_data(Settings()) == []

    copied = server.get_collection("local_rag_collection")
    assert copied.count() == 6
    assert copied.get(ids=["chunk-4"], include=["metadatas"])["metadatas"][0]["owner_user_id"] == "alice"
    assert "local_rag_collection=6" in _chroma_marker(root).read_text(encoding="utf-8")
    assert _chroma(root / "chroma").get_collection("local_rag_collection").count() == 6, "the source is kept"


def test_a_marked_store_is_not_copied_again(root, server, monkeypatch):
    _embedded_store(root)
    _chroma_marker(root).write_text("copied earlier\n", encoding="utf-8")
    _forbid(monkeypatch, "app.retrievers.stores.chroma_migration.copy_collections")

    assert init_app.migrate_legacy_data(Settings()) == []
    assert "local_rag_collection" not in [getattr(c, "name", c) for c in server.list_collections()]


def test_a_vector_the_server_did_not_keep_is_a_problem(root, server, monkeypatch):
    _embedded_store(root)
    real_missing = chroma_migration._missing
    monkeypatch.setattr(chroma_migration, "_missing", lambda target, ids: real_missing(target, ids) + ids[:1])

    problems = init_app.migrate_legacy_data(Settings())

    assert problems == ["vector chunk-0 in local_rag_collection not found after copy"]
    assert not _chroma_marker(root).exists()


def test_a_short_copy_is_a_problem(root, server, monkeypatch):
    """Every id sent was found, but not every id was sent: a page loop that ended early."""

    _embedded_store(root)
    monkeypatch.setattr(
        chroma_migration,
        "copy_collections",
        lambda source, target: [CollectionCopy(name="local_rag_collection", source_count=6, copied=4)],
    )

    problems = init_app.migrate_legacy_data(Settings())

    assert problems == ["vectors: local_rag_collection copied 4 of 6"]
    assert not _chroma_marker(root).exists()


# ---- when there is nothing to do -------------------------------------------------------


def test_memory_mode_moves_nothing(root, monkeypatch):
    """There the legacy stores are the live ones; copying them would fork the data."""

    monkeypatch.setenv("STATE_BACKEND", "memory")
    _write_session(root / "sessions" / "alice", "hot1", "alice hot")
    _embedded_store(root)
    _forbid(monkeypatch, "app.services.sessions.history_migration.migrate_file_sessions")
    _forbid(monkeypatch, "app.retrievers.stores.chroma_migration.copy_collections")

    assert init_app.migrate_legacy_data(Settings()) == []
    assert not _sessions_marker(root).exists() and not _chroma_marker(root).exists()


def test_a_fresh_installation_has_nothing_to_move(root, monkeypatch):
    _forbid(monkeypatch, "app.services.sessions.history_migration.migrate_file_sessions")
    _forbid(monkeypatch, "app.retrievers.stores.chroma_migration.copy_collections")

    assert init_app.migrate_legacy_data(Settings()) == []


# ---- the exit code compose waits on ------------------------------------------------------


@pytest.fixture
def quiet_main(monkeypatch):
    monkeypatch.setattr(init_app, "run", lambda settings=None: {"app_db": 3})
    monkeypatch.setattr(init_app.logging, "basicConfig", lambda **kwargs: None)


def test_main_succeeds_when_nothing_is_wrong(quiet_main, monkeypatch):
    monkeypatch.setattr(init_app, "migrate_legacy_data", lambda settings=None: [])

    assert init_app.main([]) == 0


def test_a_problem_exits_non_zero_and_is_named(quiet_main, monkeypatch, capsys):
    monkeypatch.setattr(init_app, "migrate_legacy_data", lambda settings=None: ["vector chunk-0 missing"])

    assert init_app.main([]) == 1
    assert "MIGRATION PROBLEM: vector chunk-0 missing" in capsys.readouterr().err


def test_a_long_list_of_problems_says_how_long(quiet_main, monkeypatch, capsys):
    problems = [f"vector chunk-{i} missing" for i in range(init_app._PROBLEMS_SHOWN + 7)]
    monkeypatch.setattr(init_app, "migrate_legacy_data", lambda settings=None: problems)

    assert init_app.main([]) == 1
    err = capsys.readouterr().err
    assert err.count("MIGRATION PROBLEM:") == init_app._PROBLEMS_SHOWN + 1
    assert "... and 7 more" in err
