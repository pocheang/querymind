"""Governed tool decisions reach audit_logs, off the event loop (ARC-01 phase 2c, SEC-10).

The sink was a list in process memory, "until a durable service is configured",
and none ever was: every approval-gated write had no record anywhere an
administrator could see, and a restart erased the ones that existed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading

import pytest

from app.core.config import get_settings
from app.mcp import audit as audit_module
from app.mcp.approvals import ApprovalStore
from app.mcp.audit import AuditLog
from app.mcp.authorization import AuthorizationPolicy
from app.mcp.contracts import AuditRecord, ToolArgument, ToolCall, ToolDefinition, ToolParameter
from app.mcp.registry import ToolRegistry
from app.orchestration.request import RequestActor
from app.services.auth.auth_service import AuthDBService

ALICE = RequestActor(user_id="alice", tenant_id="acme", role="viewer", permissions=frozenset({"tool:use"}))


def _record(**overrides) -> AuditRecord:
    fields = {"tool_id": "querymind_demo_tool", "actor_id": "alice", "status": "succeeded"}
    fields.update(overrides)
    return AuditRecord(**fields)


@pytest.fixture
def app_db(monkeypatch, tmp_path):
    """Point the default writer at a scratch app.db, never the developer's."""

    empty = tmp_path / "empty.env"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("RUNTIME_ENV_FILE", str(empty))
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.db"))
    get_settings.cache_clear()
    yield tmp_path / "app.db"
    get_settings.cache_clear()


def _rows(db_path) -> list[dict]:
    return AuthDBService(db_path=db_path).list_audit_logs(limit=100)


def test_append_returns_before_anything_is_written():
    """The caller is `ToolRegistry._finish`, on the event loop; the write happens elsewhere."""

    release = threading.Event()
    written_on: list[int] = []

    def slow_write(record):
        written_on.append(threading.get_ident())
        release.wait(5)

    log = AuditLog(write=slow_write)
    log.append(_record())  # would hang for 5s if the write were inline
    release.set()

    assert log.flush()
    assert written_on and written_on[0] != threading.get_ident()


def test_a_record_reaches_audit_logs_with_names_but_never_argument_values(app_db):
    log = AuditLog()
    log.append(
        _record(
            status="succeeded",
            approved_by="alice",
            argument_names=("connector_id",),
            execution_id="run-7",
            duration_ms=12,
            summary="connector disabled",
        )
    )
    assert log.flush()

    (row,) = _rows(app_db)
    assert (row["action"], row["resource_type"], row["result"]) == ("tool.invoke", "tool", "succeeded")
    assert (row["actor_user_id"], row["resource_id"]) == ("alice", "querymind_demo_tool")
    detail = json.loads(row["detail"])
    assert detail["argument_names"] == ["connector_id"]
    assert detail["approved_by"] == "alice"
    assert detail["execution_id"] == "run-7"


def test_a_call_held_for_approval_is_its_own_action(app_db):
    log = AuditLog()
    log.append(_record(status="approval_required"))
    assert log.flush()

    assert [row["action"] for row in _rows(app_db)] == ["tool.approval_required"]


def test_an_anonymous_actor_is_recorded_as_none_rather_than_a_fake_user_id(app_db):
    log = AuditLog()
    log.append(_record(actor_id="anonymous", status="failed"))
    assert log.flush()

    assert _rows(app_db)[0]["actor_user_id"] is None


def test_the_approval_cycle_leaves_a_trail_an_administrator_can_read(app_db, tmp_path):
    """The path SEC-10 was about: a write that needed a human, and whether anyone can see it happened."""

    definition = ToolDefinition(
        tool_id="querymind_demo_write",
        operation="write",
        risk="idempotent",
        description="demo",
        parameters=(ToolParameter(name="target", required=True, max_length=32),),
    )
    log = AuditLog()
    registry = ToolRegistry(
        authorization=AuthorizationPolicy(), approvals=ApprovalStore(tmp_path / "approvals.db"), audit=log
    )

    async def executor(call, actor):
        from app.domain.contracts import ToolResult

        return ToolResult(tool_id=call.tool_id, status="succeeded", summary="done")

    registry.register(definition, executor)
    call = ToolCall(tool_id="querymind_demo_write", arguments=(ToolArgument(name="target", value="secret-value"),))

    pending = asyncio.run(registry.invoke(call, ALICE))
    assert pending.status == "approval_required"
    registry._approvals.approve(pending.approval_token, ALICE)
    done = asyncio.run(registry.invoke(call.model_copy(update={"approval_token": pending.approval_token}), ALICE))
    assert done.status == "succeeded"
    assert log.flush()

    rows = sorted(_rows(app_db), key=lambda row: row["created_at"])
    assert [(row["action"], row["result"]) for row in rows] == [
        ("tool.approval_required", "approval_required"),
        ("tool.invoke", "succeeded"),
    ]
    assert json.loads(rows[1]["detail"])["approved_by"] == "alice"
    assert not [row for row in rows if "secret-value" in (row["detail"] or "")]


def test_a_full_queue_drops_and_says_so_instead_of_blocking(monkeypatch, caplog):
    monkeypatch.setattr(audit_module, "_MAX_PENDING", 2)
    release = threading.Event()
    log = AuditLog(write=lambda record: release.wait(5))

    with caplog.at_level(logging.ERROR, logger="app.mcp.audit"):
        for _ in range(6):
            log.append(_record())
    release.set()

    assert log.dropped >= 3
    assert any("tool_audit_dropped" in message for message in caplog.messages)
    assert log.flush()


def test_a_failed_write_does_not_stop_the_writer(caplog):
    written: list[str] = []

    def flaky(record):
        if record.summary == "first":
            raise OSError("database is locked")
        written.append(record.summary)

    log = AuditLog(write=flaky)
    with caplog.at_level(logging.ERROR, logger="app.mcp.audit"):
        log.append(_record(summary="first"))
        log.append(_record(summary="second"))
        assert log.flush()

    assert written == ["second"]
    assert any("tool_audit_write_failed" in message for message in caplog.messages)
