"""A worker's caches follow changes other workers make (ARC-01 phase 6).

When one worker changed shared state it cleared its own caches and every other
worker went on serving the old ones: a deleted document stayed retrievable
through another worker's BM25 index or its in-memory retrieval cache, a
configuration reload took effect on one worker in N, and session metadata
edited on one worker was undone by another's stale copy.

Another worker's `announce` is exactly one `INCR` on `qm:gen:<kind>`, so these
tests make that INCR themselves on fakeredis and check what this process does
about it at its next `catch_up`.
"""

from __future__ import annotations

import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.runtime import invalidation
from app.services.runtime.shared_state import SharedStateUnavailable


@pytest.fixture
def redis_server(tmp_path, monkeypatch):
    empty_env = tmp_path / "empty.env"
    empty_env.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty_env))
    monkeypatch.setenv("NACOS_ENABLED", "false")
    get_settings.cache_clear()
    server = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(invalidation, "is_shared", lambda: True)
    monkeypatch.setattr(invalidation, "shared_client", lambda: server)
    invalidation.reset_for_tests()
    yield server
    invalidation.reset_for_tests()
    get_settings.cache_clear()


@pytest.fixture
def cleared(monkeypatch) -> list[str]:
    calls: list[str] = []
    for kind in invalidation.KINDS:
        monkeypatch.setitem(invalidation._HANDLERS, kind, lambda kind=kind: calls.append(kind))
    return calls


def _another_worker_announces(server, kind: str) -> None:
    server.incr(f"qm:gen:{kind}")


# ---- the mechanism ------------------------------------------------------------------


def test_the_first_look_only_records_where_this_process_starts(redis_server, cleared):
    _another_worker_announces(redis_server, "corpus")
    assert invalidation.catch_up() == []
    assert cleared == []
    assert invalidation.generation("corpus") == 1


def test_a_change_another_worker_announced_is_cleared_here_once(redis_server, cleared):
    invalidation.catch_up()
    _another_worker_announces(redis_server, "corpus")

    assert invalidation.catch_up() == ["corpus"]
    assert invalidation.catch_up() == []
    assert cleared == ["corpus"]


def test_each_kind_clears_only_its_own_caches(redis_server, cleared):
    invalidation.catch_up()
    _another_worker_announces(redis_server, "model_settings")

    assert invalidation.catch_up() == ["model_settings"]
    assert cleared == ["model_settings"]


def test_this_process_does_not_clear_again_for_its_own_announcement(redis_server, cleared):
    invalidation.catch_up()
    invalidation.announce("corpus")

    assert redis_server.get("qm:gen:corpus") == "1"
    assert invalidation.catch_up() == []
    assert cleared == []


def test_an_announcement_does_not_swallow_another_workers_change_in_between(redis_server, cleared):
    """Another worker announced at 1, this one at 2: this process never applied 1, so it must still clear."""

    invalidation.catch_up()
    _another_worker_announces(redis_server, "corpus")
    invalidation.announce("corpus")

    assert invalidation.catch_up() == ["corpus"]


def test_an_announcement_redis_did_not_take_is_sent_at_the_next_chance(redis_server, cleared, monkeypatch):
    invalidation.catch_up()

    def unavailable():
        raise SharedStateUnavailable("shared state store (Redis) is unavailable")

    monkeypatch.setattr(invalidation, "shared_client", unavailable)
    invalidation.announce("corpus")  # the change already happened: this must not raise
    assert redis_server.get("qm:gen:corpus") is None

    monkeypatch.setattr(invalidation, "shared_client", lambda: redis_server)
    invalidation.catch_up()
    assert redis_server.get("qm:gen:corpus") == "1"


def test_a_handler_that_fails_is_retried_on_the_next_request(redis_server, monkeypatch):
    attempts: list[int] = []

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("could not reload")

    monkeypatch.setitem(invalidation._HANDLERS, "config", flaky)
    invalidation.catch_up()
    _another_worker_announces(redis_server, "config")

    with pytest.raises(RuntimeError):
        invalidation.catch_up()
    assert invalidation.catch_up() == ["config"]
    assert len(attempts) == 2


def test_nothing_happens_with_one_process(monkeypatch, cleared):
    monkeypatch.setattr(invalidation, "is_shared", lambda: False)
    monkeypatch.setattr(invalidation, "shared_client", lambda: pytest.fail("memory mode reached Redis"))
    invalidation.announce("corpus")
    assert invalidation.catch_up() == []


# ---- what each kind clears ----------------------------------------------------------


def test_a_corpus_change_drops_bm25_and_local_retrieval_results(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr("app.retrievers.bm25_retriever.reset_bm25_cache", lambda: calls.append("bm25"))
    monkeypatch.setattr("app.retrievers.hybrid.caching.drop_local_retrieval_cache", lambda: calls.append("retrieval"))
    invalidation._clear_corpus_caches()
    assert calls == ["bm25", "retrieval"]


def test_a_model_settings_change_drops_models_and_vector_store_handles(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr("app.services.models.runtime.clear_model_caches", lambda: calls.append("models"))
    monkeypatch.setattr("app.retrievers.stores.vector.clear_vector_store_cache", lambda: calls.append("vectors"))
    invalidation._clear_model_caches()
    assert calls == ["models", "vectors"]


def test_a_config_change_runs_the_reload_this_process_registered(redis_server):
    reloaded: list[str] = []
    invalidation.on_config_change(lambda: reloaded.append("reload"))
    invalidation.on_config_change(invalidation._CONFIG_HANDLERS[0])  # registering twice runs once
    invalidation.catch_up()
    _another_worker_announces(redis_server, "config")

    invalidation.catch_up()
    assert reloaded == ["reload"]


# ---- the request path ---------------------------------------------------------------


def _app_with_middleware() -> FastAPI:
    from app.api.transport.middleware import invalidation_middleware

    app = FastAPI()
    app.middleware("http")(invalidation_middleware)

    @app.get("/documents")
    def documents():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


def test_every_request_catches_up_before_it_is_handled(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr("app.services.runtime.shared_state.is_shared", lambda: True)
    monkeypatch.setattr(invalidation, "catch_up", lambda: seen.append("caught up") or [])

    assert TestClient(_app_with_middleware()).get("/documents").status_code == 200
    assert seen == ["caught up"]


def test_redis_down_is_a_503_for_requests_and_not_for_health_probes(monkeypatch):
    def unavailable():
        raise SharedStateUnavailable("shared state store (Redis) is unavailable")

    monkeypatch.setattr("app.services.runtime.shared_state.is_shared", lambda: True)
    monkeypatch.setattr(invalidation, "catch_up", unavailable)
    client = TestClient(_app_with_middleware())

    assert client.get("/documents").status_code == 503
    assert client.get("/health").status_code == 200


def test_the_application_has_the_middleware():
    from app.api.main import app

    assert any(
        getattr(m.kwargs.get("dispatch"), "__name__", "") == "invalidation_middleware" for m in app.user_middleware
    )


# ---- the retrieval cache in shared mode ----------------------------------------------


@pytest.fixture
def shared_cache(monkeypatch):
    from app.retrievers.hybrid import caching

    server = fakeredis.FakeRedis()
    monkeypatch.setattr("app.services.runtime.shared_state.is_shared", lambda: True)
    monkeypatch.setattr(caching, "redis_client", lambda settings: server)
    caching.drop_local_retrieval_cache()
    settings = get_settings().model_copy(update={"retrieval_cache_backend": "memory", "retrieval_cache_enabled": True})
    invalidation.reset_for_tests()
    yield caching, settings, server
    invalidation.reset_for_tests()
    caching.drop_local_retrieval_cache()


def _span(*_args, **_kwargs):
    from contextlib import nullcontext

    return nullcontext()


def test_a_result_cached_before_a_corpus_change_is_not_served_after_it(shared_cache):
    caching, settings, _server = shared_cache
    invalidation._APPLIED["corpus"] = 1
    caching.cache_store("q", [{"id": "deleted-doc"}], {}, settings)
    assert caching.cache_lookup("q", settings, _span)[0] == [{"id": "deleted-doc"}]

    invalidation._APPLIED["corpus"] = 2  # this process caught up to a delete on another worker
    assert caching.cache_lookup("q", settings, _span) is None


def test_shared_mode_keeps_no_per_process_copy(shared_cache, monkeypatch):
    """Even configured as `memory`: nothing tells one worker's memory about another's delete."""

    caching, settings, _server = shared_cache
    invalidation._APPLIED["corpus"] = 1
    caching.cache_store("q", [{"id": "doc"}], {}, settings)
    monkeypatch.setattr(caching, "redis_client", lambda settings: None)  # Redis gone

    assert caching.cache_lookup("q", settings, _span) is None
    assert caching._RETRIEVAL_CACHE is None


def test_nothing_is_cached_before_the_first_look(shared_cache):
    caching, settings, server = shared_cache
    caching.cache_store("q", [{"id": "doc"}], {}, settings)
    assert server.keys("retrieval:*") == []


# ---- session metadata: no per-process copy ---------------------------------------------


def test_metadata_edited_by_one_worker_is_not_undone_by_another(tmp_path):
    """Two services on one database file are two workers' views of the same user's metadata.

    With the old per-process cache, B read the metadata before A's edit, then
    wrote its whole cached copy back when it counted a query: A's tags vanished.
    """

    from app.services.sessions.metadata import MetadataUpdate, SessionMetadata
    from app.services.sessions.metadata_db import SessionMetadataDB

    path = tmp_path / "metadata.db"
    worker_a, worker_b = SessionMetadataDB(db_path=path), SessionMetadataDB(db_path=path)
    worker_a.create(SessionMetadata(session_id="s1"))
    assert worker_b.get("s1").tags == []  # B has looked at it

    worker_a.update("s1", MetadataUpdate(tags=["contracts"]))
    worker_b.update("s1", MetadataUpdate(increment_query_count=True))

    stored = SessionMetadataDB(db_path=path).get("s1")
    assert stored.tags == ["contracts"]
    assert stored.query_count == 1
    assert worker_b.get("s1").tags == ["contracts"]


# ---- every change is announced ---------------------------------------------------------


@pytest.fixture
def announced(monkeypatch) -> list[str]:
    kinds: list[str] = []
    for target in (
        "app.services.documents.ingest.announce",
        "app.services.documents.index_manager.announce",
        "app.services.runtime.invalidation.announce",
        "app.api.application.config_reload.announce",
        "app.api.routes.admin.settings.announce",
    ):
        monkeypatch.setattr(target, kinds.append)
    return kinds


def test_a_delete_announces_a_corpus_change(announced, monkeypatch, tmp_path):
    from app.services.documents import index_manager

    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks" / "chunks.jsonl"))
    get_settings.cache_clear()
    for name in ("_delete_vector_documents", "_reset_bm25", "_reset_retrieval_cache"):
        monkeypatch.setattr(index_manager, name, lambda *a: None)
    monkeypatch.setattr(index_manager, "_delete_triplets_by_sources", lambda sources: 0)
    try:
        index_manager.delete_file_index("report.txt", source="x")
    finally:
        get_settings.cache_clear()
    assert announced == ["corpus"]


def test_a_full_rebuild_announces_a_corpus_change(announced, monkeypatch, tmp_path):
    from app.services.documents import index_manager

    monkeypatch.setenv("CORPUS_STORE_PATH", str(tmp_path / "chunks" / "chunks.jsonl"))
    get_settings.cache_clear()
    monkeypatch.setattr("app.retrievers.stores.vector.reset_vector_store_from_records", lambda records: None)
    monkeypatch.setattr(index_manager, "_reset_bm25", lambda: None)
    monkeypatch.setattr(index_manager, "_reset_retrieval_cache", lambda: None)
    try:
        index_manager.rebuild_all_vector_index()
    finally:
        get_settings.cache_clear()
    assert announced == ["corpus"]


def test_saving_model_settings_announces_them(announced, monkeypatch):
    from app.services.models import config_store
    from app.services.runtime import rag_runtime_scope

    monkeypatch.setattr(config_store, "get_global_model_settings", lambda: {})
    monkeypatch.setattr(config_store, "save_global_model_settings", lambda raw: dict(raw))
    monkeypatch.setattr(rag_runtime_scope, "embedding_settings_signature", lambda settings: "same")
    config_store.apply_global_model_settings({"provider": "local"})
    assert announced == ["model_settings"]


def test_an_admin_reload_announces_a_config_change(announced, monkeypatch):
    from types import SimpleNamespace

    from app.api.routes.admin import settings as route

    monkeypatch.setattr(route, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(route, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(route, "apply_config_reload", get_settings)
    monkeypatch.setattr(route, "get_global_model_settings", lambda: {})
    monkeypatch.setattr(route, "public_global_model_settings", lambda raw: {})
    route.admin_reload_config(SimpleNamespace(), user={"user_id": "admin"})
    assert announced == ["config"]


def test_the_ingest_worker_catches_up_before_every_job(monkeypatch):
    from rq import Queue

    import app.ingest_worker as worker_module

    server = fakeredis.FakeRedis()
    ran: list[str] = []
    monkeypatch.setattr(worker_module, "_catch_up_before_work", lambda: ran.append("caught up"))
    queue = Queue("qm:test-ingest", connection=server)
    queue.enqueue("builtins.len", "abc")
    queue.enqueue("builtins.len", "abcd")
    worker_module.build_worker(server, queue).work(burst=True)
    assert ran == ["caught up", "caught up"]
