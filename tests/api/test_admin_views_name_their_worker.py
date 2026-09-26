"""Admin views built from one worker's memory say which worker (ARC-01 phase 8).

With several workers, the runtime panel, the overview's request figures, the
captured system log and the circuit breakers are each one process's slice, and
which one depends on where the request landed. Unlabelled, a slice reads as the
whole deployment. /metrics, by contrast, aggregates -- and probes only the
deployment's own infrastructure.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from app.api import main
from app.api.routes.admin import ops as ops_route
from app.api.routes.operations import health as health_route
from app.api.routes.operations import metrics_collectors

ADMIN = {"X-Test-User": "ops-admin", "X-Test-User-Id": "ops-admin", "X-Test-Role": "admin"}


@pytest.fixture
def client(monkeypatch):
    # No network in these tests: the probes answer from here.
    monkeypatch.setattr(ops_route, "_service_health_snapshot", lambda: {})
    monkeypatch.setattr(ops_route, "_check_ollama_ready", lambda: {"ok": True, "required": False})
    monkeypatch.setattr(ops_route, "_check_chroma_ready", lambda: {"ok": True, "required": True})
    for name in health_route._SCRAPED_DEPENDENCIES:
        monkeypatch.setitem(
            health_route._SCRAPED_DEPENDENCIES, name, lambda name=name: {"ok": name != "neo4j", "required": True}
        )
    metrics_collectors.reset_for_tests()
    yield TestClient(main.app)
    metrics_collectors.reset_for_tests()


@pytest.mark.parametrize(
    "path", ["/admin/ops/runtime", "/admin/ops/overview", "/admin/system-logs", "/circuit-breakers"]
)
def test_a_per_worker_view_names_the_worker_that_answered(client, path):
    response = client.get(path, headers=ADMIN)

    assert response.status_code == 200, response.text
    assert response.json()["worker"]["pid"] == os.getpid()


def test_the_overview_says_which_of_its_parts_are_per_worker(client):
    assert client.get("/admin/ops/overview", headers=ADMIN).json()["worker_scoped"] == ["requests", "diagnostics"]


def test_the_csv_export_names_the_worker_behind_its_request_figures(client):
    body = client.get("/admin/ops/export.csv", headers=ADMIN).text

    assert f"meta,worker_pid,{os.getpid()}" in body.replace("\r\n", "\n")


def test_metrics_exports_requests_and_dependency_reachability(client):
    client.get("/health")

    body = client.get("/metrics").text

    assert 'http_requests_total{kind="other",status="200"}' in body
    assert 'dependency_up{dependency="neo4j"} 0.0' in body
    assert 'dependency_up{dependency="redis"} 1.0' in body
    assert "query_guard_inflight" in body


def test_metrics_never_probes_an_external_model_provider():
    """/metrics is unauthenticated and scraped every few seconds; provider probes cost money."""

    assert set(health_route._SCRAPED_DEPENDENCIES) == {"redis", "chroma", "neo4j", "ollama"}


def test_dependency_probes_are_reused_within_the_cache_window():
    calls: list[str] = []
    metrics_collectors.reset_for_tests()
    checks = {"redis": lambda: calls.append("redis") or {"ok": True, "required": True}}

    first = asyncio.run(metrics_collectors.probe_dependencies(checks))
    second = asyncio.run(metrics_collectors.probe_dependencies(checks))
    metrics_collectors.reset_for_tests()

    assert calls == ["redis"]
    assert first == second == {"redis": {"ok": True, "required": True}}
