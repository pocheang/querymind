"""The one lock every write to the document index takes (ARC-01 phase 5).

"The index" is everything a delete has to keep in step: `chunks.jsonl`,
`parents.jsonl`, the Chroma collections, the graph triplets and the table store.
A delete reads the corpus to learn which vector ids and sources to remove, so an
ingest writing the same document's rows between that read and the delete's own
writes leaves vectors no corpus row names -- which is why every writer holds
this lock for its writes, and only for its writes: parsing, OCR, embedding and
triplet extraction happen before it is taken.

A request waits `INDEX_LOCK_REQUEST_TIMEOUT_SECONDS` and then answers 503 with
`Retry-After`; the ingest worker waits as long as it takes.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import get_settings
from app.services.runtime.file_locks import LockBusy, held

__all__ = ["LockBusy", "index_lock_path", "index_writes", "request_index_writes"]


def index_lock_path() -> Path:
    return get_settings().corpus_path.parent / "index.lock"


@contextmanager
def index_writes(*, timeout: float | None = None) -> Iterator[None]:
    with held(index_lock_path(), timeout=timeout):
        yield


@contextmanager
def request_index_writes() -> Iterator[None]:
    """For a request: wait briefly, then raise `LockBusy` rather than hold a worker thread."""

    with index_writes(timeout=float(get_settings().index_lock_request_timeout_seconds)):
        yield
