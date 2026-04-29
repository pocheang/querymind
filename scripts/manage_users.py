"""Local user management utility.

This script is intentionally interactive and should only be run from a trusted
admin shell. It does not create weak default accounts.
"""
from __future__ import annotations

import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_db import AuthDBService


def _find_user_by_username(db: AuthDBService, username: str) -> dict | None:
    wanted = username.strip().lower()
    for user in db.list_users():
        if str(user.get("username", "")).lower() == wanted:
            return user
    return None


def _prompt_password(label: str) -> str:
    password = getpass.getpass(label)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise ValueError("passwords do not match")
    return password


def main() -> int:
    db = AuthDBService()

    print("=" * 50)
    print("User Management Tool")
    print("=" * 50)

    users = db.list_users()
    print("\nExisting users:")
    if not users:
        print("  (none)")
    else:
        for user in users:
            print(
                "  - {username} (role: {role}, status: {status})".format(
                    username=user.get("username", "-"),
                    role=user.get("role", "-"),
                    status=user.get("status", "-"),
                )
            )

    print("\n" + "=" * 50)
    print("Choose an action:")
    print("1. Create user")
    print("2. Reset user password")
    print("3. Exit")
    print("=" * 50)

    choice = input("\nSelect (1-3): ").strip()

    try:
        if choice == "1":
            username = input("Username: ").strip()
            password = _prompt_password("Password: ")
            role = input("Role (admin/analyst/viewer, default viewer): ").strip() or "viewer"
            user = db.create_user_with_role(username=username, password=password, role=role)
            print(f"\nCreated user: {user['username']} (role: {user['role']})")
            return 0

        if choice == "2":
            username = input("Username: ").strip()
            user = _find_user_by_username(db, username)
            if not user:
                print(f"\nUser not found: {username}")
                return 1
            password = _prompt_password("New password: ")
            db.update_user_password(str(user["user_id"]), password)
            print(f"\nPassword reset: {username}")
            return 0

        if choice == "3":
            print("\nBye.")
            return 0

        print("\nInvalid selection.")
        return 1
    except Exception as exc:
        print(f"\nOperation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
