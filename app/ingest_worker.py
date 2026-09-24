"""The ingest worker: runs ingest and reindex jobs from Redis (ARC-01 phase 5).

    python -m app.ingest_worker            # run until stopped
    python -m app.ingest_worker --burst    # run what is queued, then exit
    python -m app.ingest_worker --check    # healthcheck: exit 0 if a worker is alive

Only with STATE_BACKEND=shared; in memory mode the API process runs its own
jobs and this refuses to start. Run exactly one: recovery at startup treats
every job RQ still lists as started as one whose worker died, which is true
only when this is the only worker.

At startup, in order:

1. Jobs RQ still lists as started are dropped from that registry -- the worker
   that started them is gone, and their documents are requeued by step 2.
2. Every document still pending, queued or indexing with no job waiting for it
   is reindexed (`recover_unfinished_documents`).
3. The auto-ingest folder watcher starts here when AUTO_INGEST_ENABLED is on;
   the API processes no longer run it in shared mode, since each one would
   ingest every new file once per worker.

Jobs run in this process (`SimpleWorker`), not in a fork per job, so the
embedding model is loaded once rather than once per document. The per-job
timeout is a timer rather than SIGALRM, which also works on Windows.
"""

from __future__ import annotations

import argparse
import logging
import threading

logger = logging.getLogger("app.ingest_worker")


def _abandon_started_jobs(queue) -> list[str]:
    """Empty RQ's started-job registry; return the job ids it held.

    RQ 2.x keeps one `job_id:execution_id` entry per execution and implements
    neither `add` nor `remove` on this registry, so the entries are dropped
    directly. Their documents are requeued by `recover_unfinished_documents`.
    """
    registry = queue.started_job_registry
    entries = registry.connection.zrange(registry.key, 0, -1)
    abandoned = sorted({registry.parse_job_id(entry) for entry in entries})
    if entries:
        registry.connection.zrem(registry.key, *entries)
    if abandoned:
        logger.warning("ingest_worker_abandoned_started_jobs count=%d", len(abandoned))
    return abandoned


def _start_folder_watcher(settings) -> threading.Thread | None:
    if not settings.auto_ingest_enabled:
        return None
    from app.services.runtime.auto_ingest_watcher import AutoIngestWatcher

    watcher = AutoIngestWatcher(settings=settings)
    thread = threading.Thread(target=watcher.run_loop, args=(lambda: False,), daemon=True, name="auto-ingest-watcher")
    thread.start()
    return thread


def build_worker(connection, queue):
    from rq import SimpleWorker
    from rq.timeouts import TimerDeathPenalty

    class IngestWorker(SimpleWorker):
        death_penalty_class = TimerDeathPenalty

        def perform_job(self, job, queue):
            # A job embeds with the current model and writes with the current
            # settings, so it starts from what the other processes changed.
            _catch_up_before_work()
            return super().perform_job(job, queue)

    return IngestWorker([queue], connection=connection)


def _catch_up_before_work() -> None:
    from app.services.runtime.invalidation import catch_up
    from app.services.runtime.shared_state import SharedStateUnavailable

    try:
        catch_up()
    except SharedStateUnavailable as error:
        # The job itself came out of Redis a moment ago; if Redis is gone now,
        # the job will fail on its own writes and say so.
        logger.warning("ingest_worker_catch_up_failed error=%s", error)


def _connect():
    """Bytes, not text (RQ stores pickled payloads); no socket timeout (the worker blocks on the queue)."""

    from app.services.runtime.redis_connector import RedisConnector

    return RedisConnector("ingest_worker", decode_responses=False, socket_timeout=None).client()


def worker_is_alive(connection, queue_name: str) -> bool:
    """Whether some worker on this queue is registered in Redis.

    RQ keeps a worker's key alive by heartbeat and lets it expire otherwise, so
    a registered worker is one that has checked in within its TTL. The image's
    own healthcheck asks port 8000 for HTTP, which this process never serves.
    """

    from rq import Queue, Worker

    return bool(Worker.all(connection=connection, queue=Queue(queue_name, connection=connection)))


def _check() -> int:
    # Deliberately light: this runs every healthcheck interval, so it imports
    # neither the ingest pipeline nor any model -- only Redis and RQ.
    from app.services.runtime.shared_state import state_key

    connection = _connect()
    return 0 if connection is not None and worker_is_alive(connection, state_key("ingest")) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run QueryMind ingest and reindex jobs from Redis.")
    parser.add_argument("--burst", action="store_true", help="run the queued jobs, then exit")
    parser.add_argument("--check", action="store_true", help="exit 0 if a worker on the queue is alive, else 1")
    args = parser.parse_args(argv)
    if args.check:
        return _check()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    from rq import Queue

    from app.core.config import get_settings, validate_shared_state_backends
    from app.services.runtime.ingest_queue import queue_name, recover_unfinished_documents
    from app.services.runtime.redis_connector import probe

    settings = get_settings()
    if settings.state_backend != "shared":
        logger.error("The ingest worker needs STATE_BACKEND=shared; in memory mode the API process runs jobs itself.")
        return 2
    validate_shared_state_backends(settings)
    error = probe(settings.redis_url)
    if error is not None:
        # The URL is not repeated: it can carry the Redis password.
        logger.error("Redis at REDIS_URL did not answer: %s", error)
        return 2

    connection = _connect()
    if connection is None:
        logger.error("Redis at REDIS_URL did not answer.")
        return 2
    queue = Queue(queue_name(), connection=connection)
    from app.api.application.config_reload import apply_config_reload
    from app.services.runtime.invalidation import catch_up, on_config_change

    on_config_change(apply_config_reload)
    catch_up()
    _abandon_started_jobs(queue)
    recovered = recover_unfinished_documents()
    logger.info("ingest_worker_starting queue=%s recovered=%d", queue.name, len(recovered))
    _start_folder_watcher(settings)
    build_worker(connection, queue).work(burst=args.burst, with_scheduler=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
