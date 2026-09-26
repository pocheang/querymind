"""A session export offers nothing it cannot deliver.

The export dialog had an "include context tracking data" checkbox, ticked by
default, and `POST /api/v1/sessions/{id}/export` took `include_context`. What it
read was `app/services/context_management.py`'s process-local entity tracker --
and **nothing on the request path ever wrote to it**: `process_query` had no
caller anywhere in `app/`. So every export carried `"context": null` whichever
way the box was set, and import answered `context_imported: false` as a
constant. A control that changes nothing reads exactly like one that works until
somebody opens the file.

Removed rather than connected, together with the module: the export route was
its only reader, and its entity extractor was the pronoun/gazetteer design this
repository had already judged wrong for Chinese (see
`tests/knowledge/test_followup_rewriting.py`), so connecting it would have
exported an entity list nobody should trust.

Two compatibility properties matter more than the removal and are pinned here:
an older client still sending `include_context` is ignored rather than refused,
and an export file written before this change -- which carries a `context`
block -- still imports.
"""

from __future__ import annotations

import importlib.util
import io
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import _require_user
from app.api.routes.sessions import export as export_module
from app.services.sessions.history import HistoryStore
from app.services.sessions.metadata import SessionMetadataService

USER: dict[str, Any] = {"user_id": "export-user", "tenant_id": "t-1", "username": "exporter", "role": "user"}


@pytest.fixture
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(base_dir=tmp_path / "sessions")


@pytest.fixture
def client(store: HistoryStore, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    metadata = SessionMetadataService()
    monkeypatch.setattr(export_module, "_history_store_for_user", lambda _user: store)
    monkeypatch.setattr(export_module, "get_metadata_service", lambda _user_id: metadata)
    app = FastAPI()
    app.include_router(export_module.router)
    app.dependency_overrides[_require_user] = lambda: USER
    return TestClient(app)


def test_an_export_carries_no_context_block_even_when_an_old_client_asks(client, store):
    session_id = uuid.uuid4().hex
    store.create_session(session_id=session_id)
    store.append_message(session_id, "user", "RRF 是什么")

    response = client.post(f"/api/v1/sessions/{session_id}/export", json={"format": "json", "include_context": True})

    assert response.status_code == 200
    body = json.loads(response.content)
    assert "context" not in body
    assert [m["content"] for m in body["messages"]] == ["RRF 是什么"]


def test_an_export_written_before_the_removal_still_imports(client, store):
    original = uuid.uuid4().hex
    legacy = {
        "session_id": original,
        "metadata": {"tags": [], "category": None, "description": None},
        "messages": [{"role": "user", "content": "旧的导出文件", "metadata": {}}],
        "context": {"entities": [], "current_topic": None, "previous_topics": [], "current_turn": 0},
        "export_version": "1.0",
        "exported_at": "2026-09-01T00:00:00+00:00",
    }
    upload = io.BytesIO(json.dumps(legacy, ensure_ascii=False).encode("utf-8"))

    response = client.post("/api/v1/sessions/import", files={"file": ("old.json", upload, "application/json")})

    assert response.status_code == 200, response.text
    result = response.json()
    assert "context_imported" not in result
    assert result["messages_imported"] == 1
    assert [m["content"] for m in store.get_session(result["session_id"])["messages"]] == ["旧的导出文件"]


def test_the_tracker_nothing_wrote_to_stays_deleted():
    """Its only reader was the export route; without it the module has none."""

    assert importlib.util.find_spec("app.services.context_management") is None
