"""/metrics with several workers (ARC-01 phase 8): `app/services/runtime/runtime_metrics.py`.

Each scrape used to render the memory of whichever worker took the connection,
so counters jumped between processes and Prometheus read every jump as a reset.
The aggregation is tested with real processes sharing one directory -- the
thing that has to hold is between processes, and a thread shares the module.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from app.services.runtime import runtime_metrics
from app.services.runtime.runtime_metrics import request_kind

ROOT = Path(__file__).resolve().parents[2]


def _samples(text: str) -> dict[tuple[str, tuple[tuple[str, str], ...]], float]:
    return {
        (sample.name, tuple(sorted(sample.labels.items()))): sample.value
        for family in text_string_to_metric_families(text)
        for sample in family.samples
    }


def _run(code: str, directory: Path) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    env.update(PROMETHEUS_MULTIPROC_DIR=str(directory), PYTHONPATH=str(ROOT), PYTHONUTF8="1")
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout


def test_a_scrape_counts_the_requests_of_every_worker(tmp_path):
    for _ in range(3):
        _run(
            """
            from app.services.runtime.runtime_metrics import record_request
            for _ in range(5):
                record_request(200, 0.2, "query")
            """,
            tmp_path,
        )

    exposition = _run(
        """
        from app.services.runtime.runtime_metrics import render
        print(render()[0].decode())
        """,
        tmp_path,
    )
    samples = _samples(exposition)

    assert samples[("http_requests_total", (("kind", "query"), ("status", "200")))] == 15
    assert samples[("http_request_duration_seconds_count", (("kind", "query"),))] == 15


def test_a_dead_workers_open_breaker_is_not_reported(tmp_path):
    """`livemax` is over live processes; a worker that died with a breaker open must drop out."""

    far = time.time() + 3600
    _run(
        f"""
        from app.services.runtime.runtime_metrics import record_circuit_breaker
        record_circuit_breaker("neo4j", {far})
        """,
        tmp_path,
    )

    # The first process has exited. _alive is forced here because on Windows the
    # real check cannot probe a pid without killing it (see runtime_metrics._alive).
    exposition = _run(
        """
        import os
        from app.services.runtime import runtime_metrics
        runtime_metrics._alive = lambda pid: pid == os.getpid()
        print(runtime_metrics.render()[0].decode())
        """,
        tmp_path,
    )

    open_until = [
        value
        for (name, labels), value in _samples(exposition).items()
        if name == "circuit_breaker_open_until_seconds" and ("breaker", "neo4j") in labels
    ]
    assert not open_until or max(open_until) < time.time()


def test_a_live_workers_open_breaker_is_reported(tmp_path):
    far = time.time() + 3600
    exposition = _run(
        f"""
        from app.services.runtime.runtime_metrics import record_circuit_breaker, render
        record_circuit_breaker("neo4j", {far})
        print(render()[0].decode())
        """,
        tmp_path,
    )

    assert _samples(exposition)[("circuit_breaker_open_until_seconds", (("breaker", "neo4j"),))] == pytest.approx(far)


@pytest.mark.skipif(os.name == "nt", reason="os.kill(pid, 0) terminates the process on Windows")
def test_liveness_tells_a_finished_process_from_a_running_one():
    finished = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)

    assert runtime_metrics._alive(os.getpid())
    assert not runtime_metrics._alive(int(finished.stdout))


def test_the_middleware_records_into_what_metrics_exports():
    """It used to write to an instance of its own that /metrics never rendered."""

    from app.api.transport.middleware import request_timing_middleware

    app = FastAPI()
    app.middleware("http")(request_timing_middleware)

    @app.post("/api/advanced-rag/query")
    def query():
        return {"ok": True}

    key = ("http_requests_total", (("kind", "query"), ("status", "200")))
    before = _samples(runtime_metrics.render()[0].decode()).get(key, 0.0)
    TestClient(app).post("/api/advanced-rag/query")

    assert _samples(runtime_metrics.render()[0].decode())[key] == before + 1


@pytest.mark.parametrize(
    ("method", "path", "kind"),
    [
        ("POST", "/api/advanced-rag/query", "query"),
        ("GET", "/api/advanced-rag/query", "other"),
        ("GET", "/api/v1/orchestration/executions/abc/events", "stream"),
        ("GET", "/agent-tracking/stream/abc", "stream"),
        ("GET", "/health", "other"),
        ("GET", "/api/v1/orchestration/executions/abc", "other"),
    ],
)
def test_requests_are_classified_into_three_kinds(method, path, kind):
    assert request_kind(method, path) == kind


def test_a_failing_metric_write_does_not_fail_the_caller(monkeypatch):
    class Broken:
        def labels(self, **_):
            raise OSError("no space left on device")

    monkeypatch.setattr(runtime_metrics, "CIRCUIT_BREAKER_OPEN_UNTIL", Broken())

    runtime_metrics.record_circuit_breaker("neo4j", 1.0)  # must not raise


def test_the_breaker_publishes_when_it_opens_and_when_it_closes(monkeypatch):
    from app.services.runtime import resilience

    recorded: list[tuple[str, float]] = []
    monkeypatch.setattr(resilience, "record_circuit_breaker", lambda name, until: recorded.append((name, until)))
    monkeypatch.setitem(resilience._BREAKERS, "probe-test", resilience._BreakerState())

    def fail():
        raise RuntimeError("down")

    for _ in range(5):
        with pytest.raises(RuntimeError):
            resilience.call_with_circuit_breaker("probe-test", fail)
    assert recorded
    assert recorded[-1][1] > time.time()

    resilience._BREAKERS["probe-test"].opened_until = time.time() - 1  # cooldown over
    assert resilience.call_with_circuit_breaker("probe-test", lambda: "ok") == "ok"
    assert recorded[-1] == ("probe-test", 0.0)


def test_a_failing_metric_store_does_not_reach_a_breaker_call(monkeypatch):
    """Telemetry is observer-only: the breaker's success path records a metric."""

    from app.services.runtime import resilience

    class Broken:
        def labels(self, **_):
            raise OSError("no space left on device")

    monkeypatch.setattr(runtime_metrics, "CIRCUIT_BREAKER_OPEN_UNTIL", Broken())
    # opened long ago: the call runs, closes the breaker, and records that.
    monkeypatch.setitem(resilience._BREAKERS, "probe-ok", resilience._BreakerState(fails=2, opened_until=1.0))

    assert resilience.call_with_circuit_breaker("probe-ok", lambda: "ok") == "ok"
    assert resilience._BREAKERS["probe-ok"].opened_until == 0.0
