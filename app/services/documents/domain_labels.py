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
from pathlib import Path

from app.services.documents.registry import _default_path, list_document_records

__all__ = ["DomainLabels", "load_domain_labels"]


@dataclass(frozen=True)
class DomainLabels:
    by_document_id: dict[str, str]
    by_source: dict[str, str]

    def label_of(self, document_id: str | None, source: str | None) -> str | None:
        """The item's domain label, by registry id first and stored path second.

        Chunks carry the registry `document_id`; the source path is the fallback
        for rows indexed before that id existed.
        """

        if document_id and document_id in self.by_document_id:
            return self.by_document_id[document_id]
        if source and source in self.by_source:
            return self.by_source[source]
        return None


_EMPTY = DomainLabels(by_document_id={}, by_source={})
_cache: tuple[tuple[str, int, int], DomainLabels] | None = None
_cache_lock = threading.Lock()


def load_domain_labels(path: Path | None = None) -> DomainLabels:
    """Every document's label, re-read only when the registry file changes.

    Keyed on the file's modification time and size: the registry is replaced
    atomically on every write, so a relabel on any worker is seen here on the
    next question without a cross-process invalidation of its own.
    """

    global _cache
    target = path or _default_path()
    try:
        stat = target.stat()
    except FileNotFoundError:
        return _EMPTY
    key = (str(target), stat.st_mtime_ns, stat.st_size)
    with _cache_lock:
        if _cache is not None and _cache[0] == key:
            return _cache[1]

    by_id: dict[str, str] = {}
    by_source: dict[str, str] = {}
    for row in list_document_records(target):
        label = str(row.get("agent_class") or "").strip().lower()
        if not label:
            continue
        if row.get("document_id"):
            by_id[str(row["document_id"])] = label
        if row.get("source"):
            by_source[str(row["source"])] = label
    labels = DomainLabels(by_document_id=by_id, by_source=by_source)
    with _cache_lock:
        _cache = (key, labels)
    return labels
