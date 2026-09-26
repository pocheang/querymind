"""Metrics computed at scrape time by the worker answering it (ARC-01 phase 8).

These describe the deployment rather than one worker, so storing them per
process and summing would be wrong: query-guard occupancy is already shared in
Redis under STATE_BACKEND=shared, and "can this deployment reach Chroma" has one
answer. The worker that answers the scrape asks, and reports what it found.

Dependency probes are cached briefly per worker: Prometheus scrapes every few
seconds, `/metrics` is unauthenticated, and each probe is a network round trip.
Only the deployment's own infrastructure is probed -- never the external model
providers, which cost money per call and are why `/ready/dependencies` is
admin-only.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

from prometheus_client.core import GaugeMetricFamily

_CACHE_SECONDS = 15.0
_cache_lock = threading.Lock()
_cached: tuple[float, dict[str, dict[str, Any]]] | None = None


class DeploymentStateCollector:
    """Query-guard occupancy and dependency reachability, as the scraping worker sees them."""

    def __init__(self, guard: dict[str, Any], dependencies: dict[str, dict[str, Any]]) -> None:
        self._guard = guard
        self._dependencies = dependencies

    def collect(self) -> Iterator[GaugeMetricFamily]:
        yield GaugeMetricFamily(
            "query_guard_inflight", "Queries being answered now.", value=float(self._guard.get("inflight", 0) or 0)
        )
        yield GaugeMetricFamily(
            "query_guard_waiting", "Queries waiting for a slot.", value=float(self._guard.get("waiting", 0) or 0)
        )
        up = GaugeMetricFamily("dependency_up", "1 when the dependency answered its probe.", labels=["dependency"])
        required = GaugeMetricFamily(
            "dependency_required", "1 when this deployment cannot work without it.", labels=["dependency"]
        )
        for name, check in sorted(self._dependencies.items()):
            up.add_metric([name], 1.0 if check.get("ok") else 0.0)
            required.add_metric([name], 1.0 if check.get("required") else 0.0)
        yield up
        yield required


async def probe_dependencies(checks: dict[str, Callable[[], dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Run the checks concurrently, reusing a result younger than the cache window."""

    global _cached
    now = time.monotonic()
    with _cache_lock:
        if _cached is not None and now - _cached[0] < _CACHE_SECONDS:
            return _cached[1]
    results = await asyncio.gather(*(asyncio.to_thread(fn) for fn in checks.values()), return_exceptions=True)
    found = {
        name: ({"ok": False, "required": False} if isinstance(result, BaseException) else result)
        for name, result in zip(checks, results, strict=True)
    }
    with _cache_lock:
        _cached = (time.monotonic(), found)
    return found


def reset_for_tests() -> None:
    global _cached
    with _cache_lock:
        _cached = None
