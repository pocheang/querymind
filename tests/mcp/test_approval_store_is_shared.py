"""Approval tokens are shared through app.db and stay single-use across workers (ARC-01 phase 2c, SEC-10).

The store was a dict in one process. A token raised while answering a question
on worker A had to be confirmed at `POST /api/v1/connectors/approvals/{token}`
and replayed by a later request -- and either could land on worker B, which had
never heard of it. A restart dropped every pending approval.

Two `ApprovalStore` instances over one database file are two workers here: that
is exactly what they are in production, since each worker builds its own store
and every worker on a host opens the same app.db.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime

import pytest

from app.mcp.approvals import ApprovalStore
from app.mcp.contracts import ToolArgument, ToolCall
from app.orchestration.request import RequestActor

ALICE = RequestActor(user_id="alice", tenant_id="acme", role="viewer")
BOB = RequestActor(user_id="bob", tenant_id="acme", role="viewer")
CALL = ToolCall(
    tool_id="querymind_connector_disable_owned",
    arguments=(ToolArgument(name="connector_id", value="payroll"),),
)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "app.db"


def _approved(store: ApprovalStore, actor: RequestActor = ALICE) -> str:
    token = store.create(CALL, actor).token
    store.approve(token, actor)
    return token


def _replay(token: str) -> ToolCall:
    return CALL.model_copy(update={"approval_token": token})


def test_a_token_raised_on_one_worker_is_approved_and_replayed_on_another(db):
    worker_a, worker_b = ApprovalStore(db), ApprovalStore(db)

    token = worker_a.create(CALL, ALICE).token
    worker_b.approve(token, ALICE)

    replay = worker_a.approved_call(token, ALICE)
    assert replay is not None and replay.arguments == CALL.arguments
    consumed = worker_b.consume(_replay(token), ALICE)
    assert consumed is not None and consumed.consumed and consumed.approved_by == "alice"


def test_a_pending_approval_survives_a_restart(db):
    token = ApprovalStore(db).create(CALL, ALICE).token

    restarted = ApprovalStore(db)
    restarted.approve(token, ALICE)
    assert restarted.consume(_replay(token), ALICE) is not None


def test_a_token_is_consumed_once_across_workers(db):
    token = _approved(ApprovalStore(db))

    assert ApprovalStore(db).consume(_replay(token), ALICE) is not None
    assert ApprovalStore(db).consume(_replay(token), ALICE) is None


def test_concurrent_consumers_race_and_exactly_one_wins(db):
    """One conditional UPDATE decides it; the dict read, checked and wrote back in three steps."""

    token = _approved(ApprovalStore(db))
    results: list[object] = []
    lock = threading.Lock()
    start = threading.Barrier(8)

    def consume():
        store = ApprovalStore(db)
        start.wait()
        outcome = store.consume(_replay(token), ALICE)
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=consume) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(outcome is not None for outcome in results) == 1


def test_a_token_is_bound_to_its_actor(db):
    store = ApprovalStore(db)
    token = store.create(CALL, ALICE).token

    with pytest.raises(ValueError, match="not available"):
        store.approve(token, BOB)
    store.approve(token, ALICE)
    assert store.approved_call(token, BOB) is None
    assert store.consume(_replay(token), BOB) is None
    assert store.consume(_replay(token), ALICE) is not None


def test_a_token_only_authorizes_the_exact_call_it_was_raised_for(db):
    store = ApprovalStore(db)
    token = _approved(store)
    other = ToolCall(
        tool_id=CALL.tool_id,
        arguments=(ToolArgument(name="connector_id", value="slack"),),
        approval_token=token,
    )

    assert store.consume(other, ALICE) is None
    assert store.consume(_replay(token), ALICE) is not None, "a mismatched attempt must not burn the token"


def test_an_unapproved_token_cannot_be_consumed_or_replayed(db):
    store = ApprovalStore(db)
    token = store.create(CALL, ALICE).token

    assert store.approved_call(token, ALICE) is None
    assert store.consume(_replay(token), ALICE) is None


def test_an_expired_token_is_refused_everywhere(db):
    store = ApprovalStore(db)
    token = _approved(store)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE tool_approvals SET expires_at = ? WHERE token = ?", (datetime.now(UTC).timestamp() - 1, token)
        )

    assert store.approved_call(token, ALICE) is None
    assert store.consume(_replay(token), ALICE) is None
    with pytest.raises(ValueError, match="no longer valid"):
        store.approve(token, ALICE)


def test_a_consumed_token_cannot_be_approved_again(db):
    store = ApprovalStore(db)
    token = _approved(store)
    store.consume(_replay(token), ALICE)

    with pytest.raises(ValueError, match="no longer valid"):
        store.approve(token, ALICE)


def test_an_anonymous_actor_can_neither_raise_nor_redeem(db):
    store = ApprovalStore(db)
    anonymous = RequestActor(user_id=None, tenant_id="acme", role="viewer")

    with pytest.raises(ValueError):
        store.create(CALL, anonymous)
    token = _approved(store)
    assert store.approved_call(token, anonymous) is None
    assert store.consume(_replay(token), anonymous) is None


def test_long_expired_rows_are_pruned(db):
    store = ApprovalStore(db)
    stale = store.create(CALL, ALICE).token
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE tool_approvals SET expires_at = 0 WHERE token = ?", (stale,))

    store.create(CALL, ALICE)

    with sqlite3.connect(db) as conn:
        remaining = [row[0] for row in conn.execute("SELECT token FROM tool_approvals")]
    assert stale not in remaining and len(remaining) == 1


def test_callers_on_the_event_loop_reach_the_store_through_a_thread():
    """Every store method is a SQLite call now; calling one inline blocks the loop."""

    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "app"
    sources = {
        "mcp/registry.py": ("self._approvals.consume", "self._approvals.create"),
        "agents/tool/service.py": ("approvals.approved_call",),
        "api/routes/public/connectors.py": ("approval_store.approve",),
    }
    for relative, calls in sources.items():
        text = (root / relative).read_text(encoding="utf-8")
        for call in calls:
            assert f"asyncio.to_thread({call}," in text, f"{relative}: {call} is not dispatched to a thread"
            assert f"{call}(" not in text, f"{relative}: {call} is still called inline"
