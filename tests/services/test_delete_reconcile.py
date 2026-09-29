"""A delete that a store refuses is reported and retryable, and drift is found (ARC-03)."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.retrievers.stores.corpus import write_corpus_records
from app.services.documents import index_manager, reconcile
from app.services.documents.registry import create_document_record, get_document_by_source


@pytest.fixture
def data(tmp_path, monkeypatch):
    env = tmp_path / "empty.env"
    env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks" / "chunks.jsonl"))
    monkeypatch.setenv("PARENT_STORE_PATH", str(tmp_path / "chunks" / "parents.jsonl"))
    monkeypatch.setenv("DOCUMENT_REGISTRY_PATH", str(tmp_path / "documents.jsonl"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def stores(monkeypatch):
    """Stand-ins for the vector / table / multimodal stores, recording what is deleted."""
    calls = {"vectors": [], "tables": [], "multimodal": []}
    monkeypatch.setattr(index_manager, "_delete_vector_documents", lambda ids: calls["vectors"].append(ids))
    monkeypatch.setattr(index_manager, "_reset_bm25", lambda: None)
    monkeypatch.setattr(index_manager, "_reset_retrieval_cache", lambda: None)
    monkeypatch.setattr(index_manager, "_delete_triplets_by_sources", lambda sources, failures=None: 0)
    monkeypatch.setattr(index_manager, "announce", lambda *_: None)
    return calls


def _index(data, name="a.txt"):
    path = data / name
    path.write_text("x", encoding="utf-8")
    write_corpus_records([{"id": "c1", "text": "x", "metadata": {"source": str(path)}}])
    create_document_record(
        source=str(path),
        filename=name,
        sha256="0" * 64,
        owner_user_id="u",
        visibility="private",
        agent_class="general",
        tenant_id="t",
    )
    return path


def test_a_store_that_refuses_the_delete_keeps_the_file_and_the_registry_row(data, stores, monkeypatch):
    path = _index(data)

    def refuse(sources, failures=None):
        failures.append("tables")
        return 0

    monkeypatch.setattr(index_manager, "_delete_tables_by_sources", refuse)
    monkeypatch.setattr(index_manager, "_delete_multimodal_by_sources", lambda s, failures=None: None)

    result = index_manager.delete_document_index(path.name, source=str(path), remove_physical_file=True)

    assert result["failed_steps"] == ["tables"]
    assert path.exists(), "the upload is what a retry needs to find the document again"
    row = get_document_by_source(str(path))
    assert row is not None and row["status"] == "delete_failed"
    assert "tables" in row["error"]


def test_a_retry_after_the_store_recovers_finishes_the_delete(data, stores, monkeypatch):
    path = _index(data)
    monkeypatch.setattr(index_manager, "_delete_multimodal_by_sources", lambda s, failures=None: None)
    monkeypatch.setattr(index_manager, "_delete_tables_by_sources", lambda s, failures=None: 0)

    result = index_manager.delete_document_index(path.name, source=str(path), remove_physical_file=True)

    assert result["failed_steps"] == []
    assert not path.exists()
    assert get_document_by_source(str(path)) is None


def _fake_stores(monkeypatch, *, vectors, tables, images, graph=()):
    monkeypatch.setattr(reconcile, "_graph_sources", lambda: set(graph))
    monkeypatch.setattr(reconcile, "_vector_ids", lambda: set(vectors))
    monkeypatch.setattr(reconcile, "_table_sources", lambda: set(tables))
    monkeypatch.setattr(
        reconcile, "_collection_sources", lambda name: set(images) if name == "image_descriptions" else set()
    )


def test_reconcile_reports_orphans_without_touching_them(data, monkeypatch):
    path = _index(data)
    _fake_stores(monkeypatch, vectors={"c1", "ghost"}, tables={"gone.xlsx"}, images={"gone.png"})
    deleted = []
    monkeypatch.setattr(reconcile, "_delete_vector_documents", deleted.append)

    report = reconcile.reconcile_index()

    assert report.orphan_vector_ids == ["ghost"]
    assert report.orphan_table_sources == ["gone.xlsx"]
    assert report.orphan_multimodal_sources["image_descriptions"] == ["gone.png"]
    assert not report.clean
    assert deleted == [] and path.exists()


def test_a_consistent_index_is_clean(data, monkeypatch):
    _index(data)
    _fake_stores(monkeypatch, vectors={"c1"}, tables=set(), images=set())
    assert reconcile.reconcile_index().clean


def test_repair_removes_only_derived_orphans(data, monkeypatch):
    path = _index(data)
    _fake_stores(monkeypatch, vectors={"c1", "ghost"}, tables={"gone.xlsx"}, images=set())
    removed = {}
    monkeypatch.setattr(reconcile, "_delete_vector_documents", lambda ids: removed.setdefault("vectors", ids))
    monkeypatch.setattr(reconcile, "_delete_tables_by_sources", lambda s: removed.setdefault("tables", s) and 1)
    monkeypatch.setattr(reconcile, "_delete_multimodal_by_sources", lambda s: None)

    report = reconcile.reconcile_index(repair=True)

    assert removed["vectors"] == ["ghost"] and removed["tables"] == ["gone.xlsx"]
    assert report.repaired["vectors"] == 1
    assert path.exists() and get_document_by_source(str(path)) is not None


def test_an_unreadable_store_is_skipped_not_reported_empty(data, monkeypatch):
    _index(data)
    _fake_stores(monkeypatch, vectors=set(), tables=set(), images=set())

    def down():
        raise ConnectionError("chroma down")

    monkeypatch.setattr(reconcile, "_vector_ids", down)
    report = reconcile.reconcile_index()
    assert "vectors" in report.skipped
    assert report.corpus_ids_without_vector == []


def test_a_graph_source_with_no_chunks_is_an_orphan_but_a_file_name_of_a_live_one_is_not(data, monkeypatch):
    path = _index(data)
    _fake_stores(monkeypatch, vectors={"c1"}, tables=set(), images=set(), graph={path.name, "gone.txt", str(path)})

    report = reconcile.reconcile_index()

    assert report.orphan_graph_sources == ["gone.txt"]


def test_repair_removes_orphan_graph_sources(data, monkeypatch):
    _index(data)
    _fake_stores(monkeypatch, vectors={"c1"}, tables=set(), images=set(), graph={"gone.txt"})
    seen = []
    monkeypatch.setattr(
        reconcile, "_delete_triplets_by_sources", lambda sources, failures=None: seen.extend(sources) or 3
    )

    report = reconcile.reconcile_index(repair=True)

    assert seen == ["gone.txt"] and report.repaired["graph_relations"] == 3


def test_an_unreachable_graph_is_skipped_not_reported_clean_of_orphans(data, monkeypatch):
    _index(data)
    _fake_stores(monkeypatch, vectors={"c1"}, tables=set(), images=set())

    def down():
        raise ConnectionError("neo4j down")

    monkeypatch.setattr(reconcile, "_graph_sources", down)
    report = reconcile.reconcile_index()
    assert "graph" in report.skipped and report.orphan_graph_sources == []


def test_the_schedule_is_off_by_default_and_runs_a_pass_when_on(data, monkeypatch):
    import threading

    class Cfg:
        index_reconcile_interval_seconds = 0.0
        index_reconcile_repair = False

    assert reconcile.start_scheduled(Cfg()) is None

    ran = threading.Event()
    monkeypatch.setattr(reconcile, "reconcile_index", lambda repair=False: ran.set() or reconcile.ReconcileReport())
    Cfg.index_reconcile_interval_seconds = 0.01
    stop = reconcile.start_scheduled(Cfg())
    try:
        assert ran.wait(2.0)
    finally:
        stop.set()
