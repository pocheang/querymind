"""A fresh process loads its models before the first question needs them.

Measured on the development machine (2026-09-28): a fresh process's first
retrieval took 26-28 s on the vector source, 19.5 s of it loading BGE-M3, against
a 10 s per-source ceiling, so every process answered its first question "no
material found". The reranker's first load (5-8 s) could also overrun and fall
back to lexical scoring. Warm, the same searches take 0.1-0.2 s.

What must hold: the loads run once however many callers arrive together; the
warm-up records what it did and never raises; it runs at startup and after a
reload, never under pytest; it never calls a remote embedding provider; and
/ready reports `warming` without loading a model itself.
"""

from __future__ import annotations

import ast
import threading
import time
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agents.verifier.validation.nli import load_nli_cross_encoder
from app.api.routes.operations import health
from app.retrievers.reranker import _load_cross_encoder
from app.services.models import runtime, warmup
from app.services.models.runtime import _load_local_embedder
from app.services.models.single_flight import single_flight

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture(autouse=True)
def _fresh_state(monkeypatch):
    monkeypatch.setattr(warmup, "_state", warmup._State())


# --- one load, however many callers ------------------------------------------------------


def test_concurrent_first_callers_share_one_load() -> None:
    calls: list[int] = []

    @single_flight
    @lru_cache(maxsize=1)
    def load() -> object:
        calls.append(1)
        time.sleep(0.2)
        return object()

    barrier = threading.Barrier(4)
    results: list[object] = []

    def caller() -> None:
        barrier.wait()
        results.append(load())

    threads = [threading.Thread(target=caller) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert calls == [1], "lru_cache alone let every concurrent miss run the load"
    assert len({id(result) for result in results}) == 1


def test_clearing_the_cache_still_works_through_the_wrapper() -> None:
    calls: list[int] = []

    @single_flight
    @lru_cache(maxsize=1)
    def load() -> int:
        calls.append(1)
        return len(calls)

    assert load() == 1 and load() == 1
    load.cache_clear()
    assert load() == 2


@pytest.mark.parametrize("loader", [_load_local_embedder, _load_cross_encoder, load_nli_cross_encoder])
def test_every_model_loader_is_single_flight(loader) -> None:
    assert hasattr(loader, "__wrapped_loader__"), f"{loader.__name__} can be loaded twice at once"


# --- the warm-up -----------------------------------------------------------------------


def test_each_component_is_recorded_and_a_failure_stops_nothing() -> None:
    def broken() -> str:
        raise RuntimeError("model file damaged")

    warmup.run_warmup((("embedding", lambda: "loaded"), ("reranker", broken), ("validation_nli", lambda: "absent")))

    status = warmup.model_warmup_status()
    assert status["status"] == "ready"
    components = status["components"]
    assert list(components) == ["embedding", "reranker", "validation_nli"]
    assert components["embedding"]["result"] == "loaded" and components["embedding"]["ok"]
    assert components["reranker"]["result"] == "failed: RuntimeError" and not components["reranker"]["ok"]
    assert components["validation_nli"]["result"] == "absent"


def test_it_never_runs_under_pytest() -> None:
    assert warmup.start_model_warmup((("embedding", lambda: pytest.fail("loaded a model in a test")),)) is None
    assert warmup.model_warmup_status()["status"] == "idle"


def test_it_runs_in_the_background_and_only_once_at_a_time(monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    release = threading.Event()

    thread = warmup.start_model_warmup((("embedding", lambda: "loaded" if release.wait(5) else "timeout"),))

    assert thread is not None
    assert warmup.model_warmup_status()["status"] == "warming"
    assert warmup.start_model_warmup() is None, "a second warm-up must not start while one runs"
    release.set()
    thread.join(5)
    assert warmup.model_warmup_status()["status"] == "ready"


def test_a_remote_embedding_backend_is_never_called(monkeypatch) -> None:
    class Remote:
        def embed_query(self, text: str):
            pytest.fail("the warm-up called a remote embedding provider")

    monkeypatch.setattr(runtime, "get_embedding_model", lambda: Remote())

    assert warmup._warm_embedding() == "not local (Remote)"


def test_a_disabled_reranker_is_not_loaded(monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "enable_reranker", False)

    assert warmup._warm_reranker() == "disabled"


# --- where it starts -------------------------------------------------------------------


def _calls(path: Path, function: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == function
    )
    return {c.func.id for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}


def test_startup_starts_it() -> None:
    assert "start_model_warmup" in _calls(APP / "api" / "application" / "lifespan.py", "lifespan")


def test_a_configuration_reload_starts_it_again() -> None:
    """The reload drops the reranker and NLI models; the next question would pay for them."""

    assert "start_model_warmup" in _calls(APP / "api" / "application" / "config_reload.py", "apply_config_reload")


# --- /ready ------------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr(health, "_check_chroma_ready", lambda: {"ok": True, "required": True, "latency_ms": 1})
    app = FastAPI()
    app.include_router(health.router)
    return TestClient(app)


def test_ready_says_warming_while_the_models_load(client) -> None:
    warmup._state.status = "warming"

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "warming"
    assert response.json()["services"]["models"]["status"] == "warming"


def test_ready_is_ready_once_warm(client) -> None:
    warmup._state.status = "ready"

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["services"]["models"]["ok"] is True


def test_ready_loads_no_model_and_calls_no_provider(client, monkeypatch) -> None:
    """It embedded "test" before: a 20 s load on a cold process, a provider call on a remote backend."""

    def forbidden(*_args, **_kwargs):
        pytest.fail("/ready touched the embedding model")

    monkeypatch.setattr(runtime, "get_embedding_model", forbidden)
    warmup._state.status = "ready"

    assert client.get("/ready").status_code == 200


def test_ready_shares_only_the_state_word(client) -> None:
    warmup.run_warmup((("embedding", lambda: "loaded"),))

    models = client.get("/ready").json()["services"]["models"]

    assert "components" not in models and "result" not in str(models)
