"""The compose stack describes a shared-state deployment the application will start (ARC-01 phases 5, 9).

`validate_shared_state_backends` refuses STATE_BACKEND=shared without sqlite
history, database metadata and a Chroma server. Until phase 9 that was an opt-in
overlay, compose.shared-state.yaml; it is the base stack now, so a key missing
here is every deployment building, starting its containers, and then having a
backend that refuses to boot.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from app.api.transport.client_address import trusted_proxies
from app.core.config import Settings, validate_shared_state_backends

BASE = Path("deploy/compose/compose.yaml")
RETIRED_OVERLAY = Path("deploy/compose/compose.shared-state.yaml")
_REQUIRED = {"NEO4J_PASSWORD": "neo4j-test", "REDIS_PASSWORD": "redis-test", "POSTGRES_PASSWORD": "pg-test"}
_INTERPOLATION = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?:(:?[-?])([^}]*))?\}")


def _interpolate(value: str, shell: dict[str, str]) -> str:
    """Compose's `${NAME}`, `${NAME:-default}` and `${NAME:?message}`, against `shell`."""

    def replace(match: re.Match[str]) -> str:
        name, operator, argument = match.group(1), match.group(2), match.group(3)
        present = shell.get(name)
        if operator and operator.endswith("-"):
            return present if present else argument
        if operator and operator.endswith("?") and not present:
            raise AssertionError(f"compose would refuse to render: {argument}")
        return present or ""

    return _INTERPOLATION.sub(replace, value)


def _resolve(node, shell: dict[str, str]):
    if isinstance(node, dict):
        return {key: _resolve(value, shell) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve(value, shell) for value in node]
    if isinstance(node, str):
        return _interpolate(node, shell)
    return node


def _stack(**shell: str) -> dict:
    return _resolve(yaml.safe_load(BASE.read_text(encoding="utf-8")), {**_REQUIRED, **shell})


def _services(**shell: str) -> dict:
    return _stack(**shell)["services"]


def _environment(service: str, **shell: str) -> dict[str, str]:
    return {key: str(value) for key, value in _services(**shell)[service]["environment"].items()}


@pytest.mark.parametrize("service", ["backend", "ingest-worker", "init"])
def test_every_service_satisfies_the_startup_rule(service: str):
    validate_shared_state_backends(Settings(**_environment(service)))


@pytest.mark.parametrize("service", ["backend", "ingest-worker", "init"])
def test_shared_is_the_default(service: str):
    assert _environment(service)["STATE_BACKEND"] == "shared"


def test_the_default_can_still_be_overridden_from_the_shell():
    """`environment:` outranks `env_file:`, so a literal would make shared mandatory rather than default."""

    assert _environment("backend", STATE_BACKEND="memory")["STATE_BACKEND"] == "memory"


def test_the_overlay_is_gone_and_nothing_tells_an_operator_to_use_it():
    """Scripts may not name it at all; the documentation may say it was merged, never pass it to `-f`."""

    assert not RETIRED_OVERLAY.exists()
    for path in [Path("Makefile"), *Path("deploy/scripts").iterdir()]:
        if path.is_file():
            assert RETIRED_OVERLAY.name not in path.read_text(encoding="utf-8"), f"{path} still names the overlay"
    as_argument = re.compile(r"-f\s+\S*" + re.escape(RETIRED_OVERLAY.name))
    for path in (Path("deploy/README.md"),):
        assert not as_argument.search(path.read_text(encoding="utf-8")), f"{path} still tells an operator to use it"


def test_the_worker_shares_the_backends_index_files():
    """The registry, corpus, uploads and the index lock must be one set of files for both."""

    services = _services()
    backend_volumes = set(services["backend"]["volumes"])
    worker_volumes = set(services["ingest-worker"]["volumes"])
    assert {"chunks_data:/app/data/chunks", "app_data:/app/data"} <= backend_volumes & worker_volumes


def test_there_is_exactly_one_ingest_worker():
    worker = _services()["ingest-worker"]
    assert worker["command"] == ["python", "-m", "app.ingest_worker"]
    assert worker["deploy"]["replicas"] == 1


def test_init_runs_once_and_everything_that_uses_the_data_waits_for_it():
    """A failed migration must keep the backend down, not let it start on half-moved data."""

    services = _services()
    init = services["init"]
    assert init["command"] == ["python", "-m", "app.init_app"]
    assert init["restart"] == "no"
    assert init["healthcheck"] == {"disable": True}
    for name in ("backend", "ingest-worker"):
        assert services[name]["depends_on"]["init"]["condition"] == "service_completed_successfully"


def test_init_can_reach_both_ends_of_the_vector_migration():
    """The source is the embedded directory an older backend wrote; the target is the Chroma server.

    If init mounted the directory anywhere but where the backend's
    CHROMA_PERSIST_DIR points, it would find nothing to copy, write no problems,
    and an upgrade would come up with an empty vector store.
    """

    services = _services()
    persist_dir = _environment("backend")["CHROMA_PERSIST_DIR"]
    assert _environment("init")["CHROMA_PERSIST_DIR"] == persist_dir
    for name in ("backend", "init"):
        assert f"chroma_data:{persist_dir}" in services[name]["volumes"]
    assert "app_data:/app/data" in services["init"]["volumes"]
    assert services["init"]["depends_on"]["chroma"]["condition"] == "service_healthy"


@pytest.mark.parametrize("shell", [{}, {"QUERYMIND_SUBNET": "10.77.0.0/24"}])
def test_the_backend_trusts_exactly_the_network_it_is_on(shell: dict[str, str]):
    """QUERYMIND_TRUSTED_PROXIES names the peers allowed to set the client address (SEC-02).

    nginx's address is whatever Docker assigns in this subnet, so the trust and
    the subnet are one value; if they came apart the backend would either trust
    nobody (every limit keyed on nginx) or trust a range nginx is not in.
    """

    stack = _stack(**shell)
    subnet = stack["networks"]["querymind"]["ipam"]["config"][0]["subnet"]
    trusted = stack["services"]["backend"]["environment"]["QUERYMIND_TRUSTED_PROXIES"]
    assert trusted == subnet
    assert trusted_proxies(trusted) == [subnet]
    if shell:
        assert subnet == shell["QUERYMIND_SUBNET"]


def test_the_chroma_server_matches_the_locked_client():
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

    The first version of the overlay probed with wget, which the image does not ship.
    """

    services = _services()
    chroma = services["chroma"]
    test = chroma["healthcheck"]["test"]
    assert test[0] == "CMD"
    assert test[1] in _CHROMA_IMAGE_TOOLS
    assert not any(tool in " ".join(test) for tool in _CHROMA_IMAGE_LACKS)
    assert chroma["image"] == "chromadb/chroma:1.5.9", "re-measure _CHROMA_IMAGE_TOOLS for the new image"
    for name in ("backend", "ingest-worker", "init"):
        assert services[name]["depends_on"]["chroma"]["condition"] == "service_healthy"


def test_the_worker_replaces_the_images_http_probe():
    """The Dockerfile's HEALTHCHECK curls port 8000, which the ingest worker never serves."""

    healthcheck = _services()["ingest-worker"]["healthcheck"]
    assert healthcheck["test"] == ["CMD", "python", "-m", "app.ingest_worker", "--check"]
    assert "8000" not in " ".join(healthcheck["test"])


def test_redis_keeps_its_append_only_file():
    """Redis holds the ingest queue and pending approvals now, not only a cache."""

    command = _services()["redis"]["command"]
    assert command[command.index("--appendonly") + 1] == "yes"
