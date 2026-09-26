"""What ingest_paths does, pinned before it was split up.

It was one 171-line function with no test of its own: load, count, split, write
the corpus, write the parents, reset caches, rebuild the vector store, extract
graph triplets, and assemble a result whose shape differs between the empty case
and every other one. These tests describe that behaviour rather than the code, so
they hold across the refactor -- which is the only way to know a 171-line
function came apart without taking something with it.

Every collaborator is faked. What is under test is the orchestration: what runs,
with what, and what survives a failure.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from langchain_core.documents import Document

from app.services.documents import ingest as ingest_module


@dataclass
class _FakeEvidenceDocument:
    source: str
    filename: str = "report.pdf"
    document_id: str = "doc-1"
    version: int = 1
    tenant_id: str = "tenant-1"
    owner_user_id: str = "user-1"
    visibility: str = "private"
    acl_tags: tuple[str, ...] = ()
    sha256: str = "abc123"


@dataclass
class _FakeParsed:
    document: _FakeEvidenceDocument
    parser: str = "fake"
    images: tuple[Any, ...] = ()
    tables: tuple[Any, ...] = ()


@dataclass
class _Triplet:
    head: str
    relation: str
    tail: str
    confidence: float = 0.9


@dataclass
class _Calls:
    corpus_written: list[list[dict]] = field(default_factory=list)
    parents_written: list[list[dict]] = field(default_factory=list)
    added: list[tuple[list[Document], list[str]]] = field(default_factory=list)
    upserted: list[list[dict]] = field(default_factory=list)
    deleted_collection: int = 0
    bm25_reset: int = 0
    retrieval_cache_cleared: int = 0
    vector_cache_cleared: int = 0
    closed: int = 0


class _FakeStore:
    def __init__(self, calls: _Calls) -> None:
        self._calls = calls

    def delete_collection(self) -> None:
        self._calls.deleted_collection += 1


class _FakeNeo4j:
    def __init__(self, calls: _Calls, *, upsert_error: Exception | None = None) -> None:
        self._calls = calls
        self._upsert_error = upsert_error

    def batch_upsert_triplets(self, rows: list[dict]) -> int:
        self._calls.upserted.append(list(rows))
        if self._upsert_error is not None:
            raise self._upsert_error
        return len(rows)

    def close(self) -> None:
        self._calls.closed += 1


def _bump(calls: _Calls, name: str) -> None:
    setattr(calls, name, getattr(calls, name) + 1)


@pytest.fixture
def wiring(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    """Replace every collaborator, leaving only the orchestration under test."""

    calls = _Calls()

    def load(path: Path, metadata: dict[str, Any]):
        parsed = _FakeParsed(_FakeEvidenceDocument(source=str(path), document_id=f"doc-{path.stem}"))
        loaded = [Document(page_content=f"body of {path.name}", metadata={"page": 1, "image_id": "img-1"})]
        return parsed, loaded

    def split(docs: list[Document]):
        chunks = [Document(page_content=doc.page_content, metadata=dict(doc.metadata)) for doc in docs]
        parents = [{"id": f"parent-{index}"} for index, _ in enumerate(chunks)]
        return chunks, parents

    def to_records(chunks: list[Document]) -> list[dict]:
        return [
            {"id": f"chunk-{index}", "metadata": {**chunk.metadata, "chunk_id": f"chunk-{index}"}}
            for index, chunk in enumerate(chunks)
        ]

    monkeypatch.setattr(ingest_module, "load_document_with_evidence", load)
    monkeypatch.setattr(ingest_module, "_persist_evidence", lambda parsed, path: {"img-1": "artifact://img-1"})
    monkeypatch.setattr(ingest_module, "_existing_image_artifacts", lambda parsed: {"img-1": "existing://img-1"})
    monkeypatch.setattr(ingest_module, "split_documents", split)
    monkeypatch.setattr(ingest_module, "documents_to_records", to_records)
    monkeypatch.setattr(ingest_module, "read_corpus_records", lambda: [{"id": "chunk-old"}])
    monkeypatch.setattr(ingest_module, "read_parent_records", lambda: [{"id": "parent-old"}])
    monkeypatch.setattr(ingest_module, "write_corpus_records", lambda rows: calls.corpus_written.append(list(rows)))
    monkeypatch.setattr(ingest_module, "write_parent_records", lambda rows: calls.parents_written.append(list(rows)))
    monkeypatch.setattr(ingest_module, "reset_bm25_cache", lambda: _bump(calls, "bm25_reset"))
    monkeypatch.setattr(ingest_module, "clear_retrieval_cache", lambda: _bump(calls, "retrieval_cache_cleared"))
    monkeypatch.setattr(ingest_module, "clear_vector_store_cache", lambda: _bump(calls, "vector_cache_cleared"))
    monkeypatch.setattr(ingest_module, "get_vector_store", lambda: _FakeStore(calls))
    monkeypatch.setattr(ingest_module, "embed_texts", lambda collection, texts: [[0.0] for _ in texts])

    def upsert(collection, ids, texts, metadatas, embeddings):
        if collection is None:
            docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas, strict=True)]
            calls.added.append((docs, list(ids)))

    monkeypatch.setattr(ingest_module, "upsert_texts", upsert)
    monkeypatch.setattr(ingest_module, "index_writes", nullcontext)
    monkeypatch.setattr(ingest_module, "Neo4jClient", lambda: _FakeNeo4j(calls))
    monkeypatch.setattr(
        ingest_module,
        "extract_graph_triplets_with_diagnostics",
        lambda text, min_confidence: ([_Triplet("A", "relates_to", "B")], {"llm": 1, "discarded_low_confidence": 0}),
    )
    return calls


def test_nothing_loaded_returns_the_short_result_and_touches_no_store(wiring: _Calls, monkeypatch) -> None:
    """The empty result has three keys, where the full one has six.

    A file that parses to no text still has evidence persisted for it -- the
    early return discards the manifest it just wrote, which is worth knowing
    before reading the two result shapes as the same thing.
    """

    def parses_to_nothing(path: Path, metadata: dict[str, Any]):
        return _FakeParsed(_FakeEvidenceDocument(source=str(path))), []

    monkeypatch.setattr(ingest_module, "load_document_with_evidence", parses_to_nothing)

    result = ingest_module.ingest_paths([Path("a.pdf")])

    assert result == {"loaded_documents": 0, "chunks_indexed": 0, "triplets_written": 0}
    assert wiring.corpus_written == []
    assert wiring.added == []
    assert wiring.bm25_reset == 0


def test_the_full_result_counts_sources_pages_and_triplets(wiring: _Calls) -> None:
    result = ingest_module.ingest_paths([Path("a.pdf"), Path("b.pdf")])

    assert result["loaded_documents"] == 2
    assert result["chunks_indexed"] == 2
    assert result["triplets_written"] == 2
    # Pages are gathered as a set per source and reported as a count.
    assert result["pages_by_source"] == {"a.pdf": 1, "b.pdf": 1}
    assert [manifest["document_id"] for manifest in result["evidence_manifests"]] == ["doc-a", "doc-b"]


def test_indexed_chunks_carry_overrides_canonical_metadata_and_the_artifact_uri(wiring: _Calls) -> None:
    ingest_module.ingest_paths(
        [Path("a.pdf")],
        metadata_overrides_by_source={"a.pdf": {"campaign": "q3"}},
    )

    indexed_chunks, ids = wiring.added[0]
    metadata = indexed_chunks[0].metadata
    assert metadata["campaign"] == "q3"  # the caller's override
    assert metadata["document_id"] == "doc-a"  # canonical, from the parsed document
    assert metadata["artifact_uri"] == "artifact://img-1"  # matched on image_id
    assert ids == ["chunk-0"]  # the records' ids, not the chunks' own


def test_persist_evidence_off_reuses_the_artifacts_already_stored(wiring: _Calls) -> None:
    ingest_module.ingest_paths([Path("a.pdf")], persist_evidence=False)

    indexed_chunks, _ = wiring.added[0]
    assert indexed_chunks[0].metadata["artifact_uri"] == "existing://img-1"


def test_an_incremental_run_merges_with_what_is_already_stored(wiring: _Calls) -> None:
    ingest_module.ingest_paths([Path("a.pdf")])

    assert [row["id"] for row in wiring.corpus_written[0]] == ["chunk-old", "chunk-0"]
    assert [row["id"] for row in wiring.parents_written[0]] == ["parent-old", "parent-0"]
    assert wiring.deleted_collection == 0
    assert wiring.bm25_reset == 1
    assert wiring.retrieval_cache_cleared == 1


def test_a_reset_run_drops_the_collection_and_keeps_nothing_from_before(wiring: _Calls) -> None:
    ingest_module.ingest_paths([Path("a.pdf")], reset_vector_store=True)

    assert [row["id"] for row in wiring.corpus_written[0]] == ["chunk-0"]
    assert [row["id"] for row in wiring.parents_written[0]] == ["parent-0"]
    assert wiring.deleted_collection == 1
    assert wiring.vector_cache_cleared == 1


def _service_unavailable() -> Exception:
    from neo4j.exceptions import ServiceUnavailable

    return ServiceUnavailable("Couldn't connect to neo4j:7687")


@pytest.mark.parametrize("failure", [lambda: RuntimeError("no route to host"), _service_unavailable])
def test_indexing_happens_even_when_the_graph_is_unavailable(wiring: _Calls, monkeypatch, failure) -> None:
    """Neo4j is optional -- a client that will not construct costs the triplets, nothing else.

    With the exception the real driver raises for a server it cannot reach, not
    only a `RuntimeError`: that stand-in happened to be a type the code caught,
    and the driver's is not.
    """

    def refuse():
        raise failure()

    monkeypatch.setattr(ingest_module, "Neo4jClient", refuse)

    result = ingest_module.ingest_paths([Path("a.pdf")])

    assert result["chunks_indexed"] == 1
    assert result["triplets_written"] == 0
    assert wiring.added
    assert wiring.upserted == []


def test_a_source_that_disables_the_graph_contributes_no_triplets(wiring: _Calls) -> None:
    result = ingest_module.ingest_paths(
        [Path("a.pdf")],
        parser_profiles_by_source={"a.pdf": {"enable_graph": False}},
    )

    assert result["chunks_indexed"] == 1
    assert result["triplets_written"] == 0
    assert wiring.upserted == []
    assert wiring.closed == 1


def test_one_chunk_failing_extraction_does_not_lose_the_others(wiring: _Calls, monkeypatch) -> None:
    def extract(text: str, min_confidence: float):
        if "a.pdf" in text:
            raise ValueError("unparseable")
        return [_Triplet("A", "relates_to", "B")], {"llm": 1, "discarded_low_confidence": 0}

    monkeypatch.setattr(ingest_module, "extract_graph_triplets_with_diagnostics", extract)

    result = ingest_module.ingest_paths([Path("a.pdf"), Path("b.pdf")])

    assert result["triplets_written"] == 1
    assert [row["source"] for row in wiring.upserted[0]] == ["b.pdf"]


def test_a_failed_batch_insert_reports_no_triplets_and_still_closes_the_client(wiring: _Calls, monkeypatch) -> None:
    monkeypatch.setattr(
        ingest_module, "Neo4jClient", lambda: _FakeNeo4j(wiring, upsert_error=RuntimeError("write conflict"))
    )

    result = ingest_module.ingest_paths([Path("a.pdf")])

    assert result["chunks_indexed"] == 1
    assert result["triplets_written"] == 0
    assert wiring.closed == 1


def test_an_unreadable_page_number_leaves_the_source_out_rather_than_at_zero(wiring: _Calls, monkeypatch) -> None:
    """A count of 0 would claim the document has no pages, which is a different thing."""

    def load(path: Path, metadata: dict[str, Any]):
        parsed = _FakeParsed(_FakeEvidenceDocument(source=str(path), document_id=f"doc-{path.stem}"))
        return parsed, [Document(page_content="body", metadata={"page": "not a number"})]

    monkeypatch.setattr(ingest_module, "load_document_with_evidence", load)

    result = ingest_module.ingest_paths([Path("a.pdf")])

    assert result["pages_by_source"] == {}
    assert result["chunks_indexed"] == 1


def test_a_documents_images_are_indexed_and_counted(wiring: _Calls, monkeypatch) -> None:
    """The multimodal source reads what this writes; before it, nothing did."""

    @dataclass
    class _Image:
        image_id: str = "img-1"
        page: int = 1
        filename: str = "figure-1.png"
        data: bytes = b""
        ocr_text: str = "Deployment topology"
        description: str = ""

    def load(path: Path, metadata: dict[str, Any]):
        parsed = _FakeParsed(
            _FakeEvidenceDocument(source=str(path), document_id=f"doc-{path.stem}"),
            images=(_Image(),),
        )
        return parsed, [Document(page_content="body", metadata={"page": 1})]

    indexed: list[object] = []

    class _FakeProcessor:
        def index_entry(self, image):
            return image.description, {}

        def index_image(self, image, collection_name: str = "image_descriptions", *, embedding=None) -> None:
            indexed.append(image)

    monkeypatch.setattr(ingest_module, "load_document_with_evidence", load)
    monkeypatch.setattr("app.services.multimodal.image_processor.ImageProcessor", _FakeProcessor)

    result = ingest_module.ingest_paths([Path("a.pdf")])

    assert result["images_indexed"] == 1
    assert indexed
    assert "Deployment topology" in indexed[0].description


def test_the_empty_result_reports_no_images_key(wiring: _Calls, monkeypatch) -> None:
    """The short result keeps its three keys; images_indexed belongs to the full one."""

    def parses_to_nothing(path: Path, metadata: dict[str, Any]):
        return _FakeParsed(_FakeEvidenceDocument(source=str(path))), []

    monkeypatch.setattr(ingest_module, "load_document_with_evidence", parses_to_nothing)

    assert "images_indexed" not in ingest_module.ingest_paths([Path("a.pdf")])


def test_a_run_that_fell_back_to_rules_writes_no_triplets_and_says_so(wiring: _Calls, monkeypatch) -> None:
    """Zero triplets has several causes and the result must distinguish them.

    On an installation with no working LLM the rule extractor produces
    candidates and every one scores below the profile threshold -- correctly, but
    a bare `triplets_written: 0` cannot be told apart from "no Neo4j" or "nothing
    extractable", and a graph route that quietly returns nothing looks like a
    retrieval problem rather than a configuration one.
    """

    monkeypatch.setattr(
        ingest_module,
        "extract_graph_triplets_with_diagnostics",
        lambda text, min_confidence: ([], {"rules_llm_fallback": 3, "discarded_low_confidence": 3}),
    )

    result = ingest_module.ingest_paths([Path("a.pdf")])

    assert result["triplets_written"] == 0
    assert result["triplets_discarded_low_confidence"] == 3
    assert result["triplet_methods"] == {"rules_llm_fallback": 3}
    assert wiring.upserted == []


def test_only_the_writes_happen_under_the_index_lock(wiring: _Calls, monkeypatch, tmp_path) -> None:
    """Embedding and triplet extraction are the slow half; a delete must not wait for them (ARC-01 phase 5)."""

    from app.core.config import get_settings
    from app.services.documents import index_lock
    from app.services.runtime import file_locks

    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks" / "chunks.jsonl"))
    get_settings.cache_clear()
    try:
        monkeypatch.setattr(ingest_module, "index_writes", index_lock.index_writes)
        lock = file_locks._lock_for(index_lock.index_lock_path())
        held: dict[str, bool] = {}

        def embed(collection, texts):
            held["embedding"] = lock.is_locked
            return [[0.0] for _ in texts]

        def extract(text, min_confidence):
            held["triplet extraction"] = lock.is_locked
            return [_Triplet("A", "relates_to", "B")], {"llm": 1}

        def upsert(collection, ids, texts, metadatas, embeddings):
            held["vector write"] = lock.is_locked

        def write_corpus(rows):
            held["corpus write"] = lock.is_locked

        monkeypatch.setattr(ingest_module, "embed_texts", embed)
        monkeypatch.setattr(ingest_module, "extract_graph_triplets_with_diagnostics", extract)
        monkeypatch.setattr(ingest_module, "upsert_texts", upsert)
        monkeypatch.setattr(ingest_module, "write_corpus_records", write_corpus)

        ingest_module.ingest_paths([Path("a.pdf")])
    finally:
        get_settings.cache_clear()

    assert held == {
        "embedding": False,
        "triplet extraction": False,
        "corpus write": True,
        "vector write": True,
    }
    assert not lock.is_locked, "the lock was not released"


def test_refused_vectors_leave_the_corpus_untouched(wiring: _Calls, monkeypatch) -> None:
    """The corpus used to be written first, so a refused vector write left rows naming vectors that never existed."""

    def refuse(*args, **kwargs):
        raise ValueError("Batch size 14208 exceeds maximum batch size 5461")

    monkeypatch.setattr(ingest_module, "upsert_texts", refuse)
    with pytest.raises(ValueError):
        ingest_module.ingest_paths([Path("a.pdf")])
    assert wiring.corpus_written == []


def test_a_failed_corpus_write_removes_the_vectors_it_would_have_described(wiring: _Calls, monkeypatch) -> None:
    removed: list[list[str]] = []

    def disk_full(rows):
        raise OSError("No space left on device")

    monkeypatch.setattr(ingest_module, "write_corpus_records", disk_full)
    monkeypatch.setattr(ingest_module, "delete_documents_by_ids", lambda ids: removed.append(list(ids)))
    with pytest.raises(OSError):
        ingest_module.ingest_paths([Path("a.pdf")])
    assert removed == [["chunk-0"]]
    assert wiring.added, "the vectors were written before the corpus"


def test_an_ingest_tells_the_other_workers_the_corpus_changed(wiring: _Calls, monkeypatch) -> None:
    kinds: list[str] = []
    monkeypatch.setattr(ingest_module, "announce", kinds.append)
    ingest_module.ingest_paths([Path("a.pdf")])
    assert kinds == ["corpus"]
