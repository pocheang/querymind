"""Exporting a session must not require metadata nobody wrote.

`POST /sessions` creates a session in the history store and **no**
`SessionMetadata`; the only writers of metadata are the edit-metadata endpoint
and import itself. `export_session` opened by fetching that metadata and raising
`KeyError` when it was absent, and the route turns any exception into
`500 "Export failed"`.

So **exporting any session a user had not tagged by hand returned 500** -- which
is every session, for anybody who just asks questions. Found by pressing the
export control on a real session.

This shares a root cause with session search finding nothing: one empty metadata
store, two symptoms. The search half is a labelling problem (it really is a
metadata search); this half is a bug, because messages are the substance of a
session and tags are decoration.
"""

from __future__ import annotations

import io
import json
import uuid
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import _require_user
from app.api.routes.sessions import export as export_routes
from app.services.sessions.export import SessionExportService
from app.services.sessions.history import HistoryStore
from app.services.sessions.metadata import SessionCategory, SessionMetadata, SessionMetadataService, utc_now


class _NoMetadata:
    def get_metadata(self, session_id: str):
        return None


class _WithMetadata:
    def get_metadata(self, session_id: str):
        return SessionMetadata(
            session_id=session_id,
            tags=["值班", "runbook"],
            category=SessionCategory.OTHER if hasattr(SessionCategory, "OTHER") else None,
            description="Falcon 值班复盘",
            created_at=utc_now(),
            updated_at=utc_now(),
            query_count=3,
        )


MESSAGES = [
    {"role": "user", "content": "什么是 RRF"},
    {"role": "assistant", "content": "倒数排名融合[1]。"},
]


def test_an_untagged_session_exports():
    """The regression proper: this raised `KeyError` and surfaced as a 500."""

    service = SessionExportService(metadata_service=_NoMetadata())

    exported = service.export_session(session_id="s-1", messages=MESSAGES)

    assert exported.session_id == "s-1"
    # The messages are the point of an export.
    assert exported.messages == MESSAGES


def test_the_absent_block_has_the_same_shape_as_a_present_one():
    """An importer must read one shape whether or not there was metadata."""

    absent = asdict(SessionExportService(metadata_service=_NoMetadata()).export_session("s-1", MESSAGES))
    present = asdict(SessionExportService(metadata_service=_WithMetadata()).export_session("s-1", MESSAGES))

    assert set(absent["metadata"]) == set(present["metadata"])
    assert absent["metadata"]["tags"] == []
    assert absent["metadata"]["session_id"] == "s-1"


def test_no_date_is_invented_on_export():
    """`created_at` is left null rather than stamped with the export time.

    Guessing it would give a re-imported session a date it never had, which is
    worse than admitting there is none.
    """

    exported = asdict(SessionExportService(metadata_service=_NoMetadata()).export_session("s-1", MESSAGES))

    assert exported["metadata"]["created_at"] is None
    assert exported["metadata"]["updated_at"] is None
    assert exported["metadata"]["last_query_at"] is None


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, HistoryStore]:
    store = HistoryStore(base_dir=tmp_path / "sessions")
    metadata = SessionMetadataService()
    monkeypatch.setattr(export_routes, "_history_store_for_user", lambda _user: store)
    monkeypatch.setattr(export_routes, "get_metadata_service", lambda _user_id: metadata)
    app = FastAPI()
    app.include_router(export_routes.router)
    app.dependency_overrides[_require_user] = lambda: {"user_id": "u-1", "tenant_id": "t-1", "role": "user"}
    return TestClient(app), store


def test_that_export_can_be_imported_again(client):
    """The half that would have broken if only the exporter were fixed.

    Driven through both routes, because the route is the importer: this used
    to call `SessionExportService._dict_to_metadata`, which only a parallel
    import path nothing called ever reached, and was deleted with it.
    """

    http, store = client
    session_id = uuid.uuid4().hex
    store.create_session(session_id=session_id)
    for message in MESSAGES:
        store.append_message(session_id, message["role"], message["content"])

    exported = http.post(f"/api/v1/sessions/{session_id}/export", json={"format": "json"})
    assert exported.status_code == 200
    assert json.loads(exported.content)["metadata"]["created_at"] is None

    imported = http.post(
        "/api/v1/sessions/import?conflict_strategy=rename",
        files={"file": ("s.json", io.BytesIO(exported.content), "application/json")},
    )

    assert imported.status_code == 200, imported.text
    restored = store.get_session(imported.json()["session_id"])
    assert [m["content"] for m in restored["messages"]] == [m["content"] for m in MESSAGES]


@pytest.mark.parametrize("bad", ["", "not-a-date", None])
def test_an_unreadable_date_does_not_break_an_import(client, bad):
    """Import is the one place a hand-edited or foreign file arrives."""

    http, store = client
    document = {
        "session_id": uuid.uuid4().hex,
        "metadata": {"tags": [], "created_at": bad, "updated_at": bad, "last_query_at": bad},
        "messages": MESSAGES,
        "export_version": "1.0",
    }

    imported = http.post(
        "/api/v1/sessions/import",
        files={"file": ("s.json", io.BytesIO(json.dumps(document).encode("utf-8")), "application/json")},
    )

    assert imported.status_code == 200, imported.text
    assert imported.json()["messages_imported"] == len(MESSAGES)
