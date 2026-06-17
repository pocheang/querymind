from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.services.document_registry import update_document_record
from app.services.ingest_service import ingest_paths

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingest")
_JOBS: dict[str, Future] = {}


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
        update_document_record(
            document_id,
            {"status": "failed", "stage": "failed", "error": str(exc)},
        )
        return {"ok": False, "error": str(exc)}


def enqueue_ingest_job(
    *,
    document_id: str,
    path: Path,
    metadata_overrides: dict[str, Any],
    parser_profile: dict[str, Any] | None = None,
) -> bool:
    future = _EXECUTOR.submit(
        run_ingest_job,
        document_id=document_id,
        path=path,
        metadata_overrides=metadata_overrides,
        parser_profile=parser_profile,
    )
    _JOBS[document_id] = future
    return True
