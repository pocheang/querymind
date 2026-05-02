"""Verify and reset an admin password."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_db import AuthDBService
from scripts.admin_script_utils import (
    find_user_by_username,
    get_env_value,
    require_password_value,
    should_verify_current_password,
)


def main() -> int:
    db = AuthDBService()
    username = get_env_value("ADMIN_USERNAME", default="admin") or "admin"

    admin_user = find_user_by_username(db, username)
    if not admin_user:
        print(f"Admin user '{username}' not found.")
        return 1

    print("=" * 60)
    print("Current admin user info:")
    print(f"  Username: {admin_user['username']}")
    print(f"  User ID: {admin_user['user_id']}")
    print(f"  Role: {admin_user['role']}")
    print(f"  Status: {admin_user['status']}")
    print("=" * 60)

    if should_verify_current_password():
        current_password = get_env_value("ADMIN_CURRENT_PASSWORD")
        try:
            result = db.user_manager.authenticate(username, current_password)
        except Exception as exc:
            print(f"Current password verification failed: {exc}")
            return 1

        if not result:
            print("Current password verification failed.")
            return 1

        print("Current password verification succeeded.")

    try:
        new_password = require_password_value("ADMIN_NEW_PASSWORD", f"Enter new password for {username}: ")
        db.update_user_password(admin_user["user_id"], new_password)
        print("\nPassword reset successful!")
        print("=" * 60)
        print(f"Username: {username}")
        print("=" * 60)

        result = db.user_manager.authenticate(username, new_password)
        if result:
            print("\nVerification: Login successful with new password!")
        else:
            print("\nWARNING: Password was reset but login verification failed.")

        return 0
    except Exception as exc:
        print(f"Failed to reset password: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
