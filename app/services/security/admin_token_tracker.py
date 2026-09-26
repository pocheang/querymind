"""Admin approval token tracking service.

Tracks approval token usage to implement single-use and expiration mechanisms.

The used-token records lived in one process's memory until ARC-01 phase 2e, so a
single-use token was single-use *per worker*: the second administrator created
with it only had to land on another one. They are rows in the application
database now, and spending a token is one atomic UPSERT (`claim`), because
"check whether it was used, then mark it used" was also a race between two
requests on the same worker.
"""

import hashlib
import hmac
import logging
import sqlite3
import time
from pathlib import Path

from app.services.observability.log_safety import key_ref
from app.services.runtime.sqlite_schema import Migration, ensure_schema

logger = logging.getLogger(__name__)


class AdminTokenTracker:
    """Admin approval token tracker, shared by every worker through app.db."""

    def __init__(self, expiry_hours: int = 24, db_path: Path | None = None):
        """
        Initialize token tracker.

        Args:
            expiry_hours: How long a used token stays spent. Past this the record
                expires and the same token validates again -- "single-use for
                expiry_hours", pinned by tests as a decision, not an accident.
            db_path: The database holding the records; the application database
                by default, which is what makes them shared.
        """
        self._expiry_hours = expiry_hours
        if db_path is None:
            from app.core.config import get_settings

            db_path = get_settings().app_db_path
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        ensure_schema(self.db_path, "admin_token_uses", ADMIN_TOKEN_MIGRATIONS, wal=True)
        logger.info(f"AdminTokenTracker initialized with {expiry_hours}h expiry")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _cutoff(self) -> float:
        """Records at or before this moment have expired."""
        return time.time() - self._expiry_hours * 3600

    def is_token_used(self, token_hash: str) -> bool:
        """
        Check if token has been used.

        Args:
            token_hash: SHA256 hash of the token

        Returns:
            True if token has been used and not expired
        """
        cutoff = self._cutoff()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT used_by, used_at FROM admin_token_uses WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            if row is None:
                return False
            if row["used_at"] > cutoff:
                logger.warning(
                    "Token reuse attempt detected: token=%s, originally used by %s",
                    key_ref(token_hash),
                    key_ref(row["used_by"]),
                )
                return True
            # Expired, clean up
            logger.info("Cleaning expired token: token=%s", key_ref(token_hash))
            conn.execute("DELETE FROM admin_token_uses WHERE token_hash = ? AND used_at <= ?", (token_hash, cutoff))
        return False

    def claim(self, token_hash: str, user_id: str) -> bool:
        """Spend the token for `user_id`, unless someone spent it within the expiry window.

        One statement decides it: the row is written when there is none or when
        the existing one has expired, and left alone otherwise. Of any number of
        workers claiming the same token at once, exactly one sees a change.
        """
        with self._connect() as conn:
            changed = conn.execute(
                """
                INSERT INTO admin_token_uses (token_hash, used_by, used_at) VALUES (?, ?, ?)
                ON CONFLICT(token_hash) DO UPDATE SET used_by = excluded.used_by, used_at = excluded.used_at
                WHERE admin_token_uses.used_at <= ?
                """,
                (token_hash, user_id, time.time(), self._cutoff()),
            ).rowcount
        if changed == 1:
            logger.info("admin_token_used token=%s user=%s", key_ref(token_hash), key_ref(user_id))
            return True
        return False

    def cleanup_expired(self) -> int:
        """
        Clean up expired token records.

        Returns:
            Number of tokens cleaned up
        """
        with self._connect() as conn:
            removed = conn.execute("DELETE FROM admin_token_uses WHERE used_at <= ?", (self._cutoff(),)).rowcount

        if removed:
            logger.info(f"Cleaned up {removed} expired tokens")

        return removed

    def get_usage_stats(self) -> dict:
        """
        Get token usage statistics.

        Returns:
            Statistics dictionary
        """
        with self._connect() as conn:
            (count,) = conn.execute("SELECT COUNT(*) FROM admin_token_uses").fetchone()
        return {"total_used_tokens": count, "expiry_hours": self._expiry_hours}


def validate_admin_approval_token(
    token: str, configured_hash: str, actor_user_id: str, tracker: AdminTokenTracker
) -> tuple[bool, str]:
    """
    Validate admin approval token (timing-attack resistant, single-use).

    Args:
        token: Token to validate
        configured_hash: Configured token hash
        actor_user_id: User ID performing the operation
        tracker: Token tracker instance

    Returns:
        (is_valid, mode) tuple
        - is_valid: Whether token is valid
        - mode: Validation mode ("hash", "missing", "empty", "already_used")
    """
    candidate = str(token or "").strip()
    # Normalized here rather than trusted from the caller. The one live call
    # site in `admin_security` already does `.strip().lower()`, so this changes
    # nothing today -- but the digest below is lowercase hex, and a second
    # caller passing `Settings.admin_create_approval_token_hash` straight
    # through would silently reject every token if the operator had written the
    # hash in upper case. A comparison that depends on its caller having
    # normalized first is one edit from failing closed for no stated reason.
    configured_hash = str(configured_hash or "").strip().lower()

    # Check configuration
    if not configured_hash:
        # Perform dummy comparison to maintain constant time
        dummy_digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest().lower()
        hmac.compare_digest(dummy_digest, "0" * 64)
        return False, "missing"

    if not candidate:
        # Perform dummy comparison to maintain constant time
        hmac.compare_digest("", configured_hash)
        return False, "empty"

    # Calculate token hash
    digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest().lower()

    # Check if token has been used
    if tracker.is_token_used(digest):
        # Still perform comparison to maintain constant time
        hmac.compare_digest(digest, configured_hash)
        return False, "already_used"

    # Validate token
    is_valid = hmac.compare_digest(digest, configured_hash)

    # Spend it atomically. The check above can race: two requests with the same
    # token both find it unused, and "then mark it" used to let both through.
    # Whoever loses the claim gets exactly what a later request would have got.
    if is_valid and not tracker.claim(digest, actor_user_id):
        return False, "already_used"

    return is_valid, "hash"


# Global token tracker instance
_global_tracker: AdminTokenTracker | None = None


def get_token_tracker() -> AdminTokenTracker:
    """
    Get global token tracker instance.

    Returns:
        AdminTokenTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = AdminTokenTracker(expiry_hours=24)
    return _global_tracker


def _admin_token_baseline(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admin_token_uses (
          token_hash TEXT PRIMARY KEY,
          used_by TEXT NOT NULL,
          used_at REAL NOT NULL
        )
        """
    )


ADMIN_TOKEN_MIGRATIONS = (Migration(1, "baseline: admin_token_uses", _admin_token_baseline),)
