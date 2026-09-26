"""Copy the embedded Chroma store into a Chroma server (ARC-01 phase 5).

`STATE_BACKEND=shared` requires `CHROMA_SERVER_URL`, because the embedded store
under `CHROMA_PERSIST_DIR` can only be written by one process. An installation
switching over keeps its vectors only if they are copied first; this is that
copy, used by `scripts/migrate_chroma_to_server.py`.

The vectors are copied as stored, not re-embedded: re-embedding would take as
long as the original ingest and would silently change them if the embedding
model had changed since. Copying is an upsert by id, so a second run adds what
is missing and rewrites nothing else. The embedded directory is never touched.

Verification reads back: every id read from the source must be found in the
target collection of the same name. Counting what was sent would pass a copy
into a misnamed collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_INCLUDE = ["embeddings", "documents", "metadatas"]


@dataclass
class CollectionCopy:
    name: str
    source_count: int = 0
    copied: int = 0
    missing_after: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return not self.missing_after and self.copied == self.source_count


def _names(client: Any) -> list[str]:
    return sorted(getattr(c, "name", c) for c in client.list_collections())


def _page(collection: Any, offset: int, batch_size: int) -> dict[str, Any]:
    return collection.get(include=_INCLUDE, limit=batch_size, offset=offset)


def _upsert(target: Any, page: dict[str, Any]) -> None:
    metadatas = page.get("metadatas")
    kwargs: dict[str, Any] = {"ids": page["ids"], "embeddings": page["embeddings"], "documents": page["documents"]}
    # Chroma rejects an empty metadata dict, and a row stored without metadata
    # comes back as None; send metadata only when every row in the page has some.
    if metadatas is not None and all(metadatas):
        kwargs["metadatas"] = metadatas
    target.upsert(**kwargs)


def _missing(target: Any, ids: list[str]) -> list[str]:
    found = set(target.get(ids=ids, include=[])["ids"])
    return [identifier for identifier in ids if identifier not in found]


def copy_collection(source_client: Any, target_client: Any, name: str, *, batch_size: int = 500) -> CollectionCopy:
    source = source_client.get_collection(name)
    target = target_client.get_or_create_collection(name, metadata=source.metadata or None)
    report = CollectionCopy(name=name, source_count=source.count())
    offset = 0
    while True:
        page = _page(source, offset, batch_size)
        if not page["ids"]:
            break
        _upsert(target, page)
        report.copied += len(page["ids"])
        report.missing_after.extend(_missing(target, page["ids"]))
        offset += len(page["ids"])
    return report


def copy_collections(source_client: Any, target_client: Any, *, batch_size: int = 500) -> list[CollectionCopy]:
    return [
        copy_collection(source_client, target_client, name, batch_size=batch_size) for name in _names(source_client)
    ]


def describe_collections(client: Any) -> dict[str, int]:
    return {name: client.get_collection(name).count() for name in _names(client)}
