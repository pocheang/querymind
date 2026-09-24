"""The shared-state compose overlay describes a deployment the application will start (ARC-01 phase 5).

`validate_shared_state_backends` refuses STATE_BACKEND=shared without sqlite
history, database metadata and a Chroma server. The overlay is the one place a
deployment gets those settings, so a key missing there is a stack that builds,
starts its containers, and then has a backend refusing to boot.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from app.core.config import Settings, validate_shared_state_backends

OVERLAY = Path("deploy/compose/compose.shared-state.yaml")
BASE = Path("deploy/compose/compose.yaml")


def _services() -> dict:
    return yaml.safe_load(OVERLAY.read_text(encoding="utf-8"))["services"]


def test_every_service_in_the_overlay_satisfies_the_startup_rule():
    for name in ("backend", "ingest-worker"):
        environment = {k: str(v) for k, v in _services()[name]["environment"].items()}
        validate_shared_state_backends(Settings(**environment))


def test_the_worker_shares_the_backends_index_files():
    """The registry, corpus, uploads and the index lock must be one set of files for both."""

    backend_volumes = set(yaml.safe_load(BASE.read_text(encoding="utf-8"))["services"]["backend"]["volumes"])
    worker_volumes = set(_services()["ingest-worker"]["volumes"])
    assert {"chunks_data:/app/data/chunks", "app_data:/app/data"} <= backend_volumes & worker_volumes


def test_there_is_exactly_one_ingest_worker():
    worker = _services()["ingest-worker"]
    assert worker["command"] == ["python", "-m", "app.ingest_worker"]
    assert worker["deploy"]["replicas"] == 1


def test_the_chroma_server_matches_the_locked_client():
    import re

    locked = re.search(r'name = "chromadb"\nversion = "([^"]+)"', Path("uv.lock").read_text(encoding="utf-8"))
    assert locked, "chromadb is not in uv.lock"
    assert _services()["chroma"]["image"] == f"chromadb/chroma:{locked.group(1)}"
