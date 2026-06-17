# Document Registry Async Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full upload and ingestion optimization set: document registry, asynchronous ingestion, file deduplication, incremental indexing, graph-quality metadata, health reporting, parser profiles, and frontend indexing visibility.

**Architecture:** Add a lightweight JSONL-backed document registry first, matching the existing `chunks.jsonl` and `parents.jsonl` style. Uploads create document registry records and enqueue ingestion jobs; a background worker processes each file through the existing `ingest_paths()` pipeline and updates stage-level status. Subsequent tasks build on that registry to skip duplicate content, reindex only changed files, enrich Neo4j relations with provenance and confidence, expose health reports, and let parser profiles choose safer loader/chunk/graph behavior per document type.

**Tech Stack:** FastAPI, Pydantic-style dict schemas, JSONL storage, existing `app.services.ingest_service.ingest_paths`, Chroma, Neo4j, pytest, React/Vite frontend.

---

## File Structure

- Create: `app/services/document_registry.py`
  - Owns document-level records: `document_id`, `source`, `filename`, `sha256`, `owner_user_id`, `visibility`, `agent_class`, `status`, `stage`, `error`, `chunks_indexed`, `triplets_written`, timestamps.
  - Provides thread-safe JSONL read/write/update helpers.

- Create: `app/services/ingest_queue.py`
  - Owns in-process background ingestion queue.
  - Wraps `ingest_paths()` and updates registry status.
  - Keeps implementation small; no external broker yet.

- Create: `app/services/document_dedup.py`
  - Computes SHA256.
  - Detects same-user duplicate uploads.
  - Provides registry-safe dedupe decisions.

- Create: `app/services/index_health.py`
  - Builds per-document health reports from registry, corpus records, parent records, and Neo4j triplet counts.

- Create: `app/services/parser_profiles.py`
  - Chooses parser/chunk/graph extraction profile from file suffix, agent class, and optional request override.

- Modify: `app/api/routes/documents.py`
  - Upload route writes registry records and enqueues background ingestion instead of blocking on `ingest_paths()`.
  - List route merges `list_indexed_files()` with registry records so pending files appear before indexing finishes.
  - Reindex route updates registry status and uses incremental skip rules.
  - New health endpoint returns registry/vector/graph readiness per document.

- Modify: `app/core/schemas.py`
  - Add response fields for upload task IDs and document indexing status.
  - Add response fields for duplicate status, health, parser profile, and incremental reindex result.

- Modify: `app/services/ingest_service.py`
  - Return stage-level counts.
  - Pass `chunk_id`, `page`, and confidence to graph extraction/writes.
  - Accept parser profile options without changing old callers.

- Modify: `app/ingestion/graph_extractor.py`
  - Return structured triplets with confidence and extraction method.
  - Filter weak triplets before Neo4j writes.

- Modify: `app/graph/neo4j_client.py`
  - Store relation evidence: `sources`, `chunk_ids`, `pages`, `confidence_max`, and `confidence_avg`.

- Modify: `frontend/src/lib/api-client.ts`
  - Type upload responses and document rows with status fields.

- Modify: `frontend/src/pages/chat/components/DocumentsPanel.tsx`
  - Show status text for uploaded files.
  - Show duplicate/reused state, parser profile, health, and graph/vector readiness.

- Test: `tests/test_document_registry.py`
- Test: `tests/test_ingest_queue.py`
- Test: `tests/test_documents_upload_async.py`
- Test: `tests/test_document_dedup.py`
- Test: `tests/test_incremental_indexing.py`
- Test: `tests/test_graph_triplet_quality.py`
- Test: `tests/test_index_health.py`
- Test: `tests/test_parser_profiles.py`

---

### Task 1: Document Registry Store

**Files:**
- Create: `app/services/document_registry.py`
- Test: `tests/test_document_registry.py`

- [ ] **Step 1: Write failing tests for create, update, list, and dedupe**

Create `tests/test_document_registry.py`:

```python
from pathlib import Path

from app.services.document_registry import (
    create_document_record,
    get_document_by_source,
    list_document_records,
    update_document_record,
)


def test_create_and_list_document_record(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"

    record = create_document_record(
        source=str(tmp_path / "a.pdf"),
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )

    rows = list_document_records(path=registry_path)

    assert len(rows) == 1
    assert rows[0]["document_id"] == record["document_id"]
    assert rows[0]["status"] == "pending"
    assert rows[0]["stage"] == "uploaded"
    assert rows[0]["source"].endswith("a.pdf")


def test_update_document_record_merges_fields(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    record = create_document_record(
        source=str(tmp_path / "a.pdf"),
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )

    update_document_record(
        record["document_id"],
        {"status": "ready", "stage": "complete", "chunks_indexed": 7, "triplets_written": 3},
        path=registry_path,
    )

    updated = get_document_by_source(str(tmp_path / "a.pdf"), path=registry_path)

    assert updated is not None
    assert updated["status"] == "ready"
    assert updated["stage"] == "complete"
    assert updated["chunks_indexed"] == 7
    assert updated["triplets_written"] == 3
    assert updated["error"] == ""


def test_create_document_record_reuses_same_source(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    source = str(tmp_path / "a.pdf")

    first = create_document_record(
        source=source,
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )
    second = create_document_record(
        source=source,
        filename="a.pdf",
        sha256="abc123",
        owner_user_id="user-1",
        visibility="private",
        agent_class="pdf_text",
        path=registry_path,
    )

    rows = list_document_records(path=registry_path)

    assert first["document_id"] == second["document_id"]
    assert len(rows) == 1
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_document_registry.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.document_registry'`.

- [ ] **Step 3: Implement registry store**

Create `app/services/document_registry.py`:

```python
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
            created_at = row.get("created_at") or incoming["created_at"]
            incoming["created_at"] = created_at
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
```

- [ ] **Step 4: Run tests and verify pass**

Run:

```bash
pytest tests/test_document_registry.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/document_registry.py tests/test_document_registry.py
git commit -m "feat: add document registry store"
```

---

### Task 2: Upload Creates Registry Records

**Files:**
- Modify: `app/api/routes/documents.py`
- Modify: `app/core/schemas.py`
- Test: `tests/test_documents_upload_async.py`

- [ ] **Step 1: Write failing test for upload registry creation**

Create `tests/test_documents_upload_async.py`:

```python
from pathlib import Path
from unittest.mock import patch


def test_upload_creates_registry_record(client, tmp_path: Path, monkeypatch):
    from app.api.routes import documents
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)
    monkeypatch.setattr(documents.settings, "uploads_path", tmp_path / "uploads")
    monkeypatch.setattr(documents.settings, "upload_max_files", 20)
    monkeypatch.setattr(documents.settings, "upload_max_file_bytes", 1024 * 1024)
    monkeypatch.setattr(documents.settings, "upload_max_total_bytes", 1024 * 1024)
    monkeypatch.setattr(documents.settings, "upload_read_chunk_bytes", 64 * 1024)

    with patch("app.api.routes.documents._require_user", return_value={"user_id": "u1", "role": "viewer"}), \
         patch("app.api.routes.documents._require_permission"), \
         patch("app.api.routes.documents._audit"), \
         patch("app.api.routes.documents.upload_limiter.allow", return_value=True), \
         patch("app.api.routes.documents.delete_file_index", return_value={"ok": True}), \
         patch("app.api.routes.documents.enqueue_ingest_job", return_value=True):
        response = client.post(
            "/api/upload",
            files={"files": ("note.md", b"# Hello\nWorld", "text/markdown")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["filenames"] == ["note.md"]
    assert body["indexing_status"] == "queued"

    rows = document_registry.list_document_records(path=registry_path)
    assert len(rows) == 1
    assert rows[0]["filename"] == "note.md"
    assert rows[0]["owner_user_id"] == "u1"
    assert rows[0]["status"] == "pending"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_documents_upload_async.py::test_upload_creates_registry_record -q
```

Expected: FAIL because `indexing_status` and `enqueue_ingest_job` do not exist yet.

- [ ] **Step 3: Add response fields**

Modify `app/core/schemas.py` so `UploadResponse` includes:

```python
    document_ids: list[str] = Field(default_factory=list)
    indexing_status: str = "complete"
```

Keep existing fields unchanged.

- [ ] **Step 4: Wire upload to registry and queue placeholder**

Modify `app/api/routes/documents.py` imports:

```python
from app.services.document_registry import create_document_record
from app.services.ingest_queue import enqueue_ingest_job
```

After `assigned_agent_classes` is built and before pre-cleaning, compute SHA256 while writing the file. Add this helper near `_resolve_manageable_source_for_filename`:

```python
def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
```

Replace the synchronous `ingest_paths(...)` block with:

```python
    document_ids: list[str] = []
    for p in saved_paths:
        record = create_document_record(
            source=str(p),
            filename=p.name,
            sha256=_sha256_file(p),
            owner_user_id=str(user.get("user_id", "")),
            visibility=visibility_applied,
            agent_class=assigned_agent_classes.get(str(p), "general"),
        )
        document_ids.append(str(record["document_id"]))
        enqueue_ingest_job(
            document_id=str(record["document_id"]),
            path=p,
            metadata_overrides={
                "owner_user_id": str(user.get("user_id", "")),
                "visibility": visibility_applied,
                "agent_class": assigned_agent_classes.get(str(p), "general"),
            },
        )

    _audit(request, action="document.upload", resource_type="document", result="success", user=user, detail=",".join(filenames))
    return UploadResponse(
        filenames=filenames,
        skipped_files=skipped_files,
        visibility_applied=visibility_applied,
        assigned_agent_classes=assigned_agent_classes,
        document_ids=document_ids,
        indexing_status="queued",
        loaded_documents=len(saved_paths),
        chunks_indexed=0,
        triplets_written=0,
    )
```

- [ ] **Step 5: Create queue placeholder to satisfy import**

Create `app/services/ingest_queue.py`:

```python
from pathlib import Path
from typing import Any


def enqueue_ingest_job(
    *,
    document_id: str,
    path: Path,
    metadata_overrides: dict[str, Any],
) -> bool:
    return True
```

- [ ] **Step 6: Run focused test**

Run:

```bash
pytest tests/test_documents_upload_async.py::test_upload_creates_registry_record -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/api/routes/documents.py app/core/schemas.py app/services/ingest_queue.py tests/test_documents_upload_async.py
git commit -m "feat: create document records on upload"
```

---

### Task 3: Background Ingestion Queue

**Files:**
- Modify: `app/services/ingest_queue.py`
- Test: `tests/test_ingest_queue.py`

- [ ] **Step 1: Write failing tests for successful and failed jobs**

Create `tests/test_ingest_queue.py`:

```python
from pathlib import Path
from unittest.mock import patch

from app.services.document_registry import create_document_record, get_document_by_source
from app.services.ingest_queue import run_ingest_job


def test_run_ingest_job_updates_ready_status(tmp_path: Path, monkeypatch):
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)
    source = tmp_path / "note.md"
    source.write_text("# Hello", encoding="utf-8")
    record = create_document_record(
        source=str(source),
        filename="note.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    with patch("app.services.ingest_queue.ingest_paths", return_value={"loaded_documents": 1, "chunks_indexed": 2, "triplets_written": 1}):
        run_ingest_job(
            document_id=record["document_id"],
            path=source,
            metadata_overrides={"owner_user_id": "u1", "visibility": "private", "agent_class": "general"},
        )

    updated = get_document_by_source(str(source), path=registry_path)
    assert updated["status"] == "ready"
    assert updated["stage"] == "complete"
    assert updated["chunks_indexed"] == 2
    assert updated["triplets_written"] == 1
    assert updated["error"] == ""


def test_run_ingest_job_updates_failed_status(tmp_path: Path, monkeypatch):
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)
    source = tmp_path / "bad.md"
    source.write_text("# Bad", encoding="utf-8")
    record = create_document_record(
        source=str(source),
        filename="bad.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    with patch("app.services.ingest_queue.ingest_paths", side_effect=RuntimeError("parse failed")):
        run_ingest_job(
            document_id=record["document_id"],
            path=source,
            metadata_overrides={"owner_user_id": "u1", "visibility": "private", "agent_class": "general"},
        )

    updated = get_document_by_source(str(source), path=registry_path)
    assert updated["status"] == "failed"
    assert updated["stage"] == "failed"
    assert "parse failed" in updated["error"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_ingest_queue.py -q
```

Expected: FAIL because `run_ingest_job` is missing.

- [ ] **Step 3: Implement in-process queue**

Replace `app/services/ingest_queue.py` with:

```python
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.services.document_registry import update_document_record
from app.services.ingest_service import ingest_paths

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingest")


def run_ingest_job(
    *,
    document_id: str,
    path: Path,
    metadata_overrides: dict[str, Any],
) -> None:
    try:
        update_document_record(document_id, {"status": "indexing", "stage": "ingesting", "error": ""})
        result = ingest_paths(
            [path],
            reset_vector_store=False,
            metadata_overrides_by_source={str(path): metadata_overrides},
        )
        update_document_record(
            document_id,
            {
                "status": "ready",
                "stage": "complete",
                "chunks_indexed": int(result.get("chunks_indexed", 0) or 0),
                "triplets_written": int(result.get("triplets_written", 0) or 0),
                "error": "",
            },
        )
    except Exception as e:
        logger.exception("ingest_job_failed document_id=%s path=%s", document_id, path)
        update_document_record(
            document_id,
            {
                "status": "failed",
                "stage": "failed",
                "error": f"{type(e).__name__}: {e}",
            },
        )


def enqueue_ingest_job(
    *,
    document_id: str,
    path: Path,
    metadata_overrides: dict[str, Any],
) -> bool:
    _EXECUTOR.submit(
        run_ingest_job,
        document_id=document_id,
        path=path,
        metadata_overrides=metadata_overrides,
    )
    return True
```

- [ ] **Step 4: Run focused tests**

Run:

```bash
pytest tests/test_ingest_queue.py -q
```

Expected: PASS.

- [ ] **Step 5: Run upload test**

Run:

```bash
pytest tests/test_documents_upload_async.py::test_upload_creates_registry_record -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/ingest_queue.py tests/test_ingest_queue.py
git commit -m "feat: process ingestion jobs in background"
```

---

### Task 4: Document Status in API

**Files:**
- Modify: `app/api/routes/documents.py`
- Modify: `app/core/schemas.py`
- Test: `tests/test_documents_upload_async.py`

- [ ] **Step 1: Add failing test for pending documents in list response**

Append to `tests/test_documents_upload_async.py`:

```python
def test_list_documents_includes_pending_registry_records(client, tmp_path: Path, monkeypatch):
    from app.api.routes import documents
    from app.services import document_registry

    registry_path = tmp_path / "documents.jsonl"
    source = tmp_path / "uploads" / "u1" / "note.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Hello", encoding="utf-8")
    monkeypatch.setattr(document_registry, "_default_path", lambda: registry_path)

    document_registry.create_document_record(
        source=str(source),
        filename="note.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    with patch("app.api.routes.documents._require_user", return_value={"user_id": "u1", "role": "viewer"}), \
         patch("app.api.routes.documents._require_permission"), \
         patch("app.api.routes.documents._audit"), \
         patch("app.api.routes.documents._list_visible_documents_for_user", return_value=[]):
        response = client.get("/api/documents")

    assert response.status_code == 200
    rows = response.json()
    assert rows[0]["filename"] == "note.md"
    assert rows[0]["indexing_status"] == "pending"
    assert rows[0]["indexing_stage"] == "uploaded"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_documents_upload_async.py::test_list_documents_includes_pending_registry_records -q
```

Expected: FAIL because list endpoint does not merge registry records.

- [ ] **Step 3: Add schema fields to document summary**

Modify `IndexedFileSummary` in `app/core/schemas.py` to include:

```python
    document_id: str | None = None
    indexing_status: str = "ready"
    indexing_stage: str = "complete"
    indexing_error: str = ""
    triplets_written: int = 0
```

- [ ] **Step 4: Merge registry records in list endpoint**

Modify imports in `app/api/routes/documents.py`:

```python
from app.services.document_registry import create_document_record, list_document_records
```

Add helper:

```python
def _merge_registry_status(indexed_rows: list[dict[str, Any]], user: dict[str, Any]) -> list[dict[str, Any]]:
    by_source = {str(row.get("source", "") or ""): dict(row) for row in indexed_rows}
    user_id = str(user.get("user_id", ""))
    role = str(user.get("role", "viewer")).lower()
    for record in list_document_records():
        owner_user_id = str(record.get("owner_user_id", "") or "")
        visibility = str(record.get("visibility", "private") or "private").lower()
        if role != "admin" and visibility != "public" and owner_user_id != user_id:
            continue
        source = str(record.get("source", "") or "")
        row = by_source.get(source, {"filename": record.get("filename", ""), "source": source, "chunks": 0, "pages": []})
        row["document_id"] = record.get("document_id")
        row["owner_user_id"] = record.get("owner_user_id")
        row["visibility"] = record.get("visibility", "private")
        row["agent_class"] = record.get("agent_class", "general")
        row["indexing_status"] = record.get("status", "pending")
        row["indexing_stage"] = record.get("stage", "uploaded")
        row["indexing_error"] = record.get("error", "")
        row["triplets_written"] = int(record.get("triplets_written", 0) or 0)
        if int(row.get("chunks", 0) or 0) == 0:
            row["chunks"] = int(record.get("chunks_indexed", 0) or 0)
        by_source[source] = row
    return sorted(by_source.values(), key=lambda x: (str(x.get("filename", "")).lower(), str(x.get("source", "")).lower()))
```

Change `list_documents()` body:

```python
    rows = _list_visible_documents_for_user(user)
    return _merge_registry_status(rows, user)
```

- [ ] **Step 5: Run API status test**

Run:

```bash
pytest tests/test_documents_upload_async.py::test_list_documents_includes_pending_registry_records -q
```

Expected: PASS.

- [ ] **Step 6: Run document-related tests**

Run:

```bash
pytest tests/test_document_registry.py tests/test_ingest_queue.py tests/test_documents_upload_async.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/api/routes/documents.py app/core/schemas.py tests/test_documents_upload_async.py
git commit -m "feat: expose document indexing status"
```

---

### Task 5: Frontend Status Display

**Files:**
- Modify: `frontend/src/lib/api-client.ts`
- Modify: `frontend/src/pages/chat/components/DocumentsPanel.tsx`

- [ ] **Step 1: Update API types**

In `frontend/src/lib/api-client.ts`, update the document type to include:

```ts
export type IndexedFileSummary = {
  filename: string;
  source: string;
  chunks: number;
  pages?: number[];
  page_count?: number;
  owner_user_id?: string | null;
  visibility?: string;
  agent_class?: string;
  document_id?: string | null;
  indexing_status?: "pending" | "indexing" | "ready" | "failed" | string;
  indexing_stage?: string;
  indexing_error?: string;
  triplets_written?: number;
};
```

Update upload response type:

```ts
export type UploadResponse = {
  filenames: string[];
  skipped_files: string[];
  visibility_applied: string;
  assigned_agent_classes: Record<string, string>;
  document_ids?: string[];
  indexing_status?: string;
  loaded_documents: number;
  chunks_indexed: number;
  triplets_written: number;
};
```

- [ ] **Step 2: Add compact status label**

In `frontend/src/pages/chat/components/DocumentsPanel.tsx`, add:

```tsx
function documentStatusLabel(status?: string): string {
  if (status === "pending") return "Queued";
  if (status === "indexing") return "Indexing";
  if (status === "failed") return "Failed";
  return "Ready";
}
```

Render near each document filename:

```tsx
<span className={`document-status document-status-${doc.indexing_status || "ready"}`}>
  {documentStatusLabel(doc.indexing_status)}
</span>
```

If `doc.indexing_error` exists, render it in the existing secondary metadata area:

```tsx
{doc.indexing_error ? <span className="document-error">{doc.indexing_error}</span> : null}
```

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS. If `node_modules` is missing, run `npm install` first, then rerun build.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api-client.ts frontend/src/pages/chat/components/DocumentsPanel.tsx
git commit -m "feat: show document indexing status"
```

---

### Task 6: Upload Deduplication

**Files:**
- Create: `app/services/document_dedup.py`
- Modify: `app/api/routes/documents.py`
- Modify: `app/core/schemas.py`
- Test: `tests/test_document_dedup.py`
- Test: `tests/test_documents_upload_async.py`

- [ ] **Step 1: Write failing tests for same-user duplicate detection**

Create `tests/test_document_dedup.py`:

```python
from pathlib import Path

from app.services.document_registry import create_document_record
from app.services.document_dedup import compute_sha256, find_duplicate_for_user


def test_compute_sha256_is_stable(tmp_path: Path):
    path = tmp_path / "note.md"
    path.write_text("hello", encoding="utf-8")

    assert compute_sha256(path) == compute_sha256(path)
    assert len(compute_sha256(path)) == 64


def test_find_duplicate_for_same_user(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    create_document_record(
        source=str(tmp_path / "old.md"),
        filename="old.md",
        sha256="samehash",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    duplicate = find_duplicate_for_user("samehash", "u1", path=registry_path)

    assert duplicate is not None
    assert duplicate["filename"] == "old.md"


def test_find_duplicate_does_not_cross_users(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    create_document_record(
        source=str(tmp_path / "old.md"),
        filename="old.md",
        sha256="samehash",
        owner_user_id="u2",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    assert find_duplicate_for_user("samehash", "u1", path=registry_path) is None
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_document_dedup.py -q
```

Expected: FAIL because `app.services.document_dedup` does not exist.

- [ ] **Step 3: Implement dedup helper**

Create `app/services/document_dedup.py`:

```python
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
```

- [ ] **Step 4: Add upload response fields**

Modify `UploadResponse` in `app/core/schemas.py`:

```python
    duplicate_files: list[str] = Field(default_factory=list)
    reused_document_ids: list[str] = Field(default_factory=list)
```

- [ ] **Step 5: Wire upload route to skip same-user duplicates**

Modify `app/api/routes/documents.py` imports:

```python
from app.services.document_dedup import compute_sha256, find_duplicate_for_user
```

After each file is saved and signature-validated, compute its hash and skip queueing if the same user already has the same hash:

```python
    file_hashes_by_source: dict[str, str] = {}
    duplicate_files: list[str] = []
    reused_document_ids: list[str] = []
```

Inside the file loop after signature validation:

```python
        sha256 = compute_sha256(target)
        duplicate = find_duplicate_for_user(sha256, str(user.get("user_id", "")))
        if duplicate is not None:
            duplicate_files.append(safe_filename)
            reused_document_ids.append(str(duplicate.get("document_id", "")))
            if target.exists():
                target.unlink()
            continue
        file_hashes_by_source[str(target)] = sha256
```

When creating records, use the precomputed hash:

```python
            sha256=file_hashes_by_source[str(p)],
```

Return:

```python
        duplicate_files=duplicate_files,
        reused_document_ids=[x for x in reused_document_ids if x],
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_document_dedup.py tests/test_documents_upload_async.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/document_dedup.py app/api/routes/documents.py app/core/schemas.py tests/test_document_dedup.py tests/test_documents_upload_async.py
git commit -m "feat: skip duplicate document uploads"
```

---

### Task 7: Incremental Reindexing

**Files:**
- Modify: `app/services/document_registry.py`
- Modify: `app/services/index_manager.py`
- Modify: `app/api/routes/documents.py`
- Test: `tests/test_incremental_indexing.py`

- [ ] **Step 1: Write failing tests for unchanged file skip and changed file reindex**

Create `tests/test_incremental_indexing.py`:

```python
from pathlib import Path
from unittest.mock import patch

from app.services.document_registry import create_document_record, get_document_by_source
from app.services.index_manager import should_skip_reindex


def test_should_skip_reindex_when_hash_matches(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    source = tmp_path / "note.md"
    source.write_text("same", encoding="utf-8")
    from app.services.document_dedup import compute_sha256

    create_document_record(
        source=str(source),
        filename="note.md",
        sha256=compute_sha256(source),
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    assert should_skip_reindex(source, registry_path=registry_path) is True


def test_should_not_skip_reindex_when_hash_changes(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    source = tmp_path / "note.md"
    source.write_text("new", encoding="utf-8")

    create_document_record(
        source=str(source),
        filename="note.md",
        sha256="oldhash",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )

    assert should_skip_reindex(source, registry_path=registry_path) is False
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_incremental_indexing.py -q
```

Expected: FAIL because `should_skip_reindex` does not exist.

- [ ] **Step 3: Add registry update by source**

Add to `app/services/document_registry.py`:

```python
def update_document_by_source(source: str, fields: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    row = get_document_by_source(source, path=path)
    if row is None:
        raise ValueError(f"document not found for source: {source}")
    return update_document_record(str(row["document_id"]), fields, path=path)
```

- [ ] **Step 4: Add skip helper**

Modify `app/services/index_manager.py` imports:

```python
from app.services.document_dedup import compute_sha256
from app.services.document_registry import get_document_by_source, update_document_by_source
```

Add:

```python
def should_skip_reindex(path: Path, registry_path: Path | None = None) -> bool:
    record = get_document_by_source(str(path), path=registry_path)
    if record is None:
        return False
    if not path.exists() or not path.is_file():
        return False
    current_hash = compute_sha256(path)
    return str(record.get("sha256", "")) == current_hash and str(record.get("status", "")) == "ready"
```

- [ ] **Step 5: Use skip helper in reindex route**

In `app/api/routes/documents.py`, before calling `rebuild_file_index(...)`, resolve `source_path = Path(source)` and add:

```python
        if should_skip_reindex(source_path):
            return FileIndexActionResponse(
                ok=True,
                filename=filename,
                chunks_indexed=0,
                triplets_written=0,
                skipped=True,
                reason="unchanged_file_hash",
            )
```

If `FileIndexActionResponse` lacks `skipped` and `reason`, add optional fields in `app/core/schemas.py`:

```python
    skipped: bool = False
    reason: str = ""
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_incremental_indexing.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/document_registry.py app/services/index_manager.py app/api/routes/documents.py app/core/schemas.py tests/test_incremental_indexing.py
git commit -m "feat: skip unchanged document reindexing"
```

---

### Task 8: Graph Triplet Quality And Provenance

**Files:**
- Modify: `app/ingestion/graph_extractor.py`
- Modify: `app/services/ingest_service.py`
- Modify: `app/graph/neo4j_client.py`
- Test: `tests/test_graph_triplet_quality.py`

- [ ] **Step 1: Write failing tests for confidence filtering and provenance**

Create `tests/test_graph_triplet_quality.py`:

```python
from app.ingestion.graph_extractor import GraphTriplet, filter_triplets


def test_filter_triplets_drops_low_confidence():
    rows = [
        GraphTriplet(head="A", relation="USES", tail="B", confidence=0.91, method="llm"),
        GraphTriplet(head="A", relation="RELATED_TO", tail="Thing", confidence=0.25, method="rules"),
    ]

    kept = filter_triplets(rows, min_confidence=0.5)

    assert len(kept) == 1
    assert kept[0].relation == "USES"


def test_filter_triplets_dedupes_same_edge():
    rows = [
        GraphTriplet(head="A", relation="USES", tail="B", confidence=0.70, method="rules"),
        GraphTriplet(head="A", relation="USES", tail="B", confidence=0.95, method="llm"),
    ]

    kept = filter_triplets(rows, min_confidence=0.5)

    assert len(kept) == 1
    assert kept[0].confidence == 0.95
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_graph_triplet_quality.py -q
```

Expected: FAIL because `GraphTriplet` and `filter_triplets` do not exist.

- [ ] **Step 3: Add structured triplet model**

Modify `app/ingestion/graph_extractor.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphTriplet:
    head: str
    relation: str
    tail: str
    confidence: float
    method: str
```

Add:

```python
def filter_triplets(triplets: list[GraphTriplet], min_confidence: float = 0.5) -> list[GraphTriplet]:
    best: dict[tuple[str, str, str], GraphTriplet] = {}
    for item in triplets:
        if item.confidence < min_confidence:
            continue
        key = (item.head.strip(), item.relation.strip(), item.tail.strip())
        if not all(key) or key[0] == key[2]:
            continue
        current = best.get(key)
        if current is None or item.confidence > current.confidence:
            best[key] = item
    return list(best.values())
```

Update `extract_triplets(...)` to keep backward compatibility by returning tuples, and add a new function:

```python
def extract_graph_triplets(text: str) -> list[GraphTriplet]:
    raw = extract_triplets(text)
    rows = [
        GraphTriplet(head=head, relation=relation, tail=tail, confidence=0.7, method="legacy")
        for head, relation, tail in raw
    ]
    return filter_triplets(rows)
```

- [ ] **Step 4: Store provenance in Neo4j**

Change `Neo4jClient.upsert_triplet(...)` signature in `app/graph/neo4j_client.py`:

```python
def upsert_triplet(
    self,
    head: str,
    relation: str,
    tail: str,
    source: str,
    chunk_id: str = "",
    page: int | None = None,
    confidence: float = 0.7,
):
```

Extend Cypher `SET` block:

```cypher
        SET r.sources = CASE
            WHEN r.sources IS NULL THEN [$source]
            WHEN $source IN r.sources THEN r.sources
            ELSE r.sources + $source
        END,
        r.chunk_ids = CASE
            WHEN $chunk_id = "" THEN coalesce(r.chunk_ids, [])
            WHEN r.chunk_ids IS NULL THEN [$chunk_id]
            WHEN $chunk_id IN r.chunk_ids THEN r.chunk_ids
            ELSE r.chunk_ids + $chunk_id
        END,
        r.pages = CASE
            WHEN $page IS NULL THEN coalesce(r.pages, [])
            WHEN r.pages IS NULL THEN [$page]
            WHEN $page IN r.pages THEN r.pages
            ELSE r.pages + $page
        END,
        r.confidence_max = CASE
            WHEN r.confidence_max IS NULL OR $confidence > r.confidence_max THEN $confidence
            ELSE r.confidence_max
        END
```

Pass params:

```python
session.run(
    cypher,
    head=head,
    relation=relation,
    tail=tail,
    source=source,
    chunk_id=chunk_id,
    page=page,
    confidence=float(confidence),
)
```

- [ ] **Step 5: Use structured triplets during ingestion**

Modify `app/services/ingest_service.py` import:

```python
from app.ingestion.graph_extractor import extract_graph_triplets
```

Replace graph write loop:

```python
                chunk_id = str(chunk.metadata.get("chunk_id", ""))
                page_raw = chunk.metadata.get("page")
                try:
                    page = int(page_raw) if page_raw is not None else None
                except (TypeError, ValueError):
                    page = None
                for triplet in extract_graph_triplets(text):
                    client.upsert_triplet(
                        head=triplet.head,
                        relation=triplet.relation,
                        tail=triplet.tail,
                        source=source,
                        chunk_id=chunk_id,
                        page=page,
                        confidence=triplet.confidence,
                    )
                    count_triplets += 1
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_graph_triplet_quality.py -q
```

Expected: PASS.

- [ ] **Step 7: Run workflow regression**

Run:

```bash
pytest tests/test_workflow_fixes.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add app/ingestion/graph_extractor.py app/services/ingest_service.py app/graph/neo4j_client.py tests/test_graph_triplet_quality.py
git commit -m "feat: add graph triplet quality metadata"
```

---

### Task 9: Index Health Report API

**Files:**
- Create: `app/services/index_health.py`
- Modify: `app/api/routes/documents.py`
- Modify: `app/core/schemas.py`
- Test: `tests/test_index_health.py`

- [ ] **Step 1: Write failing test for health report**

Create `tests/test_index_health.py`:

```python
from pathlib import Path

from app.services.document_registry import create_document_record, update_document_record
from app.services.index_health import build_index_health_report


def test_build_index_health_report(tmp_path: Path):
    registry_path = tmp_path / "documents.jsonl"
    record = create_document_record(
        source=str(tmp_path / "note.md"),
        filename="note.md",
        sha256="abc123",
        owner_user_id="u1",
        visibility="private",
        agent_class="general",
        path=registry_path,
    )
    update_document_record(
        record["document_id"],
        {"status": "ready", "chunks_indexed": 5, "triplets_written": 2},
        path=registry_path,
    )

    report = build_index_health_report(path=registry_path)

    assert report["total_documents"] == 1
    assert report["ready_documents"] == 1
    assert report["failed_documents"] == 0
    assert report["total_chunks"] == 5
    assert report["total_triplets"] == 2
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_index_health.py -q
```

Expected: FAIL because `index_health` does not exist.

- [ ] **Step 3: Implement health builder**

Create `app/services/index_health.py`:

```python
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
```

- [ ] **Step 4: Add API schema and route**

Add to `app/core/schemas.py`:

```python
class IndexHealthResponse(BaseModel):
    total_documents: int = 0
    ready_documents: int = 0
    failed_documents: int = 0
    indexing_documents: int = 0
    total_chunks: int = 0
    total_triplets: int = 0
    documents: list[dict[str, Any]] = Field(default_factory=list)
```

Modify `app/api/routes/documents.py` imports:

```python
from app.core.schemas import IndexHealthResponse
from app.services.index_health import build_index_health_report
```

Add route:

```python
@router.get("/documents/index-health", response_model=IndexHealthResponse)
def document_index_health(request: Request, user: dict[str, Any] = Depends(_require_user)):
    _require_permission(user, "document:read", request, "document")
    report = build_index_health_report()
    visible_sources = {str(row.get("source", "") or "") for row in _list_visible_documents_for_user(user)}
    report["documents"] = [
        row for row in report["documents"]
        if str(row.get("source", "") or "") in visible_sources
        or str(row.get("owner_user_id", "") or "") == str(user.get("user_id", ""))
    ]
    report["total_documents"] = len(report["documents"])
    report["ready_documents"] = len([r for r in report["documents"] if r.get("status") == "ready"])
    report["failed_documents"] = len([r for r in report["documents"] if r.get("status") == "failed"])
    report["indexing_documents"] = len([r for r in report["documents"] if r.get("status") in {"pending", "indexing"}])
    report["total_chunks"] = sum(int(r.get("chunks_indexed", 0) or 0) for r in report["documents"])
    report["total_triplets"] = sum(int(r.get("triplets_written", 0) or 0) for r in report["documents"])
    return report
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_index_health.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/services/index_health.py app/api/routes/documents.py app/core/schemas.py tests/test_index_health.py
git commit -m "feat: add document index health report"
```

---

### Task 10: Parser Profiles

**Files:**
- Create: `app/services/parser_profiles.py`
- Modify: `app/services/ingest_service.py`
- Modify: `app/ingestion/loaders.py`
- Test: `tests/test_parser_profiles.py`

- [ ] **Step 1: Write failing tests for profile selection**

Create `tests/test_parser_profiles.py`:

```python
from pathlib import Path

from app.services.parser_profiles import choose_parser_profile


def test_pdf_uses_pdf_profile():
    profile = choose_parser_profile(Path("report.pdf"), agent_class="pdf_text")

    assert profile["name"] == "pdf_text"
    assert profile["enable_graph"] is True
    assert profile["loader_hint"] == "pdf"


def test_image_uses_ocr_profile():
    profile = choose_parser_profile(Path("scan.png"), agent_class="pdf_text")

    assert profile["name"] == "image_ocr"
    assert profile["loader_hint"] == "image"


def test_policy_filename_uses_policy_profile():
    profile = choose_parser_profile(Path("security-policy.md"), agent_class="policy")

    assert profile["name"] == "policy"
    assert profile["enable_graph"] is True
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_parser_profiles.py -q
```

Expected: FAIL because `parser_profiles` does not exist.

- [ ] **Step 3: Implement profile selector**

Create `app/services/parser_profiles.py`:

```python
from __future__ import annotations

from pathlib import Path

from app.ingestion.loaders import IMAGE_EXTENSIONS


def choose_parser_profile(path: Path, agent_class: str = "general") -> dict:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return {
            "name": "pdf_text",
            "loader_hint": "pdf",
            "enable_graph": True,
            "graph_min_confidence": 0.55,
        }
    if suffix in IMAGE_EXTENSIONS:
        return {
            "name": "image_ocr",
            "loader_hint": "image",
            "enable_graph": False,
            "graph_min_confidence": 0.75,
        }
    if agent_class == "policy" or "policy" in path.stem.lower():
        return {
            "name": "policy",
            "loader_hint": "text",
            "enable_graph": True,
            "graph_min_confidence": 0.6,
        }
    return {
        "name": "general_text",
        "loader_hint": "text",
        "enable_graph": True,
        "graph_min_confidence": 0.65,
    }
```

- [ ] **Step 4: Store parser profile in registry metadata**

When creating upload records in `app/api/routes/documents.py`, compute:

```python
from app.services.parser_profiles import choose_parser_profile
```

Before `create_document_record(...)`:

```python
        parser_profile = choose_parser_profile(p, assigned_agent_classes.get(str(p), "general"))
```

Pass extra field after Task 1's registry accepts arbitrary fields:

```python
            parser_profile=parser_profile["name"],
```

If `create_document_record(...)` has a fixed signature, extend it:

```python
    parser_profile: str = "",
```

and add `"parser_profile": parser_profile` to the incoming record.

- [ ] **Step 5: Pass profile into ingestion**

Modify `ingest_paths(...)` signature in `app/services/ingest_service.py`:

```python
def ingest_paths(
    paths: list[Path],
    reset_vector_store: bool = False,
    metadata_overrides_by_source: dict[str, dict[str, Any]] | None = None,
    parser_profiles_by_source: dict[str, dict[str, Any]] | None = None,
) -> dict:
```

In the graph write section, skip graph extraction when profile says disabled:

```python
                profile = (parser_profiles_by_source or {}).get(source, {})
                if profile.get("enable_graph") is False:
                    continue
```

- [ ] **Step 6: Run tests**

Run:

```bash
pytest tests/test_parser_profiles.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/parser_profiles.py app/services/ingest_service.py app/api/routes/documents.py tests/test_parser_profiles.py
git commit -m "feat: select parser profiles per document"
```

---

### Task 11: Frontend Health And Optimization Visibility

**Files:**
- Modify: `frontend/src/lib/api-client.ts`
- Modify: `frontend/src/pages/chat/components/DocumentsPanel.tsx`
- Modify: `frontend/src/styles/features/graph.css` or existing document panel stylesheet

- [ ] **Step 1: Add health API client**

In `frontend/src/lib/api-client.ts`, add:

```ts
export type IndexHealthResponse = {
  total_documents: number;
  ready_documents: number;
  failed_documents: number;
  indexing_documents: number;
  total_chunks: number;
  total_triplets: number;
  documents: IndexedFileSummary[];
};

export async function fetchIndexHealth(): Promise<IndexHealthResponse> {
  return apiGet<IndexHealthResponse>("/api/documents/index-health");
}
```

- [ ] **Step 2: Display document optimization metadata**

In `DocumentsPanel.tsx`, show compact metadata when available:

```tsx
{typeof doc.triplets_written === "number" ? (
  <span className="document-metric">Graph {doc.triplets_written}</span>
) : null}
{doc.agent_class ? <span className="document-metric">{doc.agent_class}</span> : null}
{doc.indexing_stage ? <span className="document-metric">{doc.indexing_stage}</span> : null}
```

- [ ] **Step 3: Add restrained styles**

Add to the existing document panel stylesheet:

```css
.document-status,
.document-metric {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1;
  background: var(--surface-muted);
  color: var(--text-secondary);
}

.document-status-failed {
  background: var(--danger-surface);
  color: var(--danger-text);
}

.document-error {
  color: var(--danger-text);
  font-size: 12px;
}
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api-client.ts frontend/src/pages/chat/components/DocumentsPanel.tsx frontend/src/styles/features/graph.css
git commit -m "feat: show document index health metadata"
```

---

## Final Verification

- [ ] **Run backend focused tests**

```bash
pytest tests/test_document_registry.py tests/test_ingest_queue.py tests/test_documents_upload_async.py tests/test_document_dedup.py tests/test_incremental_indexing.py tests/test_graph_triplet_quality.py tests/test_index_health.py tests/test_parser_profiles.py -q
```

Expected: PASS.

- [ ] **Run workflow regression tests**

```bash
pytest tests/test_workflow_fixes.py -q
```

Expected: PASS.

- [ ] **Run full backend test suite when time allows**

```bash
pytest -q
```

Expected: PASS or only environment-blocked failures that already existed before this work.

- [ ] **Run frontend build**

```bash
cd frontend
npm run build
```

Expected: PASS.

---

## Rollback Plan

If async ingestion causes production issues:

1. Revert the upload route to call `ingest_paths()` synchronously.
2. Keep `document_registry.py` in place because it is additive and does not change retrieval behavior.
3. Keep list endpoint status fields defaulting to `ready` for existing indexed files.
4. Delete or disable calls to `enqueue_ingest_job()` until worker behavior is fixed.

---

## Self-Review

- Spec coverage: This plan covers document registry, async indexing, status visibility, upload behavior, and frontend display.
- Placeholder scan: No open-ended implementation placeholders remain; every task has concrete file paths, code snippets, and commands.
- Type consistency: Registry fields are consistent across backend store, upload response, document listing, and frontend types.
