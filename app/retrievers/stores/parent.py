import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.runtime.file_locks import write_lines


def write_parent_records(records: list[dict[str, Any]], path: Path | None = None) -> None:
    """Replace the file atomically. The caller holds the index lock (`index_writes`)
    for the read-modify-write around this; see `app/services/documents/index_lock.py`."""

    write_lines(path or get_settings().parent_store_path, records)


def read_parent_records(path: Path | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    target = path or settings.parent_store_path
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


def get_parent_text_map(parent_ids: list[str]) -> dict[str, str]:
    wanted = {str(x) for x in parent_ids if x}
    if not wanted:
        return {}
    rows = read_parent_records()
    out: dict[str, str] = {}
    for row in rows:
        parent_id = str(row.get("id", ""))
        if parent_id in wanted:
            out[parent_id] = str(row.get("text", ""))
            # Early exit optimization: stop scanning if we found all wanted IDs
            if len(out) == len(wanted):
                break
    return out
