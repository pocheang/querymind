"""Which organization a document belongs to, and moving it when that changes (BUG-04).

A user belongs to one organization (`users.tenant_id`, `DEFAULT_TENANT_ID` unless an
administrator moves them). A document carries its owner's organization as
`tenant_id` in every store it is written to, and a `public` document is visible to
everyone in that organization -- never across one.

Before this, the user *was* the tenant: uploads were tagged with the uploader's
`user_id`, so the tenant boundary in `access_scope._within_reach` ran ahead of the
`public` grant and a document approved as public stayed visible to its uploader
alone. Two operations fix that and keep it fixed:

* `retag_owner` moves one owner's documents to an organization, in every store that
  filters on `tenant_id`: the registry, the chunk and parent JSONL, the main and the
  image/table vector collections (metadata only, nothing is re-embedded) and the
  structured tables. It runs when an administrator moves a user, and it is what
  "documents follow their owner" means.
* `migrate_legacy_document_tenants` runs once per installation: every document still
  tagged with its owner's `user_id` is moved to that owner's organization.

Not moved, on purpose: evidence artifacts (their URIs are paths that keep resolving,
and a re-ingest writes a new copy under the new organization), the knowledge graph
(`Source.tenant_id` is written and never read; graph reads are scoped by source),
long-term memory and session history (both are the person's, keyed by user id).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# A tenant id is a path segment in some stores and a metadata value in others.
_TENANT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
_MIGRATION_MARKER = ".tenants-migrated-v1"


def validate_tenant_id(value: str) -> str:
    """The id an administrator may give an organization; raises ValueError otherwise."""

    from app.retrievers.stores.vector import SHARED_CORPUS_TENANT

    tenant_id = str(value or "").strip()
    if not _TENANT_ID_RE.fullmatch(tenant_id):
        raise ValueError("tenant id must be 1-64 letters, digits, '_' or '-', starting with a letter or digit")
    if tenant_id == SHARED_CORPUS_TENANT:
        # The shared corpus is the one tenant every viewer is inside; an
        # organization with that name would make its private documents everyone's.
        raise ValueError(f"'{SHARED_CORPUS_TENANT}' is reserved for the shared corpus")
    return tenant_id


def tenant_of(user: Any) -> str:
    """The organization of a signed-in user dict (or a mapping-like actor).

    A dict without `tenant_id` -- a test double, or a caller built before the
    column existed -- falls back to the user id, which is the old shape and keeps
    such a caller inside its own documents rather than someone else's.
    """

    getter = user.get if hasattr(user, "get") else (lambda key, default=None: getattr(user, key, default))
    return str(getter("tenant_id", "") or getter("user_id", "") or "").strip()


def tenant_for_user(user_id: str) -> str:
    """The organization a user belongs to now, read from the users table."""

    from app.core.config import get_settings
    from app.services.auth.auth_service import AuthDBService

    default = get_settings().default_tenant_id
    if not user_id:
        return default
    try:
        profile = AuthDBService().get_user_profile(user_id) or {}
    except Exception:  # noqa: BLE001 - an unreadable users table must not stop an ingest
        logger.warning("tenant lookup failed; using the default organization", exc_info=True)
        return default
    return str(profile.get("tenant_id") or default)


@dataclass
class RetagReport:
    registry: int = 0
    chunks: int = 0
    parents: int = 0
    vectors: dict[str, int] = field(default_factory=dict)
    tables: int = 0

    @property
    def total(self) -> int:
        return self.registry + self.chunks + self.parents + sum(self.vectors.values()) + self.tables


def _retag_rows(rows: list[dict[str, Any]], owner_user_id: str, tenant_id: str, only_from: str | None) -> int:
    moved = 0
    for row in rows:
        metadata = row.get("metadata") or {}
        if str(metadata.get("owner_user_id", "") or "") != owner_user_id:
            continue
        current = str(metadata.get("tenant_id", "") or "")
        if current == tenant_id or (only_from is not None and current != only_from):
            continue
        metadata["tenant_id"] = tenant_id
        row["metadata"] = metadata
        moved += 1
    return moved


def retag_owner(owner_user_id: str, tenant_id: str, *, only_from: str | None = None) -> RetagReport:
    """Move one owner's documents to `tenant_id` in every store; idempotent.

    `only_from` limits the move to rows still tagged with that tenant -- the
    one-time migration uses the owner's own user id there, so a document that
    was already moved is left alone. Takes the index write lock (a caller on a
    request path holds `request_index_writes` around it, which bounds the wait).
    """

    from app.retrievers.stores.corpus import read_corpus_records, write_corpus_records
    from app.retrievers.stores.parent import read_parent_records, write_parent_records
    from app.retrievers.stores.vector import retag_owner_metadata
    from app.services.documents.index_lock import index_writes
    from app.services.documents.index_manager import MULTIMODAL_COLLECTIONS, _reset_bm25, _reset_retrieval_cache
    from app.services.documents.registry import retag_owner_documents
    from app.services.runtime.invalidation import announce
    from app.services.tables.store import get_table_store

    report = RetagReport()
    with index_writes():
        report.registry = retag_owner_documents(owner_user_id, tenant_id, only_from=only_from)

        chunks = read_corpus_records()
        report.chunks = _retag_rows(chunks, owner_user_id, tenant_id, only_from)
        if report.chunks:
            write_corpus_records(chunks)
        parents = read_parent_records()
        report.parents = _retag_rows(parents, owner_user_id, tenant_id, only_from)
        if report.parents:
            write_parent_records(parents)

        for collection in (None, *MULTIMODAL_COLLECTIONS):
            report.vectors[collection or "chunks"] = retag_owner_metadata(
                collection, owner_user_id, tenant_id, only_from
            )
        report.tables = get_table_store().retag_owner(owner_user_id, tenant_id, only_from=only_from)

        if report.total:
            _reset_bm25()
            _reset_retrieval_cache()
            announce("corpus")
    return report


def migrate_legacy_document_tenants(app_db_path: Path) -> list[str]:
    """Move every document still tagged with its owner's user id to the owner's organization.

    Once per installation (a marker beside the application database). Returns
    problems; the marker is written only when there were none, so a failed run
    is retried at the next start. Until it has run, an owner still reaches their
    own documents (`_within_reach` lets an owner through the tenant boundary);
    what waits for it is other members seeing the ones marked public.
    """

    from app.services.auth.auth_service import AuthDBService

    marker = Path(app_db_path).parent / _MIGRATION_MARKER
    if marker.exists():
        return []
    problems: list[str] = []
    moved = 0
    for user in AuthDBService().list_users():
        user_id = str(user.get("user_id") or "")
        tenant_id = str(user.get("tenant_id") or "")
        if not user_id or not tenant_id or tenant_id == user_id:
            continue
        try:
            moved += retag_owner(user_id, tenant_id, only_from=user_id).total
        except Exception as exc:  # noqa: BLE001 - reported, and the run is retried
            problems.append(f"documents of {user_id} not moved to {tenant_id}: {exc}")
    if not problems:
        marker.write_text(f"{moved} rows moved to their owners' organizations\n", encoding="utf-8")
        if moved:
            logger.info("tenant_migration moved=%d", moved)
    return problems
