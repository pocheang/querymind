"""The corpus is parsed once per version, and every version is seen (PERF-01).

Scope resolution reads the whole corpus to learn which documents exist and
ran twice per question -- in the API and in `privacy_permission` -- parsing
every tenant's chunks each time: 2.8 s per call at 100k chunks. The snapshot
is keyed on the file's stat signature, so a write by any process is a new
version without an announcement, and the two halves of a question see the same
rows (the resolver refuses a requested source it cannot see itself).
"""

from __future__ import annotations

import json

import pytest

from app.core.config import get_settings
from app.retrievers.stores import corpus as corpus_module
from app.retrievers.stores.corpus import corpus_snapshot, reset_corpus_snapshot, write_corpus_records
from app.services.documents import index_manager
from app.services.security.access_scope import list_visible_document_rows


def _row(chunk: str, source: str, owner: str, text: str = "text") -> dict:
    return {
        "id": chunk,
        "text": text,
        "metadata": {"source": source, "owner_user_id": owner, "tenant_id": "t1", "visibility": "private"},
    }


@pytest.fixture
def corpus(monkeypatch, tmp_path):
    uploads = tmp_path / "uploads"
    (uploads / "alice").mkdir(parents=True)
    (uploads / "bob").mkdir(parents=True)
    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks.jsonl"))
    monkeypatch.setenv("UPLOADS_DIR", str(uploads))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "docs"))
    get_settings.cache_clear()
    reset_corpus_snapshot()
    alice = str(uploads / "alice" / "a.md")
    bob = str(uploads / "bob" / "b.md")
    write_corpus_records([_row("a1", alice, "alice"), _row("b1", bob, "bob")])
    try:
        yield {"alice": alice, "bob": bob}
    finally:
        get_settings.cache_clear()
        reset_corpus_snapshot()


@pytest.fixture
def parses(monkeypatch) -> list[int]:
    calls: list[int] = []
    real = corpus_module._parse_snapshot

    def counting(target, signature):
        calls.append(1)
        return real(target, signature)

    monkeypatch.setattr(corpus_module, "_parse_snapshot", counting)
    return calls


def test_one_version_is_parsed_once(corpus, parses):
    for _ in range(3):
        list_visible_document_rows({"user_id": "alice", "tenant_id": "t1", "role": "user"})

    assert len(parses) == 1


def test_a_write_is_a_new_version_without_any_announcement(corpus, parses):
    corpus_snapshot()
    write_corpus_records([_row("a1", corpus["alice"], "alice"), _row("a2", corpus["alice"], "alice")])

    assert [row["id"] for row in corpus_snapshot().records] == ["a1", "a2"]
    assert len(parses) == 2


def test_only_the_changed_sources_digest_moves(corpus):
    before = dict(corpus_snapshot().source_digests)
    write_corpus_records([_row("a1", corpus["alice"], "alice", text="edited"), _row("b1", corpus["bob"], "bob")])
    after = corpus_snapshot().source_digests

    assert after[corpus["alice"]] != before[corpus["alice"]]
    assert after[corpus["bob"]] == before[corpus["bob"]]


def test_scope_rows_follow_the_corpus(corpus):
    alice = {"user_id": "alice", "tenant_id": "t1", "role": "user"}
    assert {row["source"] for row in list_visible_document_rows(alice)} == {corpus["alice"]}

    write_corpus_records([_row("b1", corpus["bob"], "bob")])

    assert list_visible_document_rows(alice) == []


def test_a_caller_cannot_corrupt_the_cached_entries(corpus):
    first = index_manager.list_indexed_files()
    for row in first:
        row["visibility"] = "public"
        row["pages"].append(99)

    again = {row["source"]: row for row in index_manager.list_indexed_files()}

    assert again[corpus["alice"]]["visibility"] == "private"
    assert 99 not in again[corpus["alice"]]["pages"]


def test_a_missing_corpus_is_empty_not_an_error(corpus, tmp_path, monkeypatch):
    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "absent.jsonl"))
    get_settings.cache_clear()

    assert corpus_snapshot().records == ()


def test_the_snapshot_reads_what_the_writer_wrote(corpus):
    """Raw lines are hashed, so the digest is over the file, not a re-encoding."""
    path = get_settings().corpus_path
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert [row["id"] for row in corpus_snapshot().records] == [row["id"] for row in lines]
