from pathlib import Path

from app.services.document_dedup import compute_sha256, find_duplicate_for_user
from app.services.document_registry import create_document_record


def test_compute_sha256_is_stable(tmp_path: Path):
    path = tmp_path / "note.md"
    path.write_text("hello", encoding="utf-8")

    assert compute_sha256(path) == compute_sha256(path)
    assert len(compute_sha256(path)) == 64


def test_find_duplicate_for_same_user(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    create_document_record(
        source=str(tmp_path / "old.md"),
        filename="old.md",
        sha256="samehash",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    duplicate = find_duplicate_for_user("samehash", "u1", path=registry_path)

    assert duplicate is not None
    assert duplicate["filename"] == "old.md"


def test_find_duplicate_does_not_cross_users(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    create_document_record(
        source=str(tmp_path / "old.md"),
        filename="old.md",
        sha256="samehash",
        owner_user_id="u2",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    assert find_duplicate_for_user("samehash", "u1", path=registry_path) is None
