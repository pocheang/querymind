"""Session messages live in their own rows (ARC-05)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing

import pytest

from app.core.config import get_settings
from app.services.runtime.sqlite_schema import ensure_schema
from app.services.sessions.history import HISTORY_MIGRATIONS, HistoryStore, namespace_for


@pytest.fixture
def store_factory(settings_env, tmp_path):
    settings_env(HISTORY_BACKEND="sqlite")

    def make(user="alice") -> HistoryStore:
        return HistoryStore(base_dir=tmp_path / "sessions" / user)

    return make


def _db(store: HistoryStore):
    return closing(sqlite3.connect(store._db_path))


def test_sqlite_is_the_default_backend():
    assert get_settings().model_fields["history_backend"].default == "sqlite"


def test_an_append_inserts_one_row_and_leaves_the_others_alone(store_factory):
    store = store_factory()
    for n in range(4):
        store.append_message("s1", "user", f"m{n}")
    with _db(store) as conn:
        conn.execute("UPDATE session_messages SET message_id='pinned' WHERE seq=0")
        conn.commit()

    store.append_message("s1", "assistant", "m4")

    with _db(store) as conn:
        ids = [r[0] for r in conn.execute("SELECT message_id FROM session_messages ORDER BY seq")]
        head = json.loads(conn.execute("SELECT data_json FROM sessions").fetchone()[0])
    assert ids[0] == "pinned", "an untouched message row was rewritten"
    assert len(ids) == 5
    assert "messages" not in head


def test_listing_reads_the_count_and_not_the_messages(store_factory):
    store = store_factory()
    for n in range(3):
        store.append_message("s1", "user", f"m{n}")
    with _db(store) as conn:
        conn.execute("DELETE FROM session_messages")
        conn.commit()

    assert store.list_sessions()[0]["message_count"] == 3


def test_editing_and_deleting_a_message_round_trip(store_factory):
    store = store_factory()
    for n in range(3):
        store.append_message("s1", "user", f"m{n}")
    messages = store.get_session("s1")["messages"]

    store.update_message("s1", messages[1]["message_id"], "edited")
    store.delete_message("s1", messages[0]["message_id"])

    assert [m["content"] for m in store.get_session("s1")["messages"]] == ["edited", "m2"]
    assert store.list_sessions()[0]["message_count"] == 2


def test_deleting_a_session_removes_its_message_rows(store_factory):
    store = store_factory()
    store.append_message("s1", "user", "hi")
    assert store.delete_session("s1")
    with _db(store) as conn:
        assert conn.execute("SELECT COUNT(*) FROM session_messages").fetchone()[0] == 0


def test_the_migration_splits_a_version_one_blob(tmp_path):
    db = tmp_path / "h.db"
    ensure_schema(db, "history", HISTORY_MIGRATIONS[:1], wal=True)
    blob = {"session_id": "s1", "updated_at": "2026-01-01", "messages": [{"message_id": "a", "content": "x"}]}
    with closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "INSERT INTO sessions(namespace, session_id, data_json, created_at, updated_at) VALUES('n','s1',?,?,?)",
            (json.dumps(blob), "c", "u"),
        )
        conn.commit()

    ensure_schema(db, "history", HISTORY_MIGRATIONS, wal=True)

    with closing(sqlite3.connect(db)) as conn:
        head, count = conn.execute("SELECT data_json, message_count FROM sessions").fetchone()
        rows = conn.execute("SELECT message_id FROM session_messages").fetchall()
    assert "messages" not in json.loads(head)
    assert count == 1
    assert rows == [("a",)]


def test_file_sessions_are_imported_once_when_the_backend_defaults_to_sqlite(settings_env, tmp_path):
    base = tmp_path / "sessions" / "alice"
    base.mkdir(parents=True)
    (base / "old1.json").write_text(
        json.dumps(
            {
                "session_id": "old1",
                "title": "Old",
                "messages": [{"message_id": "m", "role": "user", "content": "hello"}],
            }
        ),
        encoding="utf-8",
    )
    settings_env(HISTORY_BACKEND="sqlite")

    store = HistoryStore(base_dir=base)

    assert store.get_session("old1")["messages"][0]["content"] == "hello"
    assert (base / "old1.json").exists(), "the source file is left in place"
    store.append_message("old1", "assistant", "later")
    (base / "old1.json").write_text(json.dumps({"session_id": "old1", "messages": []}), encoding="utf-8")
    again = HistoryStore(base_dir=base)
    assert len(again.get_session("old1")["messages"]) == 2, "a second construction must not re-import"
    assert namespace_for(base)
