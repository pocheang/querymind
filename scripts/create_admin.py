"""Create an admin user account."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_db import AuthDBService
from scripts.admin_script_utils import find_user_by_username, get_env_value, require_password_value


def main() -> int:
    db = AuthDBService()
    username = get_env_value("ADMIN_USERNAME", default="admin") or "admin"
    role = get_env_value("ADMIN_ROLE", default="admin") or "admin"

    try:
        existing_user = find_user_by_username(db, username)
        if existing_user:
            print(f"Admin user '{username}' already exists.")
            print(f"Role: {existing_user.get('role')}")
            print(f"Status: {existing_user.get('status')}")
            return 0

        password = require_password_value("ADMIN_PASSWORD", f"Enter password for {username}: ")
        user = db.create_user_with_role(username=username, password=password, role=role)

        print("=" * 60)
        print("Admin account created successfully!")
        print("=" * 60)
        print(f"Username: {user['username']}")
        print(f"Role: {user['role']}")
        print(f"Status: {user.get('status', 'active')}")
        print("=" * 60)
        print("\nStore the password securely and rotate it after first login if needed.")
        return 0
    except Exception as exc:
        print(f"Failed to create admin account: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
