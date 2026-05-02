"""List all user accounts."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.auth_db import AuthDBService


def main():
    db = AuthDBService()
    users = db.list_users()

    print("=" * 80)
    print("User List")
    print("=" * 80)

    if not users:
        print("No users found")
        return 0

    for user in users:
        print(f"\nUsername: {user.get('username')}")
        print(f"  Role: {user.get('role')}")
        print(f"  Status: {user.get('status')}")
        print(f"  User ID: {user.get('user_id')}")
        if user.get('business_unit'):
            print(f"  Business Unit: {user.get('business_unit')}")
        if user.get('department'):
            print(f"  Department: {user.get('department')}")
        if user.get('is_online'):
            print(f"  Online: {'Yes' if user.get('is_online') else 'No'}")
        print(f"  Created: {user.get('created_at')}")

    print("\n" + "=" * 80)
    print(f"Total: {len(users)} users")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
