"""Bring every stored secret to the current format, once, at startup (SEC-07).

After this has run, `decrypt_secret_text` accepts nothing but enc:v2 under the
current key. That is what closes the hole the old format had -- a value with
no prefix was handed back as though it had been decrypted, so whoever could
write the database could plant a "credential" -- and it can only be closed for
data written before the change if that data is converted first.

Idempotent: a value already in the current format is left alone, so running
it on every start costs one read of each table. A value that cannot be read
(the key changed, or it was tampered with) is left as it is and logged; it was
unusable before and stays unusable, and is never silently replaced.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings, get_settings
from app.services.auth.encryption import (
    connector_secret_context,
    encryption_key_from_seed,
    system_secret_context,
    upgrade_secret_text,
    user_secret_context,
)

logger = logging.getLogger(__name__)


@dataclass
class SecretMigrationReport:
    upgraded: int = 0
    unreadable: list[str] = field(default_factory=list)


def migrate_stored_secrets(settings: Settings | None = None) -> SecretMigrationReport:
    settings = settings or get_settings()
    report = SecretMigrationReport()
    seed = str(getattr(settings, "api_settings_encryption_key", "") or "").strip()
    db_path = Path(settings.app_db_path)
    if not seed or not db_path.exists():
        # Without a key nothing could have been stored encrypted, and nothing
        # can be encrypted now; the stores refuse to start without one anyway.
        return report
    key = encryption_key_from_seed(seed)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "connector_credentials" in tables:
                _upgrade_connector_credentials(conn, key, report)
            if "system_settings" in tables:
                _upgrade_system_settings(conn, key, report)
            if "users" in tables:
                _upgrade_user_settings(conn, key, report)
    return report


def _upgrade(value: str, key: bytes, context: str, label: str, report: SecretMigrationReport) -> str | None:
    try:
        upgraded = upgrade_secret_text(value, key, context=context)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        report.unreadable.append(label)
        logger.warning("Stored secret %s could not be read for upgrade: %s", label, type(exc).__name__)
        return None
    if upgraded is not None:
        report.upgraded += 1
    return upgraded


def _upgrade_connector_credentials(conn: sqlite3.Connection, key: bytes, report: SecretMigrationReport) -> None:
    rows = conn.execute("SELECT credential_id, connector_id, owner_id, encrypted_secret FROM connector_credentials")
    for row in rows.fetchall():
        context = connector_secret_context(str(row["owner_id"]), str(row["connector_id"]))
        label = f"connector_credentials:{row['credential_id']}"
        upgraded = _upgrade(str(row["encrypted_secret"] or ""), key, context, label, report)
        if upgraded is not None:
            conn.execute(
                "UPDATE connector_credentials SET encrypted_secret=? WHERE credential_id=?",
                (upgraded, row["credential_id"]),
            )


def _upgrade_system_settings(conn: sqlite3.Connection, key: bytes, report: SecretMigrationReport) -> None:
    setting = "global_model_settings"
    row = conn.execute("SELECT value FROM system_settings WHERE key=?", (setting,)).fetchone()
    payload = _json_object(row["value"] if row else None)
    if payload is None:
        return
    upgraded = _upgrade(
        str(payload.get("api_key", "") or ""), key, system_secret_context(setting), f"system_settings:{setting}", report
    )
    if upgraded is not None:
        payload["api_key"] = upgraded
        conn.execute("UPDATE system_settings SET value=? WHERE key=?", (json.dumps(payload), setting))


def _upgrade_user_settings(conn: sqlite3.Connection, key: bytes, report: SecretMigrationReport) -> None:
    """Retired per-user model settings; `purge_retired_user_model_settings` normally
    removes them first, so this finds nothing unless that step failed."""

    for row in conn.execute("SELECT user_id, settings FROM users WHERE settings IS NOT NULL").fetchall():
        settings_data = _json_object(row["settings"])
        api_settings = settings_data.get("api_settings") if settings_data else None
        if not isinstance(api_settings, dict):
            continue
        user_id = str(row["user_id"])
        upgraded = _upgrade(
            str(api_settings.get("api_key", "") or ""),
            key,
            user_secret_context(user_id),
            f"users:{user_id}:api_settings",
            report,
        )
        if upgraded is not None:
            api_settings["api_key"] = upgraded
            conn.execute("UPDATE users SET settings=? WHERE user_id=?", (json.dumps(settings_data), user_id))


def _json_object(raw: object) -> dict | None:
    try:
        value = json.loads(raw) if raw else None
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None
