"""Prometheus metrics, correct with any number of workers (ARC-01 phase 8).

`/metrics` used to render one process's in-memory counters. With several
uvicorn workers behind one port each scrape landed on whichever worker accepted
the connection, so counters jumped between processes -- which Prometheus reads
as counter resets, corrupting every `rate()`. Three more defects came out while
replacing it, and they are the reason this module is shaped the way it is:

- **The request metrics were never exported.** The middleware recorded HTTP
  counts and durations into its own `RuntimeMetrics()` instance; `/metrics`
  rendered a different one. Nothing a scrape saw described a request.
- **Labelled series were malformed.** `inc(name, labels={a, b})` wrote one series
  per label *key* -- `m{a="x"}` and `m{b="y"}` -- so `sum(m)` counted each event
  once per label.
- **19 of the 21 alert rules watched metrics nothing produced.** See
  `config/observability/prometheus/alert_rules.yml`, which now names only the
  series defined here, and `tests/core/test_alert_rules_have_producers.py`.

So the metrics are a fixed, declared set on `prometheus_client`. With
`PROMETHEUS_MULTIPROC_DIR` set -- the deployment images set it -- every worker
writes its values to files in that directory and a scrape aggregates all of
them (`multiprocess.MultiProcessCollector`); without it, one in-process
registry, which is what a developer's single `uvicorn` and the tests use.

Values that are facts about the whole deployment rather than about a worker
(query-guard occupancy, whether a dependency answers) are not stored at all:
they are computed by the worker answering the scrape, through collectors the
endpoint passes to `render`.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable
from pathlib import Path

logger = logging.getLogger(__name__)

_ENV = "PROMETHEUS_MULTIPROC_DIR"


def multiprocess_dir() -> Path | None:
    """The shared metrics directory, created if named; None in single-process mode.

    Read from the real process environment because `prometheus_client` reads it
    there, at import, to decide where values live -- a `Settings` field could not
    change that.
    """

    raw = os.environ.get(_ENV, "").strip()
    if not raw:
        return None
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


_MULTIPROC_DIR = multiprocess_dir()  # before any metric is created: values open files there

from prometheus_client import (  # noqa: E402 -- the directory must exist first
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

# `kind` keeps the latency SLO about answering questions: an SSE subscription
# stays open for minutes and /health answers in a millisecond, and a p95 over
# both says nothing about either. Three values, never a path -- a label per URL
# would be one series per session id.
REQUEST_KINDS = ("query", "stream", "other")
HTTP_REQUESTS = Counter(
    "http_requests",
    "HTTP requests answered, by status code and kind.",
    ["status", "kind"],
    registry=REGISTRY,
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Time to answer an HTTP request, by kind.",
    ["kind"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60, 120),
    registry=REGISTRY,
)
EMBEDDING_REINDEX = Counter(
    "embedding_reindex",
    "Full vector rebuilds requested by saving the model settings, by outcome.",
    ["outcome"],
    registry=REGISTRY,
)
# The moment a breaker closes again, as a Unix time; 0 when it is closed. A
# breaker is per process, so the scrape takes the latest across live workers:
# "open anywhere" is `circuit_breaker_open_until_seconds > time()`.
CIRCUIT_BREAKER_OPEN_UNTIL = Gauge(
    "circuit_breaker_open_until_seconds",
    "Unix time until which a circuit breaker stays open; 0 when closed.",
    ["breaker"],
    multiprocess_mode="livemax",
    registry=REGISTRY,
)


def request_kind(method: str, path: str) -> str:
    if method == "POST" and path == "/api/advanced-rag/query":
        return "query"
    if path.startswith("/agent-tracking/stream/") or (
        path.startswith("/api/v1/orchestration/executions/") and path.endswith("/events")
    ):
        return "stream"
    return "other"


def _never_raise(write: Callable[[], None], what: str) -> None:
    """A metric write must not fail the request or the call it describes.

    In multiprocess mode a write is a store into a memory-mapped file, which can
    fail with the disk -- and the breaker's success path records one.
    """

    try:
        write()
    except Exception as error:  # noqa: BLE001 - observability is observer-only
        logger.warning("metric_write_failed metric=%s error=%s", what, error)


def record_request(status_code: int, seconds: float, kind: str = "other") -> None:
    kind = kind if kind in REQUEST_KINDS else "other"

    def write() -> None:
        HTTP_REQUESTS.labels(status=str(int(status_code)), kind=kind).inc()
        HTTP_REQUEST_DURATION.labels(kind=kind).observe(max(0.0, float(seconds)))

    _never_raise(write, "http_requests")


def record_embedding_reindex(outcome: str) -> None:
    _never_raise(lambda: EMBEDDING_REINDEX.labels(outcome=outcome).inc(), "embedding_reindex")


def record_circuit_breaker(name: str, open_until: float) -> None:
    _never_raise(
        lambda: CIRCUIT_BREAKER_OPEN_UNTIL.labels(breaker=name).set(float(open_until)),
        "circuit_breaker_open_until_seconds",
    )


def render(extra_collectors: Iterable[object] = ()) -> tuple[bytes, str]:
    """The exposition document and its content type, aggregated across workers when multiprocess."""

    # A fresh registry per scrape: registering the scrape-time collectors on the
    # shared one would make two concurrent scrapes collide on duplicate names.
    registry = CollectorRegistry()
    if _MULTIPROC_DIR is None:
        registry.register(_Stored())
    else:
        from prometheus_client import multiprocess

        _forget_dead_workers(_MULTIPROC_DIR)
        multiprocess.MultiProcessCollector(registry, path=str(_MULTIPROC_DIR))
    for collector in extra_collectors:
        registry.register(collector)
    return generate_latest(registry), CONTENT_TYPE_LATEST


class _Stored:
    """This process's metrics, for a single-process server."""

    def collect(self):
        yield from REGISTRY.collect()


def _forget_dead_workers(directory: Path) -> None:
    """Drop live-gauge files of processes that no longer exist.

    `livemax` means "across live processes", and prometheus_client learns that a
    process died only from `mark_process_dead`, which a server hook would call --
    uvicorn has none. Without this a worker that died with a breaker open would
    report it open until the container restarted. Counters are left alone: a
    dead worker's requests still happened.
    """

    from prometheus_client import multiprocess

    pids = set()
    for path in directory.glob("gauge_live*_*.db"):
        try:
            pids.add(int(path.stem.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    for pid in pids:
        if pid != os.getpid() and not _alive(pid):
            multiprocess.mark_process_dead(pid, path=str(directory))


def _alive(pid: int) -> bool:
    if os.name == "nt":
        # On Windows os.kill(pid, 0) does not probe: it TERMINATES the process
        # (TerminateProcess with exit code 0). Multiprocess mode runs in the
        # Linux images; here every process is assumed alive.
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


__all__ = [
    "CONTENT_TYPE_LATEST",
    "multiprocess_dir",
    "record_circuit_breaker",
    "record_embedding_reindex",
    "record_request",
    "request_kind",
    "render",
]
