import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings

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
    settings = get_settings()
    target = path or settings.corpus_path
    target.parent.mkdir(parents=True, exist_ok=True)
    # OPTIMIZATION: Add explicit 64KB buffering for better I/O performance
    with target.open("w", encoding="utf-8", buffering=65536) as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


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
