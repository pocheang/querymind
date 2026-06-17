from pathlib import Path

from app.services.document_registry import create_document_record, update_document_record
from app.services.index_health import build_index_health_report


def test_build_index_health_report(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    record = create_document_record(
        source=str(tmp_path / "note.md"),
        filename="note.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )
    update_document_record(
        record["document_id"],
        {"status": "ready", "chunks_indexed": 5, "triplets_written": 2},
        path=registry_path,
    )

    report = build_index_health_report(path=registry_path)

    assert report["total_documents"] == 1
    assert report["ready_documents"] == 1
    assert report["failed_documents"] == 0
    assert report["total_chunks"] == 5
    assert report["total_triplets"] == 2
