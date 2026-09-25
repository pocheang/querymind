"""One-time approval token lifecycle for high-risk MCP calls, persisted in SQLite.

This was an in-process dict until ARC-01 phase 2c, which cost two things
(SEC-10). A token minted by one worker could not be redeemed on another -- the
confirmation endpoint and the pipeline replaying the call land wherever the
load balancer sends them -- and a restart silently invalidated every pending
approval. The table lives in the application database, which every worker on a
host already shares.

Every state change is one conditional UPDATE, so "single-use" holds across
processes: two workers consuming the same token race inside SQLite, and exactly
one of them sees a changed row. The dict version read, checked and wrote back
as three steps, which was not atomic even within one process.

All methods are synchronous SQLite calls. Callers on the event loop reach them
through `asyncio.to_thread`.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from app.mcp.contracts import ApprovalRequest, ToolArgument, ToolCall
from app.orchestration.request import RequestActor
from app.services.runtime.sqlite_schema import Migration, ensure_schema

# Rows are pruned this long after they expire: long enough to answer "why was my
# token refused" from the table, short enough that it stays small.
_RETENTION_SECONDS = 3600


class ApprovalStore:
    """Approval tokens bound to one actor and one exact call, shared through `app.db`."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            from app.core.config import get_settings

            db_path = get_settings().app_db_path
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_schema(self.db_path, "tool_approvals", APPROVAL_MIGRATIONS, wal=True)

    def _connect(self) -> sqlite3.Connection:
        # A generous busy timeout: a write here is one small row, and waiting
        # behind another worker's write is always better than refusing a user's
        # confirmation with "database is locked".
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _baseline_schema(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_approvals (
              token TEXT PRIMARY KEY,
              tool_id TEXT NOT NULL,
              actor_id TEXT NOT NULL,
              arguments TEXT NOT NULL,
              call_fingerprint TEXT NOT NULL,
              expires_at REAL NOT NULL,
              approved INTEGER NOT NULL DEFAULT 0,
              approved_by TEXT,
              consumed INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_approvals_expires ON tool_approvals(expires_at)")

    def create(self, call: ToolCall, actor: RequestActor) -> ApprovalRequest:
        """Create an approval token bound to one actor and one exact call."""
        request = ApprovalRequest(
            tool_id=call.tool_id,
            actor_id=_actor_id(actor),
            arguments=call.arguments,
            call_fingerprint=_call_fingerprint(call),
        )
        now = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tool_approvals
                  (token, tool_id, actor_id, arguments, call_fingerprint, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.token,
                    request.tool_id,
                    request.actor_id,
                    json.dumps([[argument.name, argument.value] for argument in request.arguments]),
                    request.call_fingerprint,
                    request.expires_at.timestamp(),
                ),
            )
            conn.execute("DELETE FROM tool_approvals WHERE expires_at < ?", (now - _RETENTION_SECONDS,))
        return request

    def approved_call(self, token: str, actor: RequestActor) -> ToolCall | None:
        """Rebuild the approved call so a later run can replay it exactly.

        Resuming replays the approved call instead of re-running tool selection:
        a model re-reading the same question may choose differently, and the
        approval has to authorize the action the user was actually shown.
        """

        try:
            actor_id = _actor_id(actor)
        except ValueError:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tool_approvals
                WHERE token = ? AND actor_id = ? AND approved = 1 AND consumed = 0 AND expires_at > ?
                """,
                (token, actor_id, _now()),
            ).fetchone()
        if row is None:
            return None
        return ToolCall(tool_id=row["tool_id"], arguments=_arguments(row), approval_token=token)

    def approve(self, token: str, actor: RequestActor) -> None:
        """Approve a valid, unexpired token for its original actor only."""
        actor_id = _actor_id(actor)
        with self._connect() as conn:
            changed = conn.execute(
                """
                UPDATE tool_approvals SET approved = 1, approved_by = ?
                WHERE token = ? AND actor_id = ? AND consumed = 0 AND expires_at > ?
                """,
                (actor_id, token, actor_id, _now()),
            ).rowcount
            if changed == 1:
                return
            exists = conn.execute(
                "SELECT 1 FROM tool_approvals WHERE token = ? AND actor_id = ?", (token, actor_id)
            ).fetchone()
        if exists is None:
            raise ValueError("approval token is not available to this actor")
        raise ValueError("approval token is no longer valid")

    def consume(self, call: ToolCall, actor: RequestActor) -> ApprovalRequest | None:
        """Atomically consume and return an approved token for one matching call.

        One UPDATE decides it: of any number of workers consuming the same token
        at once, exactly one changes the row.
        """
        if not call.approval_token:
            return None
        try:
            actor_id = _actor_id(actor)
        except ValueError:
            return None
        with self._connect() as conn:
            changed = conn.execute(
                """
                UPDATE tool_approvals SET consumed = 1
                WHERE token = ? AND actor_id = ? AND tool_id = ? AND call_fingerprint = ?
                  AND approved = 1 AND consumed = 0 AND expires_at > ?
                """,
                (call.approval_token, actor_id, call.tool_id, _call_fingerprint(call), _now()),
            ).rowcount
            if changed != 1:
                return None
            row = conn.execute("SELECT * FROM tool_approvals WHERE token = ?", (call.approval_token,)).fetchone()
        return _request(row)


def _now() -> float:
    return datetime.now(UTC).timestamp()


def _arguments(row: sqlite3.Row) -> tuple[ToolArgument, ...]:
    return tuple(ToolArgument(name=name, value=value) for name, value in json.loads(row["arguments"]))


def _request(row: sqlite3.Row) -> ApprovalRequest:
    return ApprovalRequest(
        token=row["token"],
        tool_id=row["tool_id"],
        actor_id=row["actor_id"],
        arguments=_arguments(row),
        call_fingerprint=row["call_fingerprint"],
        expires_at=datetime.fromtimestamp(row["expires_at"], UTC),
        approved=bool(row["approved"]),
        approved_by=row["approved_by"],
        consumed=bool(row["consumed"]),
    )


def _call_fingerprint(call: ToolCall) -> str:
    """Identify the *call* -- tool and arguments -- and nothing about the run.

    ``execution_id`` used to be part of this, which made a token structurally
    unredeemable: every chat turn is a new execution, so the fingerprint of the
    call being retried could never equal the fingerprint of the call that was
    approved. Approval already binds to one actor, is single-use, and expires;
    tying it to a run as well only prevented the retry it exists to enable.
    """

    digest = sha256()
    values = ((call.tool_id, ""), *((argument.name, argument.value) for argument in call.arguments))
    for pair in values:
        for value in pair:
            encoded = value.encode("utf-8")
            digest.update(len(encoded).to_bytes(4, "big"))
            digest.update(encoded)
    return digest.hexdigest()


def _actor_id(actor: RequestActor) -> str:
    if not actor.user_id:
        raise ValueError("approval requires an authenticated actor")
    return actor.user_id


APPROVAL_MIGRATIONS = (Migration(1, "baseline: tool_approvals", ApprovalStore._baseline_schema),)
