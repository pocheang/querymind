from pathlib import Path

from app.services.document_registry import (
    create_document_record,
    get_document_by_source,
    list_document_records,
    update_document_record,
)


def test_create_and_list_document_record(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"

    record = create_document_record(
        source=str(tmp_path / "a.pdf"),
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )

    rows = list_document_records(path=registry_path)

    assert len(rows) == 1
    assert rows[0]["document_id"] == record["document_id"]
    assert rows[0]["status"] == "pending"
    assert rows[0]["stage"] == "uploaded"
    assert rows[0]["source"].endswith("a.pdf")


def test_update_document_record_merges_fields(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    record = create_document_record(
        source=str(tmp_path / "a.pdf"),
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )

    update_document_record(
        record["document_id"],
        {"status": "ready", "stage": "complete", "chunks_indexed": 7, "triplets_written": 3},
        path=registry_path,
    )

    updated = get_document_by_source(str(tmp_path / "a.pdf"), path=registry_path)

    assert updated is not None
    assert updated["status"] == "ready"
    assert updated["stage"] == "complete"
    assert updated["chunks_indexed"] == 7
    assert updated["triplets_written"] == 3
    assert updated["error"] == ""


def test_create_document_record_reuses_same_source(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    source = str(tmp_path / "a.pdf")

    first = create_document_record(
        source=source,
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )
    second = create_document_record(
        source=source,
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )

    rows = list_document_records(path=registry_path)

    assert first["document_id"] == second["document_id"]
    assert len(rows) == 1
