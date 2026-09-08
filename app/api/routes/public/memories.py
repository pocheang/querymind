"""What this system remembers about the person using it, and how to forget it.

`_promote_long_term_memory` runs on every answered query and
`build_memory_context` feeds the result back into the next one, so the system
accumulates memories about a user and uses them to shape later answers. Until
this router there was no way to see that or undo it.

The two session-scoped endpoints next door are not that way, and it is worth
being precise about why, because they look like they are. `list_long_term`
returns a session's *working set* -- the memories one conversation would be
given -- which `_recompute_long_term_ids` caps at `LONG_TERM_TOP_N`. Measured on
ten promotions: nine memories stored, five listed, and a different five
depending on which session asked. A record has to show all of it.

Everything here is scoped by `_memory_store_for_user`, which keys the store on
tenant and user id, so there is no memory of another person's reachable from
these handlers and no id a caller could guess into one.
"""

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps.auth import _require_permission, _require_user
from app.api.schemas import ForgetMemoryResponse, StoredMemoryItem, StoredMemoryList
from app.api.transport.errors import not_found
from app.api.utils.auth_helpers import _audit

# Imported from the modules that define them rather than through
# `app.api.dependencies`, whose `__getattr__` exists to resolve legacy imports.
from app.api.utils.memory_helpers import _memory_store_for_user
from app.services.security.audit_actions import AuditAction
from app.services.security.rbac import Permission
from app.services.sessions.memory_store import memory_is_expired

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


def _as_item(row: dict[str, Any]) -> StoredMemoryItem:
    """Render one stored row as the record the caller is owed.

    `content` falls back to `answer` because rows written before the resolver
    existed carry only the exchange. Reporting an empty memory for those would
    show somebody a row they cannot identify and cannot judge.
    """

    expires_at = row.get("expires_at")
    return StoredMemoryItem(
        memory_id=str(row.get("candidate_id") or ""),
        kind=str(row.get("kind") or ""),
        content=str(row.get("content") or row.get("answer") or ""),
        score=float(row.get("score") or 0.0),
        active=not memory_is_expired(expires_at if expires_at is None else str(expires_at)),
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        updated_at=str(row["updated_at"]) if row.get("updated_at") else None,
        expires_at=str(expires_at) if expires_at else None,
        source_session_id=str(row["source_session_id"]) if row.get("source_session_id") else None,
    )


@router.get("", response_model=StoredMemoryList)
def list_memories(request: Request, user: dict[str, Any] = Depends(_require_user)):
    """Every long-term memory stored for the caller, newest first.

    Expired memories are returned and marked `active: false` rather than
    hidden. They are still on disk, so a page that omitted them would answer
    "what do you still hold about me" with something other than the truth --
    and the caller can then delete one, which is the whole point of the page.
    """

    _require_permission(user, Permission.SESSION_READ, request, "memory")
    rows = _memory_store_for_user(user).list_all()
    items = [_as_item(row) for row in rows if row.get("candidate_id")]
    return StoredMemoryList(memories=items, total=len(items))


@router.delete("/{memory_id}", response_model=ForgetMemoryResponse)
def forget_memory(memory_id: str, request: Request, user: dict[str, Any] = Depends(_require_user)):
    """Forget one memory, everywhere this user's store holds it."""

    _require_permission(user, Permission.SESSION_READ, request, "memory", resource_id=memory_id)
    if not _memory_store_for_user(user).forget(memory_id):
        raise not_found("Memory")
    _audit(
        request,
        action=AuditAction.MEMORY_LONG_DELETE,
        resource_type="memory",
        result="success",
        user=user,
        resource_id=memory_id,
    )
    return ForgetMemoryResponse(memory_id=memory_id, forgotten=1)


@router.delete("", response_model=ForgetMemoryResponse)
def forget_all_memories(request: Request, user: dict[str, Any] = Depends(_require_user)):
    """Forget everything stored about the caller.

    Not a 404 when there was nothing to forget: "you now hold no memories about
    me" is what was asked for and it is true either way, and answering "not
    found" to a request that has been satisfied invites a retry.
    """

    _require_permission(user, Permission.SESSION_READ, request, "memory")
    forgotten = _memory_store_for_user(user).forget_all()
    _audit(
        request,
        action=AuditAction.MEMORY_LONG_PURGE,
        resource_type="memory",
        result="success",
        user=user,
        detail=f"forgotten={forgotten}",
    )
    return ForgetMemoryResponse(forgotten=forgotten)
