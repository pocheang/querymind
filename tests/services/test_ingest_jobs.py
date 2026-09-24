"""Ingest and reindex are jobs, and a job outlives the process that accepted it (ARC-01 phase 5).

The ingest queue was a thread pool inside the API process, so a restart during
an ingest left the document `indexing` forever, and every API worker would have
run its own pool and its own folder watcher. In shared mode a job is now an RQ
entry in Redis, run by the one ingest worker; in memory mode the pool stays. In
both, whatever starts the job runner first recovers the documents whose jobs
died with the previous one.

The RQ tests drive a real `SimpleWorker` against fakeredis, running the real job
functions with only the ingest itself stubbed.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import fakeredis
import pytest
from rq import Queue
from rq.job import Job

from app.core.config import get_settings
from app.services.documents.registry import create_document_record, get_document_by_source, list_document_records
from app.services.runtime import ingest_queue
from app.services.runtime.shared_state import SharedStateUnavailable


@pytest.fixture
def data(tmp_path, monkeypatch) -> Path:
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks" / "chunks.jsonl"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def redis_server(monkeypatch):
    """Shared mode, with the queue's Redis replaced by fakeredis."""

    server = fakeredis.FakeRedis()
    monkeypatch.setattr(ingest_queue, "is_shared", lambda: True)
    monkeypatch.setattr(ingest_queue._RQ_CONNECTOR, "client", lambda: server)
    return server


def _document(data: Path, name: str, *, status: str = "pending") -> str:
    source = str(data / "uploads" / name)
    record = create_document_record(
        source=source, filename=name, sha256=name, owner_user_id="alice", visibility="private", agent_class="general"
    )
    if status != "pending":
        from app.services.documents.registry import update_document_record

        update_document_record(record["document_id"], {"status": status})
    return str(record["document_id"])


def _status(document_id: str) -> str:
    return next(r["status"] for r in list_document_records() if r["document_id"] == document_id)


def _run_worker(server) -> None:
    from app.ingest_worker import build_worker

    queue = Queue(ingest_queue.queue_name(), connection=server)
    build_worker(server, queue).work(burst=True)


# ---- shared mode: the queue is Redis ---------------------------------------------------


def test_a_reindex_is_queued_in_redis_once(data, redis_server):
    document_id = _document(data, "a.txt")

    ingest_queue.enqueue_reindex_job(document_id=document_id, user_id="alice")
    ingest_queue.enqueue_reindex_job(document_id=document_id, user_id="alice")

    queue = Queue(ingest_queue.queue_name(), connection=redis_server)
    assert queue.job_ids == [ingest_queue.job_id_for(document_id)]
    assert _status(document_id) == "queued"


def test_the_worker_runs_the_queued_reindex(data, redis_server, monkeypatch):
    document_id = _document(data, "a.txt")
    ran: list[str] = []

    def rebuild(filename, *, source, user_id):
        ran.append(filename)
        from app.services.documents.registry import update_document_by_source

        update_document_by_source(source, {"status": "ready", "stage": "complete"})
        return {"ok": True}

    monkeypatch.setattr(ingest_queue, "rebuild_document_index", rebuild)
    ingest_queue.enqueue_reindex_job(document_id=document_id, user_id="alice")
    _run_worker(redis_server)

    assert ran == ["a.txt"]
    assert _status(document_id) == "ready"


def test_a_job_that_raises_leaves_the_document_failed_with_its_error(data, redis_server, monkeypatch):
    document_id = _document(data, "a.txt")

    def rebuild(filename, *, source, user_id):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr(ingest_queue, "rebuild_document_index", rebuild)
    ingest_queue.enqueue_reindex_job(document_id=document_id, user_id="alice")
    _run_worker(redis_server)

    record = next(r for r in list_document_records() if r["document_id"] == document_id)
    assert (record["status"], record["error"]) == ("failed", "parser exploded")


def test_redis_down_is_a_503_and_leaves_the_status_as_it_was(data, monkeypatch):
    document_id = _document(data, "a.txt", status="ready")
    monkeypatch.setattr(ingest_queue, "is_shared", lambda: True)
    monkeypatch.setattr(ingest_queue._RQ_CONNECTOR, "client", lambda: None)

    with pytest.raises(SharedStateUnavailable):
        ingest_queue.enqueue_reindex_job(document_id=document_id, user_id="alice")
    assert _status(document_id) == "ready"


# ---- recovery ------------------------------------------------------------------------


def test_recovery_requeues_only_what_nothing_is_waiting_to_run(data, redis_server):
    orphan = _document(data, "orphan.txt", status="indexing")
    waiting = _document(data, "waiting.txt", status="queued")
    done = _document(data, "done.txt", status="ready")
    Queue(ingest_queue.queue_name(), connection=redis_server).enqueue(
        "builtins.len", "x", job_id=ingest_queue.job_id_for(waiting)
    )

    recovered = ingest_queue.recover_unfinished_documents()

    assert recovered == [orphan]
    assert _status(done) == "ready"


def test_a_worker_starting_treats_jobs_left_started_as_dead(data, redis_server):
    """The only worker that could have started them is the one starting now."""

    from app.ingest_worker import _abandon_started_jobs

    document_id = _document(data, "a.txt", status="indexing")
    queue = Queue(ingest_queue.queue_name(), connection=redis_server)
    job = Job.create("builtins.len", args=("x",), id=ingest_queue.job_id_for(document_id), connection=redis_server)
    job.save()
    # How RQ 2.x records a running job: one `job_id:execution_id` entry per execution.
    redis_server.zadd(queue.started_job_registry.key, {f"{job.id}:exec-1": time.time() + 3600})

    assert _abandon_started_jobs(queue) == [job.id]
    assert redis_server.zcard(queue.started_job_registry.key) == 0
    assert ingest_queue.recover_unfinished_documents() == [document_id]


def test_memory_mode_recovers_into_the_in_process_pool(data, monkeypatch):
    submitted: list[dict] = []
    monkeypatch.setattr(ingest_queue, "is_shared", lambda: False)
    monkeypatch.setattr(ingest_queue._EXECUTOR, "submit", lambda func, **kwargs: submitted.append(kwargs))
    document_id = _document(data, "a.txt", status="indexing")

    assert ingest_queue.recover_unfinished_documents() == [document_id]
    assert submitted == [{"document_id": document_id, "user_id": "alice"}]


# ---- the API side ----------------------------------------------------------------------


def test_a_reindex_request_answers_202_with_the_document_to_follow(data, monkeypatch):
    from app.api.routes.public import documents as route

    document_id = _document(data, "a.txt", status="ready")
    record = get_document_by_source(str(data / "uploads" / "a.txt"))
    queued: list[str] = []
    monkeypatch.setattr(route, "should_skip_reindex", lambda path: False)
    monkeypatch.setattr(
        route, "enqueue_reindex_job", lambda *, document_id, user_id: queued.append(document_id) or {"status": "queued"}
    )

    response = route._queue_reindex(record, "a.txt", str(data / "uploads" / "a.txt"), "alice")

    assert response.status_code == 202
    assert queued == [document_id]
    assert b'"queued":true' in response.body


def test_an_unchanged_document_is_answered_at_once_without_a_job(data, monkeypatch):
    from app.api.routes.public import documents as route

    _document(data, "a.txt", status="ready")
    record = get_document_by_source(str(data / "uploads" / "a.txt"))
    monkeypatch.setattr(route, "should_skip_reindex", lambda path: True)
    monkeypatch.setattr(route, "enqueue_reindex_job", lambda **_: pytest.fail("queued a job for an unchanged file"))

    response = route._queue_reindex(record, "a.txt", str(data / "uploads" / "a.txt"), "alice")

    assert response.skipped is True


def test_the_api_does_not_watch_folders_in_shared_mode(data, monkeypatch):
    """Every API worker would ingest each new file once; the ingest worker watches instead."""

    import app.api.application.lifespan as lifespan_module

    started: list[str] = []
    monkeypatch.setattr(lifespan_module.threading, "Thread", lambda *a, **k: started.append("thread") or _NoThread())
    monkeypatch.setattr(lifespan_module, "_auto_ingest_thread", None)

    shared = get_settings().model_copy(update={"auto_ingest_enabled": True, "state_backend": "shared"})
    lifespan_module._start_auto_ingest_thread(shared)
    assert started == []

    memory = get_settings().model_copy(update={"auto_ingest_enabled": True, "state_backend": "memory"})
    lifespan_module._start_auto_ingest_thread(memory)
    assert started == ["thread"]


class _NoThread:
    def start(self):
        return None

    def is_alive(self):
        return False


def test_the_worker_refuses_to_start_in_memory_mode(data, monkeypatch, caplog):
    """Refused for the mode, not for a Redis that happens to be absent on this machine."""

    import app.services.runtime.redis_connector as connector
    from app.ingest_worker import main

    monkeypatch.setattr(connector, "probe", lambda url, timeout=3.0: None)
    with caplog.at_level("ERROR", logger="app.ingest_worker"):
        assert main([]) == 2
    assert "STATE_BACKEND=shared" in caplog.text


# ---- the vector store in shared mode ---------------------------------------------------


def test_a_configured_server_is_what_the_store_talks_to(data, monkeypatch):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    from app.retrievers.stores import vector

    client = chromadb.EphemeralClient(settings=ChromaSettings(anonymized_telemetry=False))
    monkeypatch.setenv("CHROMA_SERVER_URL", "http://chroma:8000")
    get_settings.cache_clear()
    monkeypatch.setattr(vector, "chroma_http_client", lambda url: client)
    vector.clear_vector_store_cache()
    try:
        assert vector.get_named_vector_store("phase5_probe")._client is client
    finally:
        vector.clear_vector_store_cache()


@pytest.mark.parametrize("url", ["chroma:8000", "ftp://chroma", "http://"])
def test_a_malformed_server_url_is_refused(url):
    from app.retrievers.stores.vector import chroma_http_client

    with pytest.raises(ValueError, match="CHROMA_SERVER_URL"):
        chroma_http_client(url)


def test_asyncio_is_not_needed_here():
    """The job functions are synchronous: RQ calls them, and they reach no event loop."""

    for name in ("run_ingest_job", "run_reindex_job"):
        assert not asyncio.iscoroutinefunction(getattr(ingest_queue, name))


# ---- the full rebuild is a job too -----------------------------------------------------


def _model_settings_calls(monkeypatch, *, signature_changes: bool) -> list[str]:
    from app.services.models import config_store
    from app.services.runtime import rag_runtime_scope

    calls: list[str] = []
    signatures = iter(["before", "after" if signature_changes else "before"])
    monkeypatch.setattr(config_store, "get_global_model_settings", lambda: {})
    monkeypatch.setattr(config_store, "save_global_model_settings", lambda raw: dict(raw))
    monkeypatch.setattr(rag_runtime_scope, "embedding_settings_signature", lambda settings: next(signatures))
    monkeypatch.setattr(ingest_queue, "enqueue_rebuild_all_job", lambda: calls.append("queued"))
    monkeypatch.setattr(
        "app.services.documents.index_manager.rebuild_all_vector_index",
        lambda: pytest.fail("the save re-embedded the corpus inside the request"),
    )
    return calls


def test_a_changed_embedding_model_queues_the_rebuild_rather_than_running_it(data, monkeypatch):
    from app.services.models.config_store import apply_global_model_settings

    calls = _model_settings_calls(monkeypatch, signature_changes=True)
    saved, rebuild = apply_global_model_settings({"provider": "local"})

    assert rebuild == {"queued": True}
    assert calls == ["queued"]


def test_an_unchanged_embedding_model_queues_nothing(data, monkeypatch):
    from app.services.models.config_store import apply_global_model_settings

    calls = _model_settings_calls(monkeypatch, signature_changes=False)

    assert apply_global_model_settings({"provider": "local"})[1] is None
    assert calls == []


def test_the_admin_is_told_a_rebuild_was_queued(data, monkeypatch):
    from types import SimpleNamespace

    from app.api.routes.admin import settings as route

    monkeypatch.setattr(route, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(route, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(
        route,
        "apply_global_model_settings",
        lambda raw: ({"enabled": 1, "provider": "p", "chat_model": "c"}, {"queued": True}),
    )
    monkeypatch.setattr(
        route,
        "_admin_model_settings_view",
        lambda saved: SimpleNamespace(settings=SimpleNamespace(embedding_reindex_queued=False)),
    )

    class _Req:
        pass

    response = route.admin_save_model_settings(
        SimpleNamespace(model_dump=lambda: {}), _Req(), user={"user_id": "admin"}
    )
    assert response.settings.embedding_reindex_queued is True


def test_the_worker_runs_the_rebuild_and_a_failure_raises_an_alert(data, redis_server, monkeypatch):
    alerts: list[str] = []
    monkeypatch.setattr("app.services.observability.alerting.emit_alert", lambda name, payload: alerts.append(name))

    def rebuild():
        raise RuntimeError("embedding service down")

    monkeypatch.setattr(ingest_queue, "rebuild_all_vector_index", rebuild)
    ingest_queue.enqueue_rebuild_all_job()
    assert Queue(ingest_queue.queue_name(), connection=redis_server).job_ids == ["index-rebuild-all"]

    _run_worker(redis_server)

    assert alerts == ["admin_model_settings_embedding_reindex_failed"]
