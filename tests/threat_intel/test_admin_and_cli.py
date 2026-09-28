"""The admin endpoints and the CLI: who may sync, what a sync request does, and which paths the CLI will read."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies as api_dependencies
from app.api.routes.admin import threat_intel as route
from app.services.security.audit_actions import AuditAction
from app.services.threat_intel.store import ThreatIntelStore

ADMIN = {"X-Test-User": "ops-admin", "X-Test-User-Id": "ops-admin", "X-Test-Role": "admin"}
VIEWER = {"X-Test-User": "alice", "X-Test-User-Id": "alice", "X-Test-Role": "viewer"}


class _ImmediateQueue:
    def __init__(self, accept: bool = True) -> None:
        self.accept = accept

    def submit(self, fn, *args, **kwargs) -> bool:
        if self.accept:
            fn(*args, **kwargs)
        return self.accept


@pytest.fixture
def client(tmp_path, monkeypatch):
    from app.api import main

    store = ThreatIntelStore(tmp_path / "ti.db")
    monkeypatch.setattr(route, "get_threat_intel_store", lambda: store)
    synced: list[str] = []
    monkeypatch.setattr(
        route,
        "sync_source",
        lambda source, store, proxy=None: synced.append(source) or SimpleNamespace(status="succeeded"),
    )
    queue = _ImmediateQueue()
    monkeypatch.setattr(api_dependencies, "get_query_runtime", lambda: SimpleNamespace(shadow_queue=queue))
    audits: list[dict] = []
    monkeypatch.setattr(route, "_audit", lambda request, **kwargs: audits.append(kwargs))
    test_client = TestClient(main.app)
    test_client.synced, test_client.audits, test_client.queue = synced, audits, queue  # type: ignore[attr-defined]
    return test_client


def test_status_reports_every_source(client):
    response = client.get("/admin/threat-intel/status", headers=ADMIN)

    assert response.status_code == 200
    sources = {row["source"]: row for row in response.json()["sources"]}
    assert set(sources) == {"nvd", "kev", "epss", "attack"}
    assert sources["kev"]["state"] == "empty" and sources["kev"]["stale_after_days"] >= 1


def test_a_sync_is_accepted_queued_and_audited(client):
    response = client.post("/admin/threat-intel/sync", json={"source": "kev"}, headers=ADMIN)

    assert response.status_code == 202
    assert client.synced == ["kev"]
    (audit,) = client.audits
    assert audit["action"] == AuditAction.ADMIN_THREAT_INTEL_SYNC and audit["detail"] == "sources=kev"


def test_all_means_every_source_in_order(client):
    client.post("/admin/threat-intel/sync", json={"source": "all"}, headers=ADMIN)

    assert client.synced == ["nvd", "kev", "epss", "attack"]


def test_an_unknown_source_is_rejected_before_anything_runs(client):
    response = client.post("/admin/threat-intel/sync", json={"source": "osv"}, headers=ADMIN)

    assert response.status_code == 422
    assert client.synced == []


def test_a_full_queue_is_a_503_not_a_silent_drop(client):
    client.queue.accept = False

    response = client.post("/admin/threat-intel/sync", json={"source": "kev"}, headers=ADMIN)

    assert response.status_code == 503
    assert client.audits == []


@pytest.mark.parametrize(
    ("method", "path"), [("get", "/admin/threat-intel/status"), ("post", "/admin/threat-intel/sync")]
)
def test_a_non_admin_is_refused(client, method, path):
    response = getattr(client, method)(path, headers=VIEWER, **({"json": {}} if method == "post" else {}))

    assert response.status_code == 403
    assert client.synced == []


# --- the CLI ----------------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync_threat_intel.py"


def _cli():
    spec = importlib.util.spec_from_file_location("sync_threat_intel", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_an_import_directory_outside_the_repository_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="must be inside the repository"):
        _cli().import_dir(str(tmp_path))


def test_a_path_that_climbs_out_after_normalising_is_refused():
    cli = _cli()

    with pytest.raises(SystemExit, match="must be inside the repository"):
        cli.import_dir(str(cli.REPO_ROOT / "tests" / ".." / ".." / "elsewhere"))


def test_a_symlink_inside_the_repository_pointing_out_is_refused(tmp_path):
    """The case a `..` substring check cannot see: resolve first, then contain."""

    cli = _cli()
    link = cli.REPO_ROOT / "data" / f"ti-link-{tmp_path.name}"
    link.parent.mkdir(exist_ok=True)
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks need a privilege this machine does not grant")
    try:
        with pytest.raises(SystemExit, match="must be inside the repository"):
            cli.import_dir(str(link))
    finally:
        link.unlink()


def test_an_import_directory_inside_the_repository_is_accepted():
    cli = _cli()

    assert cli.import_dir("tests/fixtures/threat_intel") == (cli.REPO_ROOT / "tests" / "fixtures" / "threat_intel")


def test_a_missing_directory_is_a_clear_error():
    with pytest.raises(SystemExit, match="not a directory"):
        _cli().import_dir("tests/fixtures/no-such-dir")
