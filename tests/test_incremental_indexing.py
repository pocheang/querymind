from pathlib import Path

from app.services.document_registry import create_document_record, update_document_record
from app.services.index_manager import should_skip_reindex


def test_should_skip_reindex_when_hash_matches_ready(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    source = tmp_path / "note.md"
    source.write_text("hello", encoding="utf-8")
    record = create_document_record(
        source=str(source),
        filename="note.md",
        sha256="2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )
    update_document_record(record["document_id"], {"status": "ready"}, path=registry_path)

    assert should_skip_reindex(source, registry_path=registry_path) is True


def test_should_not_skip_reindex_when_status_not_ready(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    source = tmp_path / "note.md"
    source.write_text("hello", encoding="utf-8")
    create_document_record(
        source=str(source),
        filename="note.md",
        sha256="2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    assert should_skip_reindex(source, registry_path=registry_path) is False
