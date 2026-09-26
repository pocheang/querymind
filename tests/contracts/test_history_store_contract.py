"""A conversation reads back the same from JSON files and from SQLite (ARC-01 phase 10).

`HistoryStore` picks its backend from HISTORY_BACKEND when it is built, and
every caller -- the query endpoint, the session routes, clarification, export --
holds one without knowing which. STATE_BACKEND=shared requires `sqlite`, and
the init service moves file sessions into it (phase 9), so an installation
switches backend exactly once, on upgrade: whatever the file store promised, the
SQLite store has to keep promising.
"""

from __future__ import annotations

import threading

import pytest

from app.services.sessions.history import DEFAULT_TITLE, HistoryStore


@pytest.fixture(params=["file", "sqlite"])
def backend(request, settings_env) -> str:
    settings_env(HISTORY_BACKEND=request.param)
    return request.param


@pytest.fixture
def store(backend, tmp_path) -> HistoryStore:
    return HistoryStore(base_dir=tmp_path / "sessions" / "alice")


def _contents(data: dict) -> list[tuple[str, str]]:
    return [(m["role"], m["content"]) for m in data["messages"]]


def test_a_created_session_reads_back(store):
    created = store.create_session(title="Budget")

    fetched = store.get_session(created["session_id"])

    assert fetched["title"] == "Budget"
    assert fetched["messages"] == []
    assert fetched["clarification_context"]["clarification_round"] == 0


def test_appending_creates_the_session_and_the_first_question_titles_it(store):
    data = store.append_message("s1", "user", "What is the\nretention window for backups in the EU region?")

    assert data["title"] == "What is the retention window for backups"
    assert _contents(store.get_session("s1")) == [
        ("user", "What is the\nretention window for backups in the EU region?")
    ]


def test_messages_keep_their_order_and_ids(store):
    for n in range(5):
        store.append_message("s1", "user" if n % 2 == 0 else "assistant", f"m{n}")

    messages = store.get_session("s1")["messages"]

    assert [m["content"] for m in messages] == ["m0", "m1", "m2", "m3", "m4"]
    assert len({m["message_id"] for m in messages}) == 5


def test_a_later_store_sees_what_an_earlier_one_wrote(backend, tmp_path):
    """A restart, or another worker's instance: nothing lives only in the object."""

    base = tmp_path / "sessions" / "alice"
    HistoryStore(base_dir=base).append_message("s1", "user", "hello")

    assert _contents(HistoryStore(base_dir=base).get_session("s1")) == [("user", "hello")]


def test_one_users_sessions_are_invisible_to_another(backend, tmp_path):
    HistoryStore(base_dir=tmp_path / "sessions" / "alice").append_message("s1", "user", "alice's question")
    bob = HistoryStore(base_dir=tmp_path / "sessions" / "bob")

    assert bob.get_session("s1") is None
    assert bob.list_sessions() == []


def test_the_list_is_newest_first_with_counts(store):
    store.append_message("older", "user", "one")
    store.append_message("newer", "user", "two")
    store.append_message("newer", "assistant", "three")

    listed = store.list_sessions()

    assert [(s["session_id"], s["message_count"]) for s in listed] == [("newer", 2), ("older", 1)]


def test_editing_and_deleting_messages(store):
    first = store.append_message("s1", "user", "first question")["messages"][0]["message_id"]
    second = store.append_message("s1", "user", "second question")["messages"][1]["message_id"]

    store.update_message("s1", first, "edited question")
    assert store.get_session("s1")["title"] == "edited question"
    store.delete_message("s1", first)

    data = store.get_session("s1")
    assert _contents(data) == [("user", "second question")]
    assert data["title"] == "second question"
    assert store.update_message("s1", "no-such-message", "x") is None
    assert store.get_message("s1", second)["content"] == "second question"


def test_an_answer_is_placed_after_its_question_and_replaced_on_rerun(store):
    question = store.append_message("s1", "user", "q")["messages"][0]["message_id"]
    store.append_message("s1", "user", "later q")

    store.upsert_assistant_after_user("s1", question, "first answer")
    store.upsert_assistant_after_user("s1", question, "second answer")

    assert _contents(store.get_session("s1")) == [("user", "q"), ("assistant", "second answer"), ("user", "later q")]


def test_title_pin_and_strategy_lock(store):
    store.create_session(session_id="s1")

    store.update_session_title("s1", "Renamed")
    store.update_session_pinned("s1", True)
    store.set_session_strategy_lock("s1", "hybrid")

    data = store.get_session("s1")
    assert (data["title"], data["pinned"]) == ("Renamed", True)
    assert store.get_session_strategy_lock("s1") == "hybrid"


def test_clarification_context_round_trip(store):
    store.create_session(session_id="s1")

    store.update_clarification_context("s1", "region", "EU")
    assert store.get_clarification_context("s1")["collected_info"] == {"region": "EU"}
    store.reset_clarification_context("s1")

    assert store.get_clarification_context("s1")["collected_info"] == {}
    assert store.get_clarification_context("missing") is None


def test_deleting_a_session(store):
    store.append_message("s1", "user", "hello")

    assert store.delete_session("s1") is True
    assert store.delete_session("s1") is False
    assert store.get_session("s1") is None


@pytest.mark.parametrize("bad", ["../etc", "a/b", "", "x" * 300])
def test_an_invalid_session_id_names_nothing(store, bad):
    assert store.get_session(bad) is None
    assert store.delete_session(bad) is False
    with pytest.raises(ValueError):
        store.append_message(bad, "user", "hello")


def test_concurrent_appends_from_two_instances_lose_nothing(backend, tmp_path):
    """Two request handlers holding their own store for one conversation."""

    base = tmp_path / "sessions" / "alice"
    stores = [HistoryStore(base_dir=base), HistoryStore(base_dir=base)]
    stores[0].create_session(session_id="s1")

    def write(which: int) -> None:
        for n in range(25):
            stores[which].append_message("s1", "user", f"{which}-{n}")

    threads = [threading.Thread(target=write, args=(which,)) for which in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    contents = [m["content"] for m in stores[1].get_session("s1")["messages"]]
    assert sorted(contents) == sorted(f"{w}-{n}" for w in (0, 1) for n in range(25))


def test_a_new_session_has_the_default_title(store):
    assert store.get_or_create_session("s1")["title"] == DEFAULT_TITLE
    assert store.get_or_create_session("s1")["session_id"] == "s1"
