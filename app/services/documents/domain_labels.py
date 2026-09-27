"""Which specialist domain a document is labelled with, looked up at query time.

The label lives in the document registry (`documents.jsonl`, `agent_class`),
set at upload and editable afterwards. It is deliberately NOT read from chunk
metadata: a label copied into every chunk can only change by reindexing, and a
registry lookup makes relabelling take effect on the next question.

This replaced `app/services/documents/agent_scope.py`, which read the label from
`metadata["agent"]` in the corpus JSONL -- a key nothing ever wrote -- and used
it as a *filter*. Had anything called it with a class, every specialist's scope
would have been empty. A label now only orders results the caller may already
see; it never decides what they may see.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.agents.catalog import normalize_agent_class
from app.services.documents.registry import _default_path, list_document_records

__all__ = ["DomainLabels", "folder_label", "load_domain_labels"]


def _shared_root() -> str:
    from app.core.config import get_settings

    try:
        return str(get_settings().docs_path.resolve())
    except OSError:
        return ""


@dataclass(frozen=True)
class DomainLabels:
    by_document_id: dict[str, str]
    by_source: dict[str, str]
    shared_root: str = ""

    def label_of(self, document_id: str | None, source: str | None) -> str | None:
        """The item's domain label: registry id, then stored path, then shared-corpus folder.

        Chunks carry the registry `document_id`; the source path is the fallback
        for rows indexed before that id existed. A file in the shared corpus has
        no registry row at all, so its label is the folder it sits in
        (`data/docs/compliance/...` is `compliance`) -- which is how the bundled
        regulations and an administrator's own reference documents get one.
        """

        if document_id and document_id in self.by_document_id:
            return self.by_document_id[document_id]
        if source and source in self.by_source:
            return self.by_source[source]
        if source and self.shared_root:
            return folder_label(source, self.shared_root)
        return None


@lru_cache(maxsize=4096)
def folder_label(source: str, shared_root: str) -> str | None:
    """The agent class named by the first folder under the shared corpus, if any.

    Only a folder: a file directly in the shared corpus carries no label, and a
    folder name that is not an agent class is not one either.
    """

    try:
        relative = Path(source).resolve().relative_to(Path(shared_root))
    except (ValueError, OSError):
        return None
    if len(relative.parts) < 2:
        return None
    return normalize_agent_class(relative.parts[0])


_cache: tuple[tuple[str, str, int, int], DomainLabels] | None = None
_cache_lock = threading.Lock()


def load_domain_labels(path: Path | None = None) -> DomainLabels:
    """Every document's label, re-read only when the registry file changes.

    Keyed on the file's modification time and size: the registry is replaced
    atomically on every write, so a relabel on any worker is seen here on the
    next question without a cross-process invalidation of its own.
    """

    global _cache
    target = path or _default_path()
    shared_root = _shared_root()
    try:
        stat = target.stat()
    except FileNotFoundError:
        # No uploads yet: the shared corpus's folders are still labels.
        return DomainLabels(by_document_id={}, by_source={}, shared_root=shared_root)
    key = (str(target), shared_root, stat.st_mtime_ns, stat.st_size)
    with _cache_lock:
        if _cache is not None and _cache[0] == key:
            return _cache[1]

    by_id: dict[str, str] = {}
    by_source: dict[str, str] = {}
    for row in list_document_records(target):
        # Normalized, so a row written as `policy` before the compliance
        # specialist existed reads as `compliance`.
        label = normalize_agent_class(str(row.get("agent_class") or "")) or ""
        if not label:
            continue
        if row.get("document_id"):
            by_id[str(row["document_id"])] = label
        if row.get("source"):
            by_source[str(row["source"])] = label
    labels = DomainLabels(by_document_id=by_id, by_source=by_source, shared_root=shared_root)
    with _cache_lock:
        _cache = (key, labels)
    return labels
