"""Compare the stores a document lives in and report (or repair) what drifted.

Deleting or ingesting a document touches the corpus, the registry, the vector
collections, the structured tables and, optionally, the graph. They are separate
stores with no shared transaction, so an interrupted operation leaves rows that
nothing names. This module finds them:

* vectors in the main collection that no corpus row names, and the reverse;
* image / table vectors and SQL tables whose source has no corpus chunks;
* registry rows marked ``delete_failed`` (a delete that left rows behind);
* registry rows whose file is gone from disk.

Report-only by default. ``repair=True`` removes only what is derived and
therefore unreachable: orphan vectors, and orphan table / image / table-summary
rows. It never deletes corpus chunks, registry rows or files.

    python -m app.services.documents.reconcile [--repair]
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.retrievers.stores.corpus import read_corpus_records
from app.services.documents.index_lock import index_writes
from app.services.documents.index_manager import (
    MULTIMODAL_COLLECTIONS,
    _delete_multimodal_by_sources,
    _delete_tables_by_sources,
    _delete_vector_documents,
    _record_source,
)
from app.services.documents.registry import list_document_records

logger = logging.getLogger(__name__)


@dataclass
class ReconcileReport:
    orphan_vector_ids: list[str] = field(default_factory=list)
    corpus_ids_without_vector: list[str] = field(default_factory=list)
    orphan_table_sources: list[str] = field(default_factory=list)
    orphan_multimodal_sources: dict[str, list[str]] = field(default_factory=dict)
    delete_failed: list[str] = field(default_factory=list)
    registry_missing_file: list[str] = field(default_factory=list)
    repaired: dict[str, int] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (
            self.orphan_vector_ids
            or self.corpus_ids_without_vector
            or self.orphan_table_sources
            or any(self.orphan_multimodal_sources.values())
            or self.delete_failed
            or self.registry_missing_file
        )

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "clean": self.clean}


def _vector_ids() -> set[str]:
    from app.retrievers.stores.vector import get_vector_store

    return {str(i) for i in get_vector_store()._collection.get(include=[])["ids"]}  # noqa: SLF001


def _collection_sources(name: str) -> set[str]:
    from app.retrievers.stores.vector import get_named_vector_store

    metadatas = get_named_vector_store(name)._collection.get(include=["metadatas"])["metadatas"] or []  # noqa: SLF001
    return {str(m.get("source", "")) for m in metadatas if m and m.get("source")}


def _table_sources() -> set[str]:
    from app.services.tables.store import get_table_store

    return get_table_store().sources()


def _probe(report: ReconcileReport, name: str, fn: Any) -> Any:
    """A store that cannot be read is reported as skipped, never as empty."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - any backend failure means "could not look"
        logger.warning("reconcile: could not read %s: %s", name, exc)
        report.skipped.append(name)
        return None


def reconcile_index(*, repair: bool = False) -> ReconcileReport:
    report = ReconcileReport()
    with index_writes():
        records = read_corpus_records()
        corpus_ids = {str(r["id"]) for r in records if r.get("id")}
        corpus_sources = {_record_source(r) for r in records if _record_source(r)}

        vector_ids = _probe(report, "vectors", _vector_ids)
        if vector_ids is not None:
            report.orphan_vector_ids = sorted(vector_ids - corpus_ids)
            report.corpus_ids_without_vector = sorted(corpus_ids - vector_ids)

        table_sources = _probe(report, "tables", _table_sources)
        if table_sources is not None:
            report.orphan_table_sources = sorted(table_sources - corpus_sources)

        for name in MULTIMODAL_COLLECTIONS:
            found = _probe(report, name, lambda n=name: _collection_sources(n))
            if found is not None:
                report.orphan_multimodal_sources[name] = sorted(found - corpus_sources)

        for row in list_document_records():
            source = str(row.get("source", "") or "")
            if str(row.get("status", "")) == "delete_failed":
                report.delete_failed.append(source)
            if source and not Path(source).is_file():
                report.registry_missing_file.append(source)

        if repair:
            _repair(report)
    return report


def _repair(report: ReconcileReport) -> None:
    if report.orphan_vector_ids:
        _delete_vector_documents(report.orphan_vector_ids)
        report.repaired["vectors"] = len(report.orphan_vector_ids)
    if report.orphan_table_sources:
        report.repaired["tables"] = _delete_tables_by_sources(report.orphan_table_sources)
    orphans = sorted({s for group in report.orphan_multimodal_sources.values() for s in group})
    if orphans:
        _delete_multimodal_by_sources(orphans)
        report.repaired["multimodal_sources"] = len(orphans)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repair", action="store_true", help="delete orphan derived rows (default: report only)")
    args = parser.parse_args(argv)
    report = reconcile_index(repair=args.repair)
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    return 0 if report.clean or args.repair else 1


if __name__ == "__main__":
    raise SystemExit(main())
