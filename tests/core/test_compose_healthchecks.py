"""A healthcheck may only read variables its own container has.

A healthcheck runs inside the container, so `$${NAME}` (compose's escape for a
literal `$`) is expanded by the container's shell against the container's
environment -- not the host's, and not whatever compose interpolated into the
`command:`. The Redis probe read `$${REDIS_PASSWORD}`, which only ever reached
the command line: it expanded to nothing, every probe failed with WRONGPASS, and
every service waiting for Redis to be healthy -- the backend included -- never
started. Found by running the stack, which no test here had done.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

COMPOSE_FILES = sorted(Path("deploy/compose").glob("compose*.yaml"))
_CONTAINER_VARIABLE = re.compile(r"\$\$\{?([A-Za-z_][A-Za-z0-9_]*)")


def _merged_services() -> dict[str, dict]:
    """Every service's healthcheck and environment keys, across all compose files."""

    merged: dict[str, dict] = {}
    for path in COMPOSE_FILES:
        for name, service in (yaml.safe_load(path.read_text(encoding="utf-8")).get("services") or {}).items():
            entry = merged.setdefault(name, {"environment": set(), "healthcheck": None})
            environment = service.get("environment") or {}
            keys = environment.keys() if isinstance(environment, dict) else [e.split("=", 1)[0] for e in environment]
            entry["environment"].update(keys)
            if service.get("healthcheck"):
                entry["healthcheck"] = service["healthcheck"]
    return merged


def test_there_are_healthchecks_to_check():
    assert sum(1 for s in _merged_services().values() if s["healthcheck"]) >= 3


@pytest.mark.parametrize("name", sorted(_merged_services()))
def test_a_healthcheck_reads_only_variables_its_container_has(name):
    service = _merged_services()[name]
    if not service["healthcheck"] or service["healthcheck"].get("disable"):
        pytest.skip("no healthcheck")
    probe = " ".join(map(str, service["healthcheck"]["test"]))
    missing = sorted(set(_CONTAINER_VARIABLE.findall(probe)) - service["environment"])
    assert not missing, f"{name}'s healthcheck reads {missing}, which its container does not set"
