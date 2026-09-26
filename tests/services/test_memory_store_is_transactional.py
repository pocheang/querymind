"""Long-term memory writes are transactions, and the old JSON files come along.

`MemoryStore` rewrote JSON payloads with no lock of any kind, so two requests
promoting a memory at the same moment -- in one process, not only across
workers -- each wrote back the payload they had read, and one memory was lost.
It keeps one SQLite file per user now, and every change is one
`BEGIN IMMEDIATE`, including `add_candidate`'s two payloads.

The deterministic test lets a raw connection play the other writer and hold
the write lock mid-change. The two-process test is the end-to-end claim. The
rest pin the import of the JSON payloads a checkout already has: it happens
once, it survives two workers opening the same store at once, and it never
resurrects a memory somebody deleted afterwards.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import closing
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.sessions.memory_store import GLOBAL_MEMORY_SESSION_ID, MEMORY_DB_NAME, MemoryStore

REPO_ROOT = Path(__file__).resolve().parents[2]
_HOLD_SECONDS = 0.5


@pytest.fixture
def base(tmp_path, monkeypatch) -> Path:
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    get_settings.cache_clear()
    yield tmp_path / "alice" / "_long_memory"
    get_settings.cache_clear()


def _prompt(worker: str, i: int) -> str:
    return f"remember item {worker}-{i} is stored in bay {i}"


def _contents(store: MemoryStore) -> set[str]:
    return {str(row["content"]) for row in store.list_all()}


# ---- lost updates ---------------------------------------------------------------------


def test_a_promotion_waits_for_a_write_already_in_progress_and_keeps_it(base):
    store = MemoryStore(base_dir=base)
    store.add_candidate("s1", _prompt("a", 1), "ok")

    other = sqlite3.connect(base / MEMORY_DB_NAME, isolation_level=None, check_same_thread=False)
    other.execute("BEGIN IMMEDIATE")
    raw = other.execute("SELECT data_json FROM payloads WHERE session_id=?", (GLOBAL_MEMORY_SESSION_ID,)).fetchone()
    payload = json.loads(raw[0])
    payload["candidates"].append(
        {"candidate_id": "from-the-other-writer", "content": "written by the other worker", "kind": "task"}
    )
    other.execute("UPDATE payloads SET data_json=? WHERE session_id=?", (json.dumps(payload), GLOBAL_MEMORY_SESSION_ID))

    def commit() -> None:
        other.execute("COMMIT")
        other.close()

    timer = threading.Timer(_HOLD_SECONDS, commit)
    timer.start()
    try:
        store.add_candidate("s1", _prompt("a", 2), "ok")
    finally:
        timer.join()

    global_ids = {str(row["candidate_id"]) for row in store.list_global()}
    assert "from-the-other-writer" in global_ids
    assert {"item a-1 is stored in bay 1", "item a-2 is stored in bay 2"} <= _contents(store)


def test_two_processes_promoting_memories_lose_none(base):
    per_worker = 20
    go = base.parent / "go"
    child = (
        "import sys, time\n"
        "from pathlib import Path\n"
        "from app.services.sessions.memory_store import MemoryStore\n"
        "go, base, worker = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]\n"
        "store = MemoryStore(base_dir=base)\n"
        "while not go.exists():\n"
        "    time.sleep(0.01)\n"
        f"for i in range({per_worker}):\n"
        "    assert store.add_candidate(f'w-{worker}', f'remember item {worker}-{i} is stored in bay {i}', 'ok')\n"
    )
    MemoryStore(base_dir=base)
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    workers = [
        subprocess.Popen([sys.executable, "-c", child, str(go), str(base), name], cwd=REPO_ROOT, env=env)
        for name in ("a", "b")
    ]
    time.sleep(3.0)  # both past their imports and spinning on the go file
    go.touch()
    for worker in workers:
        assert worker.wait(timeout=120) == 0

    expected = {f"item {w}-{i} is stored in bay {i}" for w in ("a", "b") for i in range(per_worker)}
    assert _contents(MemoryStore(base_dir=base)) == expected


def test_a_promotion_that_fails_halfway_changes_neither_payload(base, monkeypatch):
    """`add_candidate` writes the global payload and then the session one.

    They used to be two independent writes, so a failure between them left a
    memory in the global payload and not in the session that promoted it.
    """

    store = MemoryStore(base_dir=base)
    store.add_candidate("s1", _prompt("a", 1), "ok")
    before = {sid: store.get_session_payload(sid) for sid in (GLOBAL_MEMORY_SESSION_ID, "s1")}

    calls = []
    original = MemoryStore._recompute_long_term_ids

    def fail_on_the_session_payload(payload):
        calls.append(payload["session_id"])
        if payload["session_id"] == "s1":
            raise RuntimeError("disk full")
        original(payload)

    monkeypatch.setattr(MemoryStore, "_recompute_long_term_ids", staticmethod(fail_on_the_session_payload))
    prompt = _prompt("a", 2)
    with pytest.raises(RuntimeError):
        store.add_candidate("s1", prompt, "ok")
    assert calls == [GLOBAL_MEMORY_SESSION_ID, "s1"], "the global payload was not written first"

    monkeypatch.setattr(MemoryStore, "_recompute_long_term_ids", staticmethod(original))
    assert {sid: store.get_session_payload(sid) for sid in before} == before


# ---- the JSON payloads a checkout already has -----------------------------------------


def _json_payload(directory: Path, session_id: str, *memories: tuple[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    candidates = [
        {
            "candidate_id": memory_id,
            "content": content,
            "answer": content,
            "kind": "explicit_remember",
            "score": 1.0,
            "created_at": "2026-09-01T00:00:00+00:00",
            "updated_at": "2026-09-01T00:00:00+00:00",
            "deleted": False,
        }
        for memory_id, content in memories
    ]
    payload = {"session_id": session_id, "candidates": candidates, "long_term_ids": [m for m, _ in memories]}
    (directory / f"{session_id}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_json_payloads_are_imported_on_first_use_and_kept_on_disk(base):
    _json_payload(base, GLOBAL_MEMORY_SESSION_ID, ("m1", "desk is on floor three"), ("m2", "codename is falcon"))
    _json_payload(base, "s1", ("m1", "desk is on floor three"))
    (base / "broken.json").write_text("{not json", encoding="utf-8")

    store = MemoryStore(base_dir=base)

    assert _contents(store) == {"desk is on floor three", "codename is falcon"}
    assert sorted(p.name for p in base.glob("*.json")) == ["_global.json", "broken.json", "s1.json"]


def test_the_import_happens_once_so_a_deleted_memory_stays_deleted(base):
    _json_payload(base, GLOBAL_MEMORY_SESSION_ID, ("m1", "desk is on floor three"))
    assert MemoryStore(base_dir=base).forget("m1") is True

    assert MemoryStore(base_dir=base).list_all() == []


def test_two_processes_opening_a_fresh_store_at_once_both_succeed(base):
    """Two workers meeting one user's store for the first time.

    Switching a fresh SQLite file to WAL answers "database is locked" at once
    when another connection holds its write lock, without waiting for the busy
    timeout -- which is why this store keeps the default journal.
    """

    _json_payload(base, GLOBAL_MEMORY_SESSION_ID, ("m1", "desk is on floor three"))
    go = base.parent / "go"
    child = (
        "import sys, time\n"
        "from pathlib import Path\n"
        "go = Path(sys.argv[1])\n"
        "from app.services.sessions.memory_store import MemoryStore\n"
        "while not go.exists():\n"
        "    time.sleep(0.005)\n"
        "assert len(MemoryStore(base_dir=Path(sys.argv[2])).list_all()) == 1\n"
    )
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    workers = [
        subprocess.Popen([sys.executable, "-c", child, str(go), str(base)], cwd=REPO_ROOT, env=env) for _ in range(4)
    ]
    time.sleep(3.0)
    go.touch()
    assert [worker.wait(timeout=120) for worker in workers] == [0, 0, 0, 0]
    with closing(sqlite3.connect(base / MEMORY_DB_NAME)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_a_worker_that_waited_for_another_import_does_not_import_again(base):
    """Worker A imports and then deletes a memory while worker B waits to open the store.

    B read "not imported yet" before A committed, so B has to ask again once it
    holds the write lock -- otherwise it imports the JSON files a second time
    and the deleted memory comes back.
    """

    _json_payload(base, GLOBAL_MEMORY_SESSION_ID, ("m1", "desk is on floor three"))
    worker_a = sqlite3.connect(base / MEMORY_DB_NAME, isolation_level=None, check_same_thread=False)
    worker_a.execute("BEGIN IMMEDIATE")
    worker_a.execute(
        "CREATE TABLE payloads(session_id TEXT PRIMARY KEY, data_json TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    deleted = {"session_id": "_global", "candidates": [{"candidate_id": "m1", "deleted": True}], "long_term_ids": []}
    worker_a.execute("INSERT INTO payloads VALUES('_global', ?, '')", (json.dumps(deleted),))
    worker_a.execute("PRAGMA user_version = 1")

    opened: list[MemoryStore] = []
    worker_b = threading.Thread(target=lambda: opened.append(MemoryStore(base_dir=base)))
    worker_b.start()
    time.sleep(_HOLD_SECONDS)  # B is now waiting on A's write lock
    worker_a.execute("COMMIT")
    worker_a.close()
    worker_b.join(timeout=30)

    assert opened, "worker B never opened the store"
    assert opened[0].list_all() == []


def test_opening_an_imported_store_does_not_wait_for_a_writer(base):
    """Every request constructs a store, so opening one must not take the write lock.

    The first check of `user_version` is what keeps it off: without it every
    request would queue behind whichever one is writing this user's memories.
    """

    MemoryStore(base_dir=base)
    writer = sqlite3.connect(base / MEMORY_DB_NAME, isolation_level=None, check_same_thread=False)
    writer.execute("BEGIN IMMEDIATE")
    try:
        opened = threading.Thread(target=lambda: MemoryStore(base_dir=base))
        opened.start()
        opened.join(timeout=5)
        assert not opened.is_alive(), "opening the store waited for another connection's write lock"
    finally:
        writer.execute("COMMIT")
        writer.close()
