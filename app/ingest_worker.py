"""The ingest worker: runs ingest and reindex jobs from Redis (ARC-01 phase 5).

    python -m app.ingest_worker            # run until stopped
    python -m app.ingest_worker --burst    # run what is queued, then exit

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

    return IngestWorker([queue], connection=connection)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run QueryMind ingest and reindex jobs from Redis.")
    parser.add_argument("--burst", action="store_true", help="run the queued jobs, then exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    from rq import Queue

    from app.core.config import get_settings, validate_shared_state_backends
    from app.services.runtime.ingest_queue import queue_name, recover_unfinished_documents
    from app.services.runtime.redis_connector import RedisConnector, probe

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

    # No socket timeout: the worker blocks on the queue between jobs. Bytes, not
    # text: RQ stores pickled payloads.
    connection = RedisConnector("ingest_worker", decode_responses=False, socket_timeout=None).client()
    if connection is None:
        logger.error("Redis at REDIS_URL did not answer.")
        return 2
    queue = Queue(queue_name(), connection=connection)
    _abandon_started_jobs(queue)
    recovered = recover_unfinished_documents()
    logger.info("ingest_worker_starting queue=%s recovered=%d", queue.name, len(recovered))
    _start_folder_watcher(settings)
    build_worker(connection, queue).work(burst=args.burst, with_scheduler=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
