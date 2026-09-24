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


# What `chromadb/chroma:1.5.9` has on its PATH, measured with `command -v` in the
# image on 2026-09-24. Re-measure when the image version changes: the version
# test above forces that change to be made here too.
_CHROMA_IMAGE_TOOLS = {"bash"}
_CHROMA_IMAGE_LACKS = {"wget", "curl", "python3", "nc"}


def test_the_chroma_healthcheck_uses_a_tool_the_image_has():
    """A probe naming a missing tool never passes, and every `service_healthy` dependent waits forever.

    The first version of this overlay probed with wget, which the image does not ship.
    """

    chroma = _services()["chroma"]
    test = chroma["healthcheck"]["test"]
    assert test[0] == "CMD" and test[1] in _CHROMA_IMAGE_TOOLS
    assert not any(tool in " ".join(test) for tool in _CHROMA_IMAGE_LACKS)
    assert chroma["image"] == "chromadb/chroma:1.5.9", "re-measure _CHROMA_IMAGE_TOOLS for the new image"
    for name in ("backend", "ingest-worker"):
        assert _services()[name]["depends_on"]["chroma"]["condition"] == "service_healthy"


def test_the_worker_replaces_the_images_http_probe():
    """The Dockerfile's HEALTHCHECK curls port 8000, which the ingest worker never serves."""

    healthcheck = _services()["ingest-worker"]["healthcheck"]
    assert healthcheck["test"] == ["CMD", "python", "-m", "app.ingest_worker", "--check"]
    assert "8000" not in " ".join(healthcheck["test"])
