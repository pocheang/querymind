"""Editing a message and re-running it asks the question the chat path would have asked.

The re-run path diverged from the chat path in three ways: a short question
was sent with a "[补全提示]" block appended (instructions demanding
结论、执行步骤、风险点, which went into retrieval as part of the query and
contradicted the specialists' answer shapes), reasoning was always on, and the
session went in as one pre-rendered block instead of turns. The same edited
question could get a noticeably different answer from the one chat gives.
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.api.routes.public import sessions
from app.services.sessions.history import HistoryStore


@pytest.fixture
def rerun(monkeypatch):
    root = Path(tempfile.mkdtemp(prefix="querymind-rerun-"))
    store = HistoryStore(base_dir=root / "sessions")
    calls: list[dict[str, Any]] = []

    def execute(**kwargs):
        calls.append(kwargs)
        return {"answer": "new answer", "route": "vector", "agent_class": "general"}

    @contextlib.contextmanager
    def credit(*_args, **_kwargs):
        yield SimpleNamespace(commit=lambda: None)

    monkeypatch.setattr(sessions, "execute_standard_compatibility", execute)
    monkeypatch.setattr(sessions, "_reserve_chat_credit", credit)
    monkeypatch.setattr(sessions, "record_grounding_support", lambda *a, **k: None)
    monkeypatch.setattr(sessions, "_promote_long_term_memory", lambda **_: None)
    monkeypatch.setattr(sessions, "_build_memory_context_for_session", lambda **_: "MEMORY")
    monkeypatch.setattr(sessions, "_allowed_sources_for_user", lambda user: ["corpus"])

    session_id = store.create_session()["session_id"]
    for role, content in [
        ("user", "earlier question"),
        ("assistant", "earlier answer"),
        ("user", "年假呢"),
        ("assistant", "old answer"),
        ("user", "a later question"),
        ("assistant", "a later answer"),
    ]:
        store.append_message(session_id, role, content)
    edited = [m for m in store.get_session(session_id)["messages"] if m["content"] == "年假呢"][0]

    def run() -> dict[str, Any]:
        sessions._rerun_after_message_edit(
            request=SimpleNamespace(),
            user={"user_id": "u1", "username": "u", "role": "user", "permissions": []},
            session_id=session_id,
            message_id=edited["message_id"],
            content="年假呢",
            history_store=store,
        )
        return calls[-1]

    try:
        yield run
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_question_is_asked_as_written(rerun) -> None:
    call = rerun()

    assert call["question"] == "年假呢"
    assert "补全提示" not in call["question"]


def test_reasoning_is_off_as_on_the_chat_path(rerun) -> None:
    assert rerun()["use_reasoning"] is False


def test_the_conversation_is_turns_and_only_the_ones_before_the_edited_message(rerun) -> None:
    conversation = rerun()["conversation"]

    assert [(turn.role, turn.content) for turn in conversation] == [
        ("system", "MEMORY"),
        ("user", "earlier question"),
        ("assistant", "earlier answer"),
    ]
