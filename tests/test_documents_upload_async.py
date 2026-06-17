from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.api.routes import documents

    app = FastAPI()
    app.include_router(documents.router)
    app.dependency_overrides[documents._require_user] = lambda: {"user_id": "u1", "role": "viewer"}
    with TestClient(app) as test_client:
        yield test_client


def test_upload_creates_registry_record(client, tmp_path: Path, monkeypatch):
    from app.api.routes import documents
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)
    monkeypatch.setattr(documents.settings, "uploads_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(documents.settings, "upload_max_files", 20)
    monkeypatch.setattr(documents.settings, "upload_max_file_bytes", 1024 * 1024)
    monkeypatch.setattr(documents.settings, "upload_max_total_bytes", 1024 * 1024)
    monkeypatch.setattr(documents.settings, "upload_read_chunk_bytes", 64 * 1024)

    with (
        patch("app.api.routes.documents._require_permission"),
        patch("app.api.routes.documents._audit"),
        patch("app.api.routes.documents.upload_limiter", SimpleNamespace(allow=lambda _key: True)),
        patch("app.api.routes.documents.delete_file_index", return_value={"ok": True}),
        patch("app.api.routes.documents.enqueue_ingest_job", return_value=True),
    ):
        response = client.post(
            "/upload",
            files={"files": ("note.md", b"# Hello\nWorld", "text/markdown")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["filenames"] == ["note.md"]
    assert body["indexing_status"] == "queued"

    rows = document_registry.list_document_records(path=registry_path)
    assert len(rows) == 1
    assert rows[0]["filename"] == "note.md"
    assert rows[0]["owner_user_id"] == "u1"
    assert rows[0]["status"] == "pending"


def test_list_documents_includes_pending_registry_records(client, tmp_path: Path, monkeypatch):
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    source = tmp_path / "uploads" / "u1" / "note.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Hello", encoding="utf-8")
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)

    document_registry.create_document_record(
        source=str(source),
        filename="note.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    with (
        patch("app.api.routes.documents._require_permission"),
        patch("app.api.routes.documents._audit"),
        patch("app.api.routes.documents._list_visible_documents_for_user", return_value=[]),
    ):
        response = client.get("/documents")

    assert response.status_code == 200
    rows = response.json()
    assert rows[0]["filename"] == "note.md"
    assert rows[0]["indexing_status"] == "pending"
    assert rows[0]["indexing_stage"] == "uploaded"
