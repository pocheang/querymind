from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.document_registry import list_document_records


def build_index_health_report(path: Path | None = None) -> dict[str, Any]:
    rows = list_document_records(path=path)
    ready = [r for r in rows if r.get("status") == "ready"]
    failed = [r for r in rows if r.get("status") == "failed"]
    indexing = [r for r in rows if r.get("status") in {"pending", "indexing"}]
    return {
        "total_documents": len(rows),
        "ready_documents": len(ready),
        "failed_documents": len(failed),
        "indexing_documents": len(indexing),
        "total_chunks": sum(int(r.get("chunks_indexed", 0) or 0) for r in rows),
        "total_triplets": sum(int(r.get("triplets_written", 0) or 0) for r in rows),
        "documents": rows,
    }
