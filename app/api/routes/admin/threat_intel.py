"""Admin view and control of the offline threat-intelligence store.

Status is read from the sync record; a sync runs off the request path on the
process's background queue, and a second sync of the same source -- on any
worker -- is answered `busy` by the store's cross-process lock rather than run
twice. Sync is manual by default (decision Q2, 2026-09-27); a deployment that
may reach the internet schedules `scripts/sync_threat_intel.py` from the host.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.api import dependencies as api_dependencies
from app.api.dependencies import _audit, _require_permission, _require_user
from app.api.transport.errors import service_unavailable
from app.core.config import get_settings
from app.services.security.audit_actions import AuditAction
from app.services.security.rbac import Permission
from app.services.threat_intel.status import get_threat_intel_store, source_statuses
from app.services.threat_intel.store import SOURCES
from app.services.threat_intel.sync import sync_source

router = APIRouter(prefix="/admin/threat-intel", tags=["admin", "threat-intel"])


class ThreatIntelSyncRequest(BaseModel):
    source: Literal["all", "nvd", "kev", "epss", "attack"] = "all"


@router.get("/status")
def threat_intel_status(request: Request, user: dict[str, Any] = Depends(_require_user)) -> dict[str, Any]:
    """Per source: rows held, last successful sync, age, whether it is stale, and the last attempt."""

    _require_permission(user, Permission.ADMIN_OPS_MANAGE, request, "admin")
    store = get_threat_intel_store()
    return {"sources": [status.as_dict() for status in source_statuses(store)]}


@router.post("/sync", status_code=202)
def threat_intel_sync(
    body: ThreatIntelSyncRequest, request: Request, user: dict[str, Any] = Depends(_require_user)
) -> dict[str, Any]:
    """Queue a sync. NVD's first full sync takes hours without an API key; use the CLI for that one."""

    _require_permission(user, Permission.ADMIN_OPS_MANAGE, request, "admin")
    sources = SOURCES if body.source == "all" else (body.source,)
    store = get_threat_intel_store()
    proxy = get_settings().web_proxy_url or None

    def run_all() -> None:
        for source in sources:
            sync_source(source, store, proxy=proxy)

    if not api_dependencies.get_query_runtime().shadow_queue.submit(run_all):
        raise service_unavailable("background queue is full; retry shortly")
    _audit(
        request,
        action=AuditAction.ADMIN_THREAT_INTEL_SYNC,
        resource_type="admin",
        result="accepted",
        user=user,
        detail=f"sources={','.join(sources)}",
    )
    return {"ok": True, "status": "accepted", "sources": list(sources)}
