"""A person must be able to see and delete what this system remembers of them.

`_promote_long_term_memory` runs on every answered query and
`build_memory_context` feeds the result into the next one, so memories about a
user accumulate and shape later answers. The two session-scoped endpoints were
the only way to reach that, and neither could do the job:

  * `list_long_term` returns `long_term_ids`, capped at `LONG_TERM_TOP_N`. It is
    a working set -- what one conversation will be given -- not a record.
  * `delete_long_term` searched only the payload of the session it was called
    on, while `list_long_term` merges the global set into every session's list.
    So it answered 404 for rows it had just returned.

Measured on the shipped code, nine memories stored: a session listed five and
could delete three.

These tests are written against the store rather than a live corpus because
none of that is about retrieval quality; it is about which payloads an
operation reaches.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.services.sessions.memory_store import LONG_TERM_TOP_N, MemoryStore, memory_is_expired

SIGNALS = {"vector_retrieved": 3, "citation_count": 4, "web_used": False}

# Ten things a user might ask this system to hold onto, spread over two
# conversations. Each matches a different promotion rule, so the set exercises
# all four kinds rather than ten copies of one.
PROMPTS = (
    ("session-a", "please remember my desk is on floor three"),
    ("session-b", "remember the team codename is falcon"),
    ("session-a", "I prefer concise answers"),
    ("session-b", "remind me to file the quarterly report"),
    ("session-a", "I am a backend engineer"),
    ("session-b", "my timezone is UTC+8"),
    ("session-a", "remember the deadline is in December"),
    ("session-b", "my editor is neovim"),
    ("session-a", "remind me to renew the certificate"),
    ("session-b", "remember the build server is called atlas"),
)


@pytest.fixture
def root() -> Iterator[Path]:
    """A directory of our own.

    Deliberately not pytest's temporary-path fixture: its basetemp root needs
    directory permissions that are not available on every Windows checkout,
    which this repository already hit in `tests/mcp/test_approval_resume.py`
    and `tests/api/test_advanced_rag_roundtrip.py`.
    """

    path = Path(tempfile.mkdtemp(prefix="querymind-memory-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def store(root: Path) -> MemoryStore:
    """A store holding more memories than any one session can list."""

    memory_store = MemoryStore(base_dir=root / "_long_memory")
    for session_id, question in PROMPTS:
        promoted = memory_store.add_candidate(
            session_id=session_id,
            question=question,
            answer=f"an answer about {question}",
            signals=SIGNALS,
        )
        assert promoted is not None, f"the resolver refused to promote {question!r}, so this fixture proves nothing"
    return memory_store


def _ids(rows: list[dict]) -> set[str]:
    return {str(row["candidate_id"]) for row in rows}


# --- the record is bigger than the working set -----------------------------


def test_a_session_lists_fewer_memories_than_are_stored(store: MemoryStore) -> None:
    """The premise. Without this the rest of the file is solving nothing."""

    listed = store.list_long_term("session-a")
    assert len(listed) == LONG_TERM_TOP_N
    assert len(store.list_all()) > len(listed)


def test_list_all_returns_every_stored_memory(store: MemoryStore) -> None:
    """Including the ones no session would ever show.

    Pinned as a superset of every session's view rather than as a count, so
    this keeps meaning the same thing if the promotion rules change what they
    accept or the resolver starts merging two prompts into one memory.
    """

    everything = _ids(store.list_all())
    for session_id in ("session-a", "session-b", "_global"):
        assert _ids(store.list_long_term(session_id)) <= everything


def test_the_record_does_not_depend_on_which_session_asks(store: MemoryStore) -> None:
    """`list_long_term` gives a different five per session; a record cannot."""

    assert _ids(store.list_long_term("session-a")) != _ids(store.list_long_term("_global"))
    assert store.list_all() == store.list_all()


# --- deleting what was shown ------------------------------------------------


def test_a_memory_one_session_promoted_can_be_deleted_from_another(store: MemoryStore) -> None:
    """The 404 regression, stated as the user sees it.

    Session B lists memories session A promoted -- the store merges the global
    set in -- so every row session B was shown has to be deletable from session
    B. This asserted nothing before the fixture existed: it is only meaningful
    while `cross` is non-empty, which is why that is asserted first.
    """

    b_payload = _ids(store.get_session_payload("session-b").get("candidates", []))
    cross = _ids(store.list_long_term("session-b")) - b_payload
    assert cross, "session B lists nothing it did not promote, so this test would pass vacuously"

    for memory_id in cross:
        assert store.delete_long_term(session_id="session-b", candidate_id=memory_id) is True


def test_forgetting_removes_a_memory_from_the_prompt_as_well_as_the_list(store: MemoryStore) -> None:
    """The half-delete is the failure worth guarding.

    A memory is held twice -- in the global payload and in the session that
    promoted it -- and `list_long_term` reads both. Dropping either copy alone
    leaves it listed and still fed to the model, so "deleted" would report
    success and change nothing.
    """

    target = store.list_long_term("session-a")[0]
    memory_id = str(target["candidate_id"])

    assert store.forget(memory_id) is True

    assert memory_id not in _ids(store.list_all())
    assert memory_id not in _ids(store.list_global())
    for session_id in ("session-a", "session-b", "_global"):
        assert memory_id not in _ids(store.list_long_term(session_id))


def test_forgetting_something_that_was_never_stored_says_so(store: MemoryStore) -> None:
    """This is what the endpoint turns into a 404, so it must stay false."""

    assert store.forget("no-such-memory") is False
    assert store.forget("") is False


def test_forgetting_twice_is_not_a_second_deletion(store: MemoryStore) -> None:
    memory_id = str(store.list_all()[0]["candidate_id"])
    assert store.forget(memory_id) is True
    assert store.forget(memory_id) is False


# --- forgetting everything --------------------------------------------------


def test_forget_all_empties_the_record_and_every_session(store: MemoryStore) -> None:
    stored = len(store.list_all())
    assert stored > 0

    assert store.forget_all() == stored

    assert store.list_all() == []
    for session_id in ("session-a", "session-b", "_global"):
        assert store.list_long_term(session_id) == []


def test_forget_all_counts_memories_rather_than_rows(store: MemoryStore) -> None:
    """A memory held in two payloads is one memory.

    Reporting the row count would tell somebody who was shown nine that
    eighteen were deleted, which reads as data they were never told about.
    """

    shown = len(store.list_all())
    rows = sum(
        len(store.get_session_payload(sid).get("candidates", [])) for sid in ("session-a", "session-b", "_global")
    )
    assert rows > shown, "no memory is stored twice here, so this test cannot detect the miscount"

    assert store.forget_all() == shown


def test_forget_all_on_an_empty_store_is_zero_rather_than_an_error(root: Path) -> None:
    empty = MemoryStore(base_dir=root / "_long_memory")
    assert empty.forget_all() == 0
    assert empty.list_all() == []


def test_a_payload_nobody_can_read_does_not_take_the_others_with_it(store: MemoryStore) -> None:
    """It must not make the rest of the record unreadable OR undeletable.

    The list already skipped a corrupt sibling and the delete did not, which is
    the same half-working shape as the 404 above from a different direction: a
    memory that could be shown and not removed.
    """

    target = str(store.list_all()[0]["candidate_id"])
    (store.base_dir / "session-corrupt.json").write_text("{not json", encoding="utf-8")

    assert len(store.list_all()) > 0
    assert store.forget(target) is True
    assert store.forget_all() >= 0


# --- expiry -----------------------------------------------------------------


def test_an_expired_memory_is_still_listed_and_still_deletable(store: MemoryStore) -> None:
    """It is on disk, so hiding it would answer the question dishonestly.

    An expired memory no longer reaches the model, but it has not gone
    anywhere. A page that omitted it would tell someone the system holds less
    about them than it does, and would give them no way to remove it.
    """

    payload = store.get_session_payload("_global")
    target = payload["candidates"][0]
    target["expires_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    store._write("_global", payload)
    memory_id = str(target["candidate_id"])

    listed = {str(row["candidate_id"]): row for row in store.list_all()}
    assert memory_id in listed
    assert memory_is_expired(listed[memory_id]["expires_at"]) is True
    assert store.forget(memory_id) is True


@pytest.mark.parametrize(
    ("expires_at", "expired"),
    [
        (None, False),
        ("", False),
        ((datetime.now(UTC) + timedelta(days=1)).isoformat(), False),
        ((datetime.now(UTC) - timedelta(days=1)).isoformat(), True),
        # Naive timestamps are read as UTC, the same reading the resolver used.
        ((datetime.now(UTC) - timedelta(days=1)).replace(tzinfo=None).isoformat(), True),
        # An expiry nothing can parse is not a reason to keep using a memory.
        ("whenever", True),
    ],
)
def test_expiry_is_read_the_same_way_everywhere(expires_at: str | None, expired: bool) -> None:
    assert memory_is_expired(expires_at) is expired


# --- the two consumers -------------------------------------------------------
#
# Stored memories reach an answer by two independent routes, and "deleted"
# has to mean deleted on both. `build_memory_context` renders them into the
# prompt through `list_long_term`, which the tests above cover; the `memory`
# retrieval source returns them as EVIDENCE through
# `GBrainLongTermMemory.search`, which reads `list_global` instead. A fix
# checked against one route only is half a deletion.


def _retrieved(root: Path, question: str) -> tuple[str, ...]:
    """What the `memory` retrieval source would hand the synthesizer."""

    import asyncio

    from app.domain.knowledge import AccessScope
    from app.memory.long_term import GBrainLongTermMemory

    provider = GBrainLongTermMemory(base_root=root)
    scope = AccessScope(tenant_id="alice", user_id="alice", role="viewer")
    found = asyncio.run(provider.search(question, scope, 10))
    return tuple(item.content for item in found)


def test_a_forgotten_memory_is_not_retrieved_as_evidence(root: Path) -> None:
    from app.api.utils import memory_helpers
    from app.api.utils.memory_helpers import _memory_store_for_user

    original = memory_helpers.settings
    memory_helpers.settings = SimpleNamespace(sessions_path=root)
    try:
        store = _memory_store_for_user({"user_id": "alice"})
        promoted = store.add_candidate(
            session_id="session-a", question="remember my editor is neovim", answer="noted", signals=SIGNALS
        )
        assert promoted is not None
        assert any("neovim" in content for content in _retrieved(root, "which editor do I use"))

        assert store.forget(str(promoted["candidate_id"])) is True

        assert _retrieved(root, "which editor do I use") == ()
    finally:
        memory_helpers.settings = original


def test_forgetting_everything_empties_the_retrieval_source_too(root: Path) -> None:
    from app.api.utils import memory_helpers
    from app.api.utils.memory_helpers import _memory_store_for_user

    original = memory_helpers.settings
    memory_helpers.settings = SimpleNamespace(sessions_path=root)
    try:
        store = _memory_store_for_user({"user_id": "alice"})
        for session_id, question in PROMPTS:
            store.add_candidate(session_id=session_id, question=question, answer="noted", signals=SIGNALS)
        assert _retrieved(root, "what do you know about me") != ()

        store.forget_all()

        assert _retrieved(root, "what do you know about me") == ()
    finally:
        memory_helpers.settings = original


# --- retention ---------------------------------------------------------------


def test_deleting_a_conversation_does_not_delete_what_it_taught(store: MemoryStore) -> None:
    """Pinned as a decision rather than left as an accident.

    `HistoryStore.delete_session` unlinks the transcript and nothing else, so a
    memory promoted in that conversation outlives it -- which is the design:
    "my timezone is UTC+8" is a fact about the person, not about the thread it
    was mentioned in, and it is deliberately kept in a `_global` payload so it
    can be used elsewhere.

    That is defensible only while the person can see and remove it, which is
    what `list_all` and `forget` are for; without them it was retention with no
    remedy. This test pins BOTH halves, so quietly changing either one fails.
    """

    promoted = store.get_session_payload("session-a")["candidates"]
    assert promoted, "session-a promoted nothing, so this proves nothing"
    memory_id = str(promoted[0]["candidate_id"])

    # Whatever removes the transcript, the memory payload is not it.
    assert memory_id in _ids(store.list_all())
    assert memory_id in _ids(store.list_global())

    # And it remains removable by the person it is about.
    assert store.forget(memory_id) is True
    assert memory_id not in _ids(store.list_all())


# --- the endpoints ----------------------------------------------------------


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The real routes over a real store, rooted in a temporary directory.

    `_memory_store_for_user` is left alone deliberately: how it derives a
    directory from the caller is the thing the isolation test below is for, so
    stubbing it would remove the property under test.
    """

    from app.api import main
    from app.api.utils import memory_helpers

    monkeypatch.setattr(memory_helpers, "settings", SimpleNamespace(sessions_path=root))
    return TestClient(main.app)


def _as(user_id: str) -> dict[str, str]:
    return {"X-Test-User": user_id, "X-Test-User-Id": user_id, "X-Test-Role": "viewer"}


def _remember(client: TestClient, user_id: str, question: str) -> str:
    """Promote one memory through the same helper the query path uses."""

    from app.api.utils.memory_helpers import _memory_store_for_user

    user = {"user_id": user_id}
    row = _memory_store_for_user(user).add_candidate(
        session_id="session-a", question=question, answer="an answer", signals=SIGNALS
    )
    assert row is not None
    return str(row["candidate_id"])


def test_the_endpoint_returns_the_whole_record(client: TestClient) -> None:
    for _session, question in PROMPTS:
        _remember(client, "alice", question)

    response = client.get("/api/v1/memories", headers=_as("alice"))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(body["memories"]) > LONG_TERM_TOP_N
    first = body["memories"][0]
    assert first["kind"] in {"preference", "stable_fact", "task", "explicit_remember"}
    assert first["content"], "a memory the caller cannot read is not something they can judge"
    assert first["active"] is True


def test_one_memory_can_be_forgotten_through_the_endpoint(client: TestClient) -> None:
    memory_id = _remember(client, "alice", "remember my desk is on floor three")

    deleted = client.delete(f"/api/v1/memories/{memory_id}", headers=_as("alice"))

    assert deleted.status_code == 200
    assert deleted.json()["memory_id"] == memory_id
    assert client.get("/api/v1/memories", headers=_as("alice")).json()["memories"] == []


def test_forgetting_an_unknown_memory_is_a_404(client: TestClient) -> None:
    assert client.delete("/api/v1/memories/nope", headers=_as("alice")).status_code == 404


def test_everything_can_be_forgotten_at_once(client: TestClient) -> None:
    for _session, question in PROMPTS:
        _remember(client, "alice", question)
    stored = client.get("/api/v1/memories", headers=_as("alice")).json()["total"]

    purged = client.delete("/api/v1/memories", headers=_as("alice"))

    assert purged.status_code == 200
    assert purged.json()["forgotten"] == stored
    assert client.get("/api/v1/memories", headers=_as("alice")).json()["total"] == 0


def test_forgetting_everything_twice_is_not_an_error(client: TestClient) -> None:
    """The second call has nothing to do and has still done what was asked."""

    _remember(client, "alice", "remember my desk is on floor three")
    assert client.delete("/api/v1/memories", headers=_as("alice")).json()["forgotten"] == 1
    second = client.delete("/api/v1/memories", headers=_as("alice"))
    assert second.status_code == 200
    assert second.json()["forgotten"] == 0


def test_one_persons_memories_are_not_another_persons(client: TestClient) -> None:
    """The property that makes an id in a URL safe to accept.

    Every handler resolves the store from the caller, so Bob's id names nothing
    in Alice's directory -- there is no row for it to reach rather than a check
    that refuses to reach it.
    """

    bob_memory = _remember(client, "bob", "remember the team codename is falcon")
    _remember(client, "alice", "remember my desk is on floor three")

    listed = client.get("/api/v1/memories", headers=_as("alice")).json()["memories"]
    assert bob_memory not in {row["memory_id"] for row in listed}

    assert client.delete(f"/api/v1/memories/{bob_memory}", headers=_as("alice")).status_code == 404
    assert client.delete("/api/v1/memories", headers=_as("alice")).json()["forgotten"] == 1

    assert client.get("/api/v1/memories", headers=_as("bob")).json()["total"] == 1
