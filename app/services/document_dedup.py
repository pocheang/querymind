from __future__ import annotations

import hashlib
from pathlib import Path

from app.services.document_registry import list_document_records


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicate_for_user(sha256: str, owner_user_id: str, path: Path | None = None) -> dict | None:
    for row in list_document_records(path=path):
        if str(row.get("sha256", "")) != str(sha256):
            continue
        if str(row.get("owner_user_id", "")) != str(owner_user_id):
            continue
        if str(row.get("status", "")) in {"pending", "indexing", "ready"}:
            return row
    return None
