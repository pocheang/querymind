"""Secret-free audit sink for MCP tool decisions, written to the application's audit log.

Until ARC-01 phase 2c this was a Python list "used until a durable service is
configured", and none ever was (SEC-10): every governed tool decision -- including
the approval-gated writes, the one path that most needs a record -- lived in one
process's memory, unbounded, gone at restart, and invisible to the admin audit
view, which reads `audit_logs`. It now writes there, hash-chained like every
other audit row.

`append` is called from `ToolRegistry._finish` on the event loop, and an audit
row is a `BEGIN IMMEDIATE` SQLite transaction. So `append` only enqueues and
returns -- the rule CLAUDE.md sets for reporters that need I/O -- and one daemon
thread writes. The queue is bounded: under a sustained write failure the choice
is between blocking requests and dropping records, and a dropped record is
logged at ERROR with a running count rather than silently lost.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

from app.mcp.contracts import AuditRecord
from app.services.runtime.background_writer import BackgroundWriter
from app.services.security.audit_actions import AuditAction

logger = logging.getLogger(__name__)

_MAX_PENDING = 1_000


def action_for(record: AuditRecord) -> AuditAction:
    """`tool.approval_required` for a call held for a human; `tool.invoke` for every outcome."""

    if record.status == "approval_required":
        return AuditAction.TOOL_APPROVAL_REQUIRED
    return AuditAction.TOOL_INVOKE


def _detail(record: AuditRecord) -> str:
    """Only what `AuditRecord` already carries, which is secret-free by construction:
    argument *names*, never values."""

    return json.dumps(
        {
            "connector_id": record.connector_id,
            "approved_by": record.approved_by,
            "argument_names": list(record.argument_names),
            "execution_id": record.execution_id,
            "duration_ms": record.duration_ms,
            "summary": record.summary,
        },
        ensure_ascii=False,
    )


class _AuditLogsWriter:
    """Writes to `audit_logs` through the auth service, opened once on the writer thread.

    Which database is decided here, when the log is created, not on the writer
    thread at its first write: by then the settings may name another one.
    """

    def __init__(self) -> None:
        from app.core.config import get_settings

        self._db_path = get_settings().app_db_path
        self._service = None

    def __call__(self, record: AuditRecord) -> None:
        if self._service is None:
            from app.services.auth.auth_service import AuthDBService

            self._service = AuthDBService(db_path=self._db_path)
        self._service.add_audit_log(
            action=str(action_for(record)),
            resource_type="tool",
            result=record.status,
            actor_user_id=None if record.actor_id == "anonymous" else record.actor_id,
            resource_id=record.tool_id,
            detail=_detail(record),
        )


class AuditLog:
    """Queue tool audit records and write them to `audit_logs` off the request path."""

    def __init__(self, write: Callable[[AuditRecord], None] | None = None) -> None:
        self._write = write or _AuditLogsWriter()
        self._writer = BackgroundWriter("tool_audit", max_pending=_MAX_PENDING)

    @property
    def dropped(self) -> int:
        return self._writer.dropped

    def append(self, record: AuditRecord) -> None:
        """Enqueue and return. Never blocks and never raises into the tool call."""

        self._writer.submit(lambda: self._write(record), label=f"tool={record.tool_id} status={record.status}")

    def flush(self, timeout: float = 5.0) -> bool:
        """Wait until every queued record has been handled. True if the queue drained in time."""

        return self._writer.flush(timeout)
