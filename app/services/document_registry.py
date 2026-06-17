from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings

_LOCK = threading.RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_path() -> Path:
    settings = get_settings()
    return settings.corpus_path.parent / "documents.jsonl"


def _normalize_record(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out.setdefault("document_id", "")
    out.setdefault("source", "")
    out.setdefault("filename", "")
    out.setdefault("sha256", "")
    out.setdefault("owner_user_id", "")
    out.setdefault("visibility", "private")
    out.setdefault("agent_class", "general")
    out.setdefault("parser_profile", "")
    out.setdefault("status", "pending")
    out.setdefault("stage", "uploaded")
    out.setdefault("error", "")
    out.setdefault("chunks_indexed", 0)
    out.setdefault("triplets_written", 0)
    out.setdefault("created_at", _now_iso())
    out.setdefault("updated_at", out["created_at"])
    return out


def _document_id_for(source: str, owner_user_id: str) -> str:
    seed = f"{owner_user_id}|{source}"
    return f"doc-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:16]}"


def list_document_records(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or _default_path()
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    with _LOCK:
        with target.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(_normalize_record(json.loads(line)))
    return rows


def write_document_records(records: list[dict[str, Any]], path: Path | None = None) -> None:
    target = path or _default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with target.open("w", encoding="utf-8") as f:
            for row in records:
                f.write(json.dumps(_normalize_record(row), ensure_ascii=False) + "\n")


def get_document_by_source(source: str, path: Path | None = None) -> dict[str, Any] | None:
    source_value = str(source)
    for row in list_document_records(path=path):
        if str(row.get("source", "")) == source_value:
            return row
    return None


def create_document_record(
    *,
    source: str,
    filename: str,
    sha256: str,
    owner_user_id: str,
    visibility: str,
    agent_class: str,
    parser_profile: str = "",
    path: Path | None = None,
) -> dict[str, Any]:
    rows = list_document_records(path=path)
    source_value = str(source)
    document_id = _document_id_for(source_value, str(owner_user_id))
    now = _now_iso()
    incoming = _normalize_record(
        {
            "document_id": document_id,
            "source": source_value,
            "filename": filename,
            "sha256": sha256,
            "owner_user_id": owner_user_id,
            "visibility": visibility,
            "agent_class": agent_class,
            "parser_profile": parser_profile,
            "status": "pending",
            "stage": "uploaded",
            "error": "",
            "chunks_indexed": 0,
            "triplets_written": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    replaced = False
    out: list[dict[str, Any]] = []
    for row in rows:
        if row["document_id"] == document_id or row["source"] == source_value:
            incoming["created_at"] = row.get("created_at") or incoming["created_at"]
            out.append(incoming)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(incoming)
    write_document_records(out, path=path)
    return incoming


def update_document_record(
    document_id: str,
    fields: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    rows = list_document_records(path=path)
    updated: dict[str, Any] | None = None
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("document_id") == document_id:
            merged = _normalize_record({**row, **fields, "updated_at": _now_iso()})
            out.append(merged)
            updated = merged
        else:
            out.append(row)
    if updated is None:
        raise ValueError(f"document not found: {document_id}")
    write_document_records(out, path=path)
    return updated


def update_document_by_source(source: str, fields: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    row = get_document_by_source(source, path=path)
    if row is None:
        raise ValueError(f"document not found for source: {source}")
    return update_document_record(str(row["document_id"]), fields, path=path)


def delete_document_by_source(source: str, path: Path | None = None) -> bool:
    rows = list_document_records(path=path)
    source_value = str(source)
    keep = [row for row in rows if str(row.get("source", "")) != source_value]
    if len(keep) == len(rows):
        return False
    write_document_records(keep, path=path)
    return True
