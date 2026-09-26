import logging
import secrets
import sqlite3
from contextlib import closing
from datetime import timedelta
from typing import Any

from app.services.auth.utils import iso, now, parse_iso

logger = logging.getLogger(__name__)

# `last_seen_at` has one reader, the admin view's "online in the last 10
# minutes", so recording it more than once a minute buys nothing.
TOUCH_INTERVAL_SECONDS = 60


class SessionManager:
    def __init__(self, conn_factory, token_ttl_hours: int):
        self.conn_factory = conn_factory
        self.token_ttl_hours = token_ttl_hours

    def create_session(
        self,
        user_id: str,
        username: str,
        role: str,
        status: str,
        credit_balance: int = 10,
    ) -> dict[str, Any]:
        token = secrets.token_urlsafe(40)
        issued_at = now()
        expires_at = issued_at + timedelta(hours=self.token_ttl_hours)
        with self.conn_factory() as conn:
            conn.execute(
                "INSERT INTO auth_sessions(token, user_id, username, issued_at, last_seen_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                (token, user_id, username, iso(issued_at), iso(issued_at), iso(expires_at)),
            )
        return {
            "token": token,
            "token_type": "bearer",
            "expires_at": iso(expires_at),
            "user": {
                "user_id": user_id,
                "username": username,
                "role": role,
                "status": status,
                "credit_balance": int(credit_balance),
            },
        }

    def delete_session(self, token: str) -> None:
        with self.conn_factory() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token=?", (token,))

    def get_user_by_token(self, token: str, include_disabled: bool = False) -> dict[str, Any] | None:
        with self.conn_factory() as conn:
            now_ts = now()
            row = conn.execute(
                """
                SELECT s.user_id AS user_id, s.username AS username, s.expires_at AS expires_at,
                       u.role AS role, u.status AS status, u.credit_balance AS credit_balance,
                       u.display_name AS display_name
                FROM auth_sessions s
                JOIN users u ON u.user_id = s.user_id
                WHERE s.token=?
                """,
                (token,),
            ).fetchone()
            if row is None:
                return None
            if parse_iso(str(row["expires_at"])) <= now_ts:
                conn.execute("DELETE FROM auth_sessions WHERE token=?", (token,))
                return None
            if str(row["status"]).lower() != "active" and not include_disabled:
                return None
            return {
                "user_id": str(row["user_id"]),
                "username": str(row["username"]),
                "role": str(row["role"]),
                "status": str(row["status"]),
                "credit_balance": int(row["credit_balance"]),
                # Read from `users`, like role and status, because it lives there
                # and the session row does not carry it. Omitting it meant
                # `PUT /auth/profile` stored a display name correctly -- verified
                # in the database -- while `GET /auth/me`, which populates the
                # profile page and the top bar, reported `None` for everyone
                # forever. A write nobody reads.
                "display_name": row["display_name"],
            }

    def touch_session(self, token: str) -> None:
        """Record that the session was used -- at most once a minute, and never at the cost of the request.

        This ran an UPDATE on every authenticated request, so every request
        needed `app.db`'s write lock. With several workers, and a busy writer
        on the same file, a request waited out the whole busy timeout and was
        answered 500 `database is locked` (ARC-01, found running two workers).
        A read decides whether a write is needed -- in WAL mode a read never
        waits for a writer -- and a write that still meets contention is
        skipped: `last_seen_at` is bookkeeping, and a value one minute stale
        only makes the session look older than it is.
        """

        current = now()
        with closing(self.conn_factory()) as conn:
            row = conn.execute("SELECT last_seen_at FROM auth_sessions WHERE token=?", (token,)).fetchone()
        if row is None or _seen_recently(row["last_seen_at"], current):
            return
        try:
            with closing(self.conn_factory()) as conn, conn:
                conn.execute("UPDATE auth_sessions SET last_seen_at=? WHERE token=?", (iso(current), token))
        except sqlite3.OperationalError as error:
            if not _is_contention(error):
                raise
            logger.warning("session_touch_skipped reason=%s", error)

    def rotate_session_token(
        self,
        old_token: str,
        user_id: str,
        username: str,
        role: str,
        status: str,
        credit_balance: int = 10,
    ) -> dict[str, Any]:
        """
        安全修复：轮换会话令牌（用于密码更改、角色提升等敏感操作）
        删除旧令牌，生成新令牌
        """
        # 删除旧会话
        self.delete_session(old_token)
        # 创建新会话
        return self.create_session(user_id, username, role, status, credit_balance)

    def count_active_sessions(self) -> int:
        now_ts = iso(now())
        with self.conn_factory() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM auth_sessions WHERE expires_at > ?", (now_ts,)).fetchone()
            return int(row["c"]) if row else 0


def _seen_recently(last_seen_at: Any, current) -> bool:
    if not last_seen_at:
        return False
    try:
        return (current - parse_iso(str(last_seen_at))).total_seconds() < TOUCH_INTERVAL_SECONDS
    except (TypeError, ValueError):
        return False


def _is_contention(error: sqlite3.OperationalError) -> bool:
    message = str(error).lower()
    return "locked" in message or "busy" in message
