import hashlib
import json
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.singleton import Cell
from app.services.runtime.file_locks import write_lines

if TYPE_CHECKING:
    from langchain_core.documents import Document


def normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in metadata.items():
        if isinstance(v, str | int | float | bool) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


def _stable_chunk_id(metadata: dict[str, Any], page_content: str, index: int) -> str:
    """Derive a chunk_id from content-identifying metadata.

    Re-ingesting the same document without an explicit chunk_id then produces
    the same id rather than a fresh one every time, since the seed is the
    document's own identity plus its position and content hash. Falls back to
    a random suffix only when there is no identity to seed from at all.
    """
    source = str(metadata.get("source", "") or "")
    document_id = str(metadata.get("document_id", "") or "")
    version = str(metadata.get("version", "") or "")
    parent_id = str(metadata.get("parent_id", "") or "")
    parent_index = str(metadata.get("parent_index", "") or "")
    child_index = str(metadata.get("child_index", "") or "")
    page = str(metadata.get("page", "") or "")
    image_index = str(metadata.get("image_index", "") or "")
    text_hash = hashlib.sha1(str(page_content or "").encode("utf-8")).hexdigest()[:16]
    identity = f"{document_id}|v{version}" if document_id and version else source
    if not identity:
        return f"chunk-{index}-{uuid.uuid4().hex[:8]}"
    stable_seed = f"{identity}|{page}|{parent_id}|{parent_index}|{child_index}|{image_index}|{text_hash}"
    return f"chunk-{hashlib.sha1(stable_seed.encode('utf-8')).hexdigest()[:16]}"


def documents_to_records(documents: list["Document"]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for i, doc in enumerate(documents):
        metadata = normalize_metadata(dict(doc.metadata))
        if not metadata.get("ingested_at"):
            metadata["ingested_at"] = datetime.now(UTC).isoformat()
        chunk_id = metadata.get("chunk_id") or _stable_chunk_id(metadata, doc.page_content, i)
        metadata["chunk_id"] = chunk_id
        records.append({"id": chunk_id, "text": doc.page_content, "metadata": metadata})
    return records


def write_corpus_records(records: list[dict[str, Any]], path: Path | None = None) -> None:
    """Replace the file atomically. The caller holds the index lock (`index_writes`)
    for the read-modify-write around this; see `app/services/documents/index_lock.py`."""

    write_lines(path or get_settings().corpus_path, records)


@dataclass(frozen=True)
class CorpusSnapshot:
    """One version of the corpus file, parsed once and shared by its readers.

    `records` are shared across every caller in the process and must not be
    mutated -- writers read their own copy through `read_corpus_records`.
    `source_digests` maps each source to a digest of its raw lines, so a cache
    built over some sources can tell whether *those* changed without
    re-reading their text (PERF-02).
    """

    signature: tuple[str, int, int, int]
    records: tuple[dict[str, Any], ...]
    source_digests: Mapping[str, str]


_EMPTY_SNAPSHOT = CorpusSnapshot(signature=("", 0, 0, 0), records=(), source_digests=MappingProxyType({}))
# Keyed by the file's stat signature, so any write -- this process's, another
# worker's, or a hand edit -- is a new version without anyone announcing it.
# `write_lines` replaces the file atomically, which changes the inode and the
# mtime together.
_SNAPSHOT: Cell[CorpusSnapshot | None] = Cell(None)
_SNAPSHOT_LOCK = threading.Lock()


def _signature(target: Path) -> tuple[str, int, int, int] | None:
    try:
        stat = target.stat()
    except FileNotFoundError:
        return None
    return (str(target.resolve()), stat.st_mtime_ns, stat.st_size, stat.st_ino)


def corpus_snapshot(path: Path | None = None) -> CorpusSnapshot:
    """The current corpus, parsed at most once per version per process (PERF-01).

    Scope resolution reads the whole corpus to learn which documents exist, and
    it ran twice per question -- once in the API and once in
    `privacy_permission` -- parsing every tenant's chunks each time.
    """

    target = path or get_settings().corpus_path
    signature = _signature(target)
    if signature is None:
        return _EMPTY_SNAPSHOT
    cached = _SNAPSHOT.value
    if cached is not None and cached.signature == signature:
        return cached
    with _SNAPSHOT_LOCK:
        cached = _SNAPSHOT.value
        if cached is not None and cached.signature == signature:
            return cached
        snapshot = _parse_snapshot(target, signature)
        _SNAPSHOT.value = snapshot
        return snapshot


def _parse_snapshot(target: Path, signature: tuple[str, int, int, int]) -> CorpusSnapshot:
    records: list[dict[str, Any]] = []
    hashers: dict[str, Any] = {}
    with target.open("r", encoding="utf-8", buffering=65536) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            records.append(row)
            source = str((row.get("metadata", {}) or {}).get("source", ""))
            hasher = hashers.get(source)
            if hasher is None:
                hasher = hashers[source] = hashlib.blake2b(digest_size=16)
            hasher.update(line.encode("utf-8"))
            hasher.update(b"\n")
    digests = {source: hasher.hexdigest() for source, hasher in hashers.items()}
    # The signature is re-read after parsing: a write that landed mid-read would
    # otherwise be cached under the older signature and served as that version.
    if _signature(target) != signature:
        signature = ("", -1, -1, -1)
    return CorpusSnapshot(signature=signature, records=tuple(records), source_digests=MappingProxyType(digests))


def reset_corpus_snapshot() -> None:
    _SNAPSHOT.value = None


def read_corpus_records(path: Path | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    target = path or settings.corpus_path
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    # OPTIMIZATION: Add explicit 64KB buffering for better I/O performance
    with target.open("r", encoding="utf-8", buffering=65536) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows
