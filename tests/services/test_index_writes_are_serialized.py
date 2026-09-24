"""Writes to the document index are serialized across processes (ARC-01 phase 5, BUG-05).

`chunks.jsonl` and `parents.jsonl` were rewritten by truncating the file first,
with no lock, and `documents.jsonl` behind a `threading` lock. So two ingests --
even the two threads of one process's ingest pool -- each wrote back the corpus
they had read and one document's chunks were lost, and a reader could open the
file mid-rewrite. One cross-process `FileLock` now guards every write to the
index, the files are replaced atomically, and a request that cannot get the lock
in a few seconds answers 503 rather than holding a worker thread.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.retrievers.stores.corpus import read_corpus_records, write_corpus_records
from app.services.documents import index_manager
from app.services.documents import ingest as ingest_module
from app.services.documents.index_lock import index_writes
from app.services.documents.registry import create_document_record, get_document_by_source
from app.services.runtime.file_locks import LockBusy

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def data(tmp_path, monkeypatch) -> Path:
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks" / "chunks.jsonl"))
    monkeypatch.setenv("PARENT_STORE_PATH", str(tmp_path / "chunks" / "parents.jsonl"))
    monkeypatch.setenv("INDEX_LOCK_REQUEST_TIMEOUT_SECONDS", "0.5")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _prepared(document: str) -> ingest_module.PreparedIngest:
    record = {"id": f"chunk-{document}", "text": document, "metadata": {"source": document}}
    return ingest_module.PreparedIngest(
        docs=[], parsed_documents=[], chunks=[], parent_records=[], records=[record], chunk_embeddings=[]
    )


def test_two_ingests_committing_at_once_keep_both_documents(data, monkeypatch):
    """The lost update, made certain: each commit sleeps between reading and writing the corpus."""

    real_read = ingest_module.read_corpus_records

    def slow_read():
        rows = real_read()
        time.sleep(0.3)
        return rows

    monkeypatch.setattr(ingest_module, "read_corpus_records", slow_read)
    monkeypatch.setattr(ingest_module, "prepare_ingest", lambda paths, *a, **k: _prepared(paths[0].name))
    monkeypatch.setattr(ingest_module, "upsert_texts", lambda *a, **k: None)
    monkeypatch.setattr(ingest_module, "clear_retrieval_cache", lambda: None)
    monkeypatch.setattr(ingest_module, "reset_bm25_cache", lambda: None)

    threads = [threading.Thread(target=ingest_module.ingest_paths, args=([Path(name)],)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(row["id"] for row in read_corpus_records()) == ["chunk-a", "chunk-b"]


def test_a_rewrite_that_fails_halfway_leaves_the_previous_file_whole(data):
    write_corpus_records([{"id": "old-1"}, {"id": "old-2"}])

    def rows_then_failure():
        yield {"id": "new-1"}
        yield {"id": "new-2"}
        raise RuntimeError("disk full")

    with pytest.raises(RuntimeError):
        write_corpus_records(rows_then_failure())

    assert [row["id"] for row in read_corpus_records()] == ["old-1", "old-2"]
    assert not list((data / "chunks").glob(".chunks.jsonl.*")), "the temporary file was left behind"


def test_two_processes_updating_the_registry_lose_no_update(data):
    """Each process increments its own document's counter; the other must not overwrite it with a stale copy."""

    sources = [str(data / "uploads" / f"{name}.txt") for name in ("a", "b")]
    for source in sources:
        create_document_record(
            source=source,
            filename=Path(source).name,
            sha256=source,
            owner_user_id="u",
            visibility="private",
            agent_class="general",
        )
    child = (
        "import sys\n"
        "from app.services.documents.registry import get_document_by_source, update_document_by_source\n"
        "source = sys.argv[1]\n"
        "for _ in range(25):\n"
        "    count = int(get_document_by_source(source)['chunks_indexed'])\n"
        "    update_document_by_source(source, {'chunks_indexed': count + 1})\n"
    )
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    workers = [subprocess.Popen([sys.executable, "-c", child, source], cwd=REPO_ROOT, env=env) for source in sources]
    assert [worker.wait(timeout=120) for worker in workers] == [0, 0]

    assert [get_document_by_source(source)["chunks_indexed"] for source in sources] == [25, 25]


def _hold_the_index_lock(seconds: float) -> threading.Thread:
    """Another writer: a thread has its own lock handle, so it contends like another process."""

    taken = threading.Event()

    def hold():
        with index_writes():
            taken.set()
            time.sleep(seconds)

    holder = threading.Thread(target=hold)
    holder.start()
    assert taken.wait(10)
    return holder


def test_a_delete_that_cannot_get_the_lock_gives_up_and_changes_nothing(data):
    source = str(data / "uploads" / "report.txt")
    create_document_record(
        source=source,
        filename="report.txt",
        sha256="x",
        owner_user_id="u",
        visibility="private",
        agent_class="general",
    )
    write_corpus_records([{"id": "chunk-1", "text": "t", "metadata": {"source": source, "filename": "report.txt"}}])

    holder = _hold_the_index_lock(3.0)
    started = time.perf_counter()
    try:
        with pytest.raises(LockBusy):
            index_manager.delete_document_index("report.txt", source=source, remove_physical_file=False)
        assert time.perf_counter() - started < 2.5, "the request waited for the writer instead of giving up"
    finally:
        holder.join()
    assert [row["id"] for row in read_corpus_records()] == ["chunk-1"]


def test_the_upload_preclean_also_gives_up_rather_than_waiting(data):
    holder = _hold_the_index_lock(3.0)
    try:
        with pytest.raises(LockBusy):
            index_manager.prepare_uploaded_document_indexes([data / "uploads" / "report.txt"])
    finally:
        holder.join()


def test_lock_busy_is_a_503_with_retry_after(data):
    from app.api.main import app

    handler = app.exception_handlers[LockBusy]
    response = asyncio.run(handler(None, LockBusy("index.lock is held by another writer")))

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert b"INDEX_BUSY" in response.body


def test_the_upload_route_lets_lock_busy_through_instead_of_a_500(data, monkeypatch):
    """The route turns any pre-clean failure into 500; a busy index is not a failure of this service."""

    from app.api.routes.public import documents as route
    from app.services.documents.dedup import StoredUpload, UploadStorageResult

    upload = StoredUpload(filename="a.txt", path=data / "a.txt", sha256="x", agent_class="general", parser_profile={})
    stored = UploadStorageResult(
        saved_uploads=[upload],
        skipped_files=[],
        duplicate_files=[],
        reused_document_ids=[],
        visibility_applied="private",
    )
    loops: list[bool] = []

    def busy(paths):
        try:
            asyncio.get_running_loop()
            loops.append(True)
        except RuntimeError:
            loops.append(False)
        raise LockBusy("index.lock is held by another writer")

    async def store(**_kwargs):
        return stored

    monkeypatch.setattr(route, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(route.upload_limiter, "try_acquire", lambda key: True)
    monkeypatch.setattr(route, "_approved_upload_visibility", lambda visibility, user: ("private", False))
    monkeypatch.setattr(route, "store_uploaded_files", store)
    monkeypatch.setattr(route, "prepare_uploaded_document_indexes", busy)
    monkeypatch.setattr(route, "_audit", lambda *a, **k: None)

    class _Req:
        client = None
        headers: dict = {}

    with pytest.raises(LockBusy):
        asyncio.run(route.upload_files(_Req(), files=[], visibility="private", user={"user_id": "u"}))
    assert loops == [False], "the pre-clean ran on the event loop"


@pytest.mark.parametrize("writer", ["delete_file_index", "rebuild_all_vector_index"])
def test_a_writer_outside_a_request_waits_for_the_lock_rather_than_writing_through_it(data, monkeypatch, writer):
    """The worker's own deletes and the full rebuild wait; only a request gives up."""

    monkeypatch.setattr("app.retrievers.stores.vector.reset_vector_store_from_records", lambda records: None)
    monkeypatch.setattr(index_manager, "_delete_vector_documents", lambda ids: None)
    monkeypatch.setattr(index_manager, "_reset_bm25", lambda: None)
    monkeypatch.setattr(index_manager, "_reset_retrieval_cache", lambda: None)
    monkeypatch.setattr(index_manager, "_delete_triplets_by_sources", lambda sources: 0)
    monkeypatch.setattr(index_manager, "_delete_tables_by_sources", lambda sources: 0)
    call = {
        "delete_file_index": lambda: index_manager.delete_file_index("report.txt", source="x"),
        "rebuild_all_vector_index": index_manager.rebuild_all_vector_index,
    }[writer]

    holder = _hold_the_index_lock(1.0)
    started = time.perf_counter()
    try:
        call()
        waited = time.perf_counter() - started
    finally:
        holder.join()
    assert waited >= 0.7, f"{writer} wrote while another writer held the index lock"


@pytest.mark.parametrize("has_chunks", [True, False])
def test_deleting_a_document_removes_its_images_and_tables_from_the_multimodal_index(data, monkeypatch, has_chunks):
    """Its chunks and SQL tables went; its image and table vectors used to stay searchable.

    Without chunks too: an ingest that failed after writing its images leaves
    no corpus row to learn the source from, and the explicit source must do.
    """

    from app.retrievers.stores import vector
    from app.services.multimodal.image_processor import ImageProcessor
    from app.services.multimodal.models import ImageContent, TableContent
    from app.services.multimodal.table_extractor import TableExtractor

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(data / "chroma"))
    monkeypatch.setenv("MODEL_BACKEND", "local")
    get_settings.cache_clear()
    vector.clear_vector_store_cache()
    mine, other = str(data / "uploads" / "report.txt"), str(data / "uploads" / "keep.txt")
    try:
        for source, tag in ((mine, "mine"), (other, "other")):
            ImageProcessor().index_image(
                ImageContent(
                    image_id=f"img-{tag}",
                    doc_id=tag,
                    page_number=1,
                    image_data=b"",
                    description=f"diagram {tag}",
                    metadata={"source": source},
                )
            )
            TableExtractor().index_table(
                TableContent(
                    table_id=f"tbl-{tag}",
                    doc_id=tag,
                    page_number=1,
                    headers=["a"],
                    rows=[["1"]],
                    summary=f"table {tag}",
                    metadata={"source": source},
                )
            )
        rows = [{"id": "chunk-1", "text": "t", "metadata": {"source": mine, "filename": "report.txt"}}]
        write_corpus_records(rows if has_chunks else [])
        monkeypatch.setattr(index_manager, "_delete_vector_documents", lambda ids: None)
        monkeypatch.setattr(index_manager, "_delete_triplets_by_sources", lambda sources: 0)

        index_manager.delete_file_index("report.txt", source=mine)

        for collection, prefix in (("image_descriptions", "img"), ("table_summaries", "tbl")):
            left = vector.get_named_vector_store(collection)._collection.get()["ids"]
            assert left == [f"{prefix}-other"], collection
    finally:
        vector.clear_vector_store_cache()
