from __future__ import annotations

import getpass
import os

from app.services.auth_db import AuthDBService


def get_env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip()
    if not normalized:
        return default
    return normalized


def require_password_value(name: str, prompt: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        value = getpass.getpass(prompt)

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} cannot be empty")
    return normalized


def find_user_by_username(db: AuthDBService, username: str) -> dict | None:
    wanted = username.strip().lower()
    for user in db.list_users():
        if str(user.get("username", "")).strip().lower() == wanted:
            return user
    return None


def should_verify_current_password() -> bool:
    current_password = os.getenv("ADMIN_CURRENT_PASSWORD")
    return bool(current_password and current_password.strip())
