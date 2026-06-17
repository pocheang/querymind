from pathlib import Path
from unittest.mock import patch

from app.services.document_registry import create_document_record, get_document_by_source
from app.services.ingest_queue import run_ingest_job


def test_run_ingest_job_updates_ready_status(tmp_path: Path, monkeypatch):
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)
    source = tmp_path / "note.md"
    source.write_text("# Hello", encoding="utf-8")
    record = create_document_record(
        source=str(source),
        filename="note.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    with patch(
        "app.services.ingest_queue.ingest_paths",
        return_value={"loaded_documents": 1, "chunks_indexed": 2, "triplets_written": 1},
    ):
        run_ingest_job(
            document_id=record["document_id"],
            path=source,
            metadata_overrides={"owner_user_id": "u1", "visibility": "private", "agent_class": "general"},
        )

    updated = get_document_by_source(str(source), path=registry_path)
    assert updated["status"] == "ready"
    assert updated["stage"] == "complete"
    assert updated["chunks_indexed"] == 2
    assert updated["triplets_written"] == 1
    assert updated["error"] == ""


def test_run_ingest_job_updates_failed_status(tmp_path: Path, monkeypatch):
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)
    source = tmp_path / "bad.md"
    source.write_text("# Bad", encoding="utf-8")
    record = create_document_record(
        source=str(source),
        filename="bad.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    with patch("app.services.ingest_queue.ingest_paths", side_effect=RuntimeError("parse failed")):
        run_ingest_job(
            document_id=record["document_id"],
            path=source,
            metadata_overrides={"owner_user_id": "u1", "visibility": "private", "agent_class": "general"},
        )

    updated = get_document_by_source(str(source), path=registry_path)
    assert updated["status"] == "failed"
    assert updated["stage"] == "failed"
    assert "parse failed" in updated["error"]
