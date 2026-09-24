"""Where ingest and reindex jobs run (ARC-01 phase 5).

`STATE_BACKEND=memory` keeps the in-process thread pool: one process, no Redis,
the behaviour a development checkout has always had. `STATE_BACKEND=shared`
puts each job on an RQ queue in Redis, and the one `ingest-worker` process
(`python -m app.ingest_worker`) runs them -- so a job survives the API process
that accepted it, and no API worker spends its threads parsing PDFs.

Each document has at most one job at a time. RQ enqueues a job id twice if it
is asked to, and running a reindex twice is harmless but pointless, so
`enqueue_*` returns without a second enqueue while a job for the document is
still waiting.

Crash recovery is `recover_unfinished_documents`: run when the only thing that
could be running a job has just started -- the API process in memory mode, the
ingest worker in shared mode -- so a document still marked pending, queued or
indexing, with no job waiting for it, can only be one whose job died. It is
reindexed, which deletes whatever the dead job had half-written first.
"""

from __future__ import annotations

import atexit
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.documents.index_manager import rebuild_document_index
from app.services.documents.ingest import ingest_paths
from app.services.documents.registry import (
    create_document_record,
    list_document_records,
    update_document_record,
)
from app.services.runtime.redis_connector import RedisConnector, redis_unavailable_errors
from app.services.runtime.runtime_ops import append_index_freshness
from app.services.runtime.shared_state import SharedStateUnavailable, is_shared, state_key

logger = logging.getLogger(__name__)

# The states a document is in while a job for it is owed or running.
UNFINISHED_STATES = frozenset({"pending", "queued", "indexing"})

# STATE_BACKEND=memory only. Two threads, as before; the index lock is what
# keeps them from losing each other's writes now.
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingest")
atexit.register(lambda: _EXECUTOR.shutdown(wait=False))

# RQ stores pickled payloads, so this client must not decode responses.
_RQ_CONNECTOR = RedisConnector("ingest_queue", decode_responses=False, socket_connect_timeout=2, socket_timeout=5)


def queue_name() -> str:
    return state_key("ingest")


def job_id_for(document_id: str) -> str:
    return f"index-{document_id}"


def _rq_queue():
    from rq import Queue

    client = _RQ_CONNECTOR.client()
    if client is None:
        raise SharedStateUnavailable("ingest queue (Redis) is unavailable")
    return Queue(queue_name(), connection=client)


def _job_is_waiting(queue: Any, job_id: str) -> bool:
    from rq.exceptions import NoSuchJobError
    from rq.job import Job, JobStatus

    try:
        status = Job.fetch(job_id, connection=queue.connection).get_status()
    except NoSuchJobError:
        return False
    return status in {JobStatus.QUEUED, JobStatus.DEFERRED, JobStatus.SCHEDULED}


def _submit(document_id: str, func: Callable[..., Any], /, **kwargs: Any) -> None:
    if not is_shared():
        _EXECUTOR.submit(func, **kwargs)
        return
    try:
        queue = _rq_queue()
        job_id = job_id_for(document_id)
        if _job_is_waiting(queue, job_id):
            return
        queue.enqueue(
            func,
            kwargs=kwargs,
            job_id=job_id,
            job_timeout=int(get_settings().ingest_job_timeout_seconds),
            result_ttl=3600,
            failure_ttl=7 * 24 * 3600,
        )
    except redis_unavailable_errors() as error:
        _RQ_CONNECTOR.drop(error)
        raise SharedStateUnavailable("ingest queue (Redis) is unavailable") from error


# ---- jobs --------------------------------------------------------------------------
# Module-level functions with plain arguments: RQ imports them by name in the
# worker process and pickles the keyword arguments.


def run_ingest_job(
    *,
    document_id: str,
    path: Path,
    metadata_overrides: dict[str, Any],
    parser_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    update_document_record(document_id, {"status": "indexing", "stage": "loading", "error": ""})
    source = str(path)
    try:
        result = ingest_paths(
            [path],
            reset_vector_store=False,
            metadata_overrides_by_source={source: metadata_overrides},
            parser_profiles_by_source={source: parser_profile or {}},
        )
        updated = update_document_record(
            document_id,
            {
                "status": "ready",
                "stage": "complete",
                "error": "",
                "chunks_indexed": int(result.get("chunks_indexed", 0) or 0),
                "triplets_written": int(result.get("triplets_written", 0) or 0),
            },
        )
        return {"ok": True, "result": result, "document": updated}
    except Exception as exc:
        logger.exception("ingest_job_failed document_id=%s path=%s", document_id, path)
        update_document_record(document_id, {"status": "failed", "stage": "failed", "error": str(exc)})
        return {"ok": False, "error": str(exc)}


def run_reindex_job(*, document_id: str, user_id: str) -> dict[str, Any]:
    """Delete a document's rows and ingest it again; the record says whether it worked."""

    record = _record(document_id)
    if record is None:
        logger.warning("reindex_job_document_gone document_id=%s", document_id)
        return {"ok": False, "error": "document not found"}
    try:
        return rebuild_document_index(
            str(record.get("filename", "") or ""), source=str(record.get("source", "") or ""), user_id=user_id
        )
    except Exception as exc:
        logger.exception("reindex_job_failed document_id=%s", document_id)
        update_document_record(document_id, {"status": "failed", "stage": "failed", "error": str(exc)})
        return {"ok": False, "error": str(exc)}


def _record(document_id: str) -> dict[str, Any] | None:
    return next((row for row in list_document_records() if row.get("document_id") == document_id), None)


# ---- entry points ------------------------------------------------------------------


def enqueue_ingest_job(
    *,
    document_id: str,
    path: Path,
    metadata_overrides: dict[str, Any],
    parser_profile: dict[str, Any] | None = None,
) -> bool:
    _submit(
        document_id,
        run_ingest_job,
        document_id=document_id,
        path=path,
        metadata_overrides=metadata_overrides,
        parser_profile=parser_profile,
    )
    return True


def enqueue_reindex_job(*, document_id: str, user_id: str) -> dict[str, Any]:
    """Mark the document queued and hand its reindex to whichever runner this deployment has.

    Marked first: a job can start the moment it is submitted, and marking after
    would overwrite its "indexing" with "queued". If the submit fails the mark
    is put back, so a 503 does not leave a document queued behind no job.
    """

    before = _record(document_id) or {}
    updated = update_document_record(document_id, {"status": "queued", "stage": "reindex_queued", "error": ""})
    try:
        _submit(document_id, run_reindex_job, document_id=document_id, user_id=user_id)
    except Exception:
        update_document_record(
            document_id,
            {key: before.get(key, "") for key in ("status", "stage", "error")},
        )
        raise
    return updated


def register_and_enqueue_uploads(
    *,
    uploads: list[Any],
    owner_user_id: str,
    visibility: str,
    tenant_id: str = "",
    acl_tags: tuple[str, ...] = (),
) -> list[str]:
    """Create document records and enqueue their ingestion as one runtime operation."""
    document_ids: list[str] = []
    for upload in uploads:
        parser_profile = upload.parser_profile
        record = create_document_record(
            source=str(upload.path),
            filename=upload.filename,
            sha256=upload.sha256,
            owner_user_id=owner_user_id,
            visibility=visibility,
            agent_class=upload.agent_class,
            parser_profile=str(parser_profile.get("name", "") or ""),
            tenant_id=tenant_id or owner_user_id,
            acl_tags=acl_tags,
        )
        document_id = str(record["document_id"])
        document_ids.append(document_id)
        enqueue_ingest_job(
            document_id=document_id,
            path=upload.path,
            metadata_overrides={
                "owner_user_id": owner_user_id,
                "tenant_id": str(record.get("tenant_id", "") or tenant_id or owner_user_id),
                "document_id": document_id,
                "version": int(record.get("version", 1) or 1),
                "acl_tags": tuple(str(value) for value in record.get("acl_tags", ()) or ()),
                "visibility": visibility,
                "agent_class": upload.agent_class,
                "parser_profile": str(parser_profile.get("name", "") or ""),
            },
            parser_profile=parser_profile,
        )
        append_index_freshness(
            {
                "user_id": owner_user_id,
                "filename": upload.filename,
                "source": str(upload.path),
                "freshness_seconds": 0.0,
                "chunks_indexed": 0,
                "mode": "queued",
            }
        )
    return document_ids


def recover_unfinished_documents() -> list[str]:
    """Reindex every document whose job cannot still be running; return their ids.

    Call only where nothing else can be running a job: at the start of the
    process that runs them. The ingest worker also clears RQ's started-job
    registry first, since the only worker that could have started those jobs is
    the one that is starting now.
    """

    queue = _rq_queue() if is_shared() else None
    recovered: list[str] = []
    for record in list_document_records():
        document_id = str(record.get("document_id", "") or "")
        if not document_id or str(record.get("status", "")) not in UNFINISHED_STATES:
            continue
        if queue is not None and _job_is_waiting(queue, job_id_for(document_id)):
            continue
        owner = str(record.get("owner_user_id", "") or "")
        logger.warning("ingest_recovery_requeue document_id=%s status=%s", document_id, record.get("status"))
        enqueue_reindex_job(document_id=document_id, user_id=owner)
        recovered.append(document_id)
    return recovered
