"""Queued tool-audit rows must not outlive the stack that queued them (found in ARC-01 phase 7).

Two connector test files failed intermittently with `FOREIGN KEY constraint
failed` -- 1 run in 12 before phase 7, 3 in 12 after it made opening the auth
store slower. Instrumenting the failure showed the connector repository writing
to the *previous* test's database: `get_settings()` returned that test's path
while the environment named the new one.

The writer thread did it. `reset_tool_stack` dropped the stack without draining
its audit queue, so a queued row ran afterwards, on a thread that opened the auth
store through `get_settings()` at that moment. A `Settings()` construction that
began under the old environment and finished after the next test's
`cache_clear()` is stored by `lru_cache` anyway -- the classic race -- and the
next stack was built on the stale path. Three `tool_audit-writer` threads were
alive at the failure, one per earlier test.

Both halves are pinned: a reset waits for the queue, and the writer uses the
database named when the log was created, whatever the settings say later.
"""

from __future__ import annotations

import threading
import time

import pytest

from app.core.config import get_settings
from app.mcp import runtime
from app.mcp.approvals import ApprovalStore
from app.mcp.audit import AuditLog, _AuditLogsWriter
from app.mcp.authorization import AuthorizationPolicy
from app.mcp.contracts import AuditRecord
from app.mcp.registry import ToolRegistry
from app.services.auth.auth_service import AuthDBService


def _record() -> AuditRecord:
    return AuditRecord(tool_id="querymind_demo_tool", actor_id="alice", status="succeeded")


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty))
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "first.db"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_resetting_the_stack_waits_for_its_queued_audit_rows(isolated_env, monkeypatch):
    written: list[str] = []

    def slow_write(record: AuditRecord) -> None:
        time.sleep(0.3)
        written.append(record.tool_id)

    registry = ToolRegistry(
        authorization=AuthorizationPolicy(),
        approvals=ApprovalStore(db_path=isolated_env / "approvals.db"),
        audit=AuditLog(write=slow_write),
    )
    stack = runtime.ToolStack(approvals=None, registry=registry, gateway=None, connectors=None)
    monkeypatch.setattr(runtime, "_stack", stack)

    registry._audit.append(_record())
    runtime.reset_tool_stack()

    assert written == ["querymind_demo_tool"], "reset returned while an audit row was still queued"
    assert runtime._stack is None


def test_the_audit_writer_uses_the_database_named_when_it_was_created(isolated_env, monkeypatch):
    first, second = isolated_env / "first.db", isolated_env / "second.db"
    writer = _AuditLogsWriter()

    # What the stale-cache race amounts to: by the time the writer thread first
    # writes, the settings name a different database.
    monkeypatch.setenv("APP_DB_PATH", str(second))
    get_settings.cache_clear()
    done = threading.Event()
    threading.Thread(target=lambda: (writer(_record()), done.set()), daemon=True).start()
    assert done.wait(10)

    assert [row["resource_id"] for row in AuthDBService(db_path=first).list_audit_logs(limit=10)] == [
        "querymind_demo_tool"
    ]
    assert not second.exists() or AuthDBService(db_path=second).list_audit_logs(limit=10) == []
