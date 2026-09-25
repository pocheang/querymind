"""gunicorn for the backend image (ARC-01 phase 9).

    gunicorn -c deploy/gunicorn.conf.py app.api.main:app

Why gunicorn rather than `uvicorn --workers`: gunicorn kills a worker whose
heartbeat stops and starts another. A UvicornWorker's heartbeat comes from its
event loop, so a process that is alive but wedged -- CLAUDE.md records one, a
thread parked in `logging` holding the lock every request needs, at zero CPU --
stops answering and is replaced after `timeout` seconds, where uvicorn would
leave it wedged until someone noticed.

The worker count is `APP_WORKERS`, read from the environment the container was
given, which is also where `Settings` reads it: the two cannot disagree the way
`uvicorn --workers N` and an unset `APP_WORKERS` could.
"""

import os
import shutil
from pathlib import Path

bind = "0.0.0.0:8000"
workers = max(1, int(os.environ.get("APP_WORKERS") or 1))
worker_class = "app.gunicorn_worker.QueryMindWorker"

# A worker whose heartbeat stops for this long is killed and replaced. The
# event loop ticks the heartbeat, so this bounds a blocked loop, not a request:
# a slow answer runs on threads and keeps the loop -- and the heartbeat -- alive.
timeout = int(os.environ.get("GUNICORN_TIMEOUT_SECONDS") or 60)
graceful_timeout = 30
keepalive = 5

# gunicorn's own check accepts single addresses only; the worker replaces this
# with QUERYMIND_TRUSTED_PROXIES, which may name a network (app/gunicorn_worker.py).
forwarded_allow_ips = "127.0.0.1"

accesslog = "-"
errorlog = "-"


def on_starting(server):
    """Start the metrics directory empty: files from a previous run are not this run's workers."""

    directory = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not directory:
        return
    path = Path(directory)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def child_exit(server, worker):
    """Drop a finished worker's live gauges, so a breaker it left open stops being reported."""

    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)
