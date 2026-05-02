"""Reset admin user password."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_db import AuthDBService
from scripts.admin_script_utils import find_user_by_username, get_env_value, require_password_value


def main() -> int:
    db = AuthDBService()
    username = get_env_value("ADMIN_USERNAME", default="admin") or "admin"

    admin_user = find_user_by_username(db, username)
    if not admin_user:
        print(f"Admin user '{username}' not found.")
        return 1

    try:
        new_password = require_password_value("ADMIN_NEW_PASSWORD", f"Enter new password for {username}: ")
        db.update_user_password(admin_user["user_id"], new_password)

        print("=" * 60)
        print("Admin password reset successfully!")
        print("=" * 60)
        print(f"Username: {admin_user['username']}")
        print(f"Role: {admin_user['role']}")
        print("=" * 60)
        print("\nStore the new password securely.")
        return 0
    except Exception as exc:
        print(f"Failed to reset password: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
