#!/usr/bin/env python
"""Create the first administrator, or reset one's password.

    conda run -n rag-local python scripts/create_admin.py
    conda run -n rag-local python scripts/create_admin.py --reset-password

**The server does the creating half itself now**, on any start that finds no
active administrator (`app/services/auth/bootstrap.py`, reached from the
lifespan), so a first run no longer needs this script. It stays for the two
things a running server will not do for you: resetting a forgotten password, and
adding an administrator under a chosen name without a restart.

Both paths go through `ensure_admin_account`, so the script and the server
cannot disagree about what an administrator is.

The password comes from `ADMIN_PASSWORD` when it is set, and is otherwise
generated and printed **once**. It is never written to a file in the repository,
because a credential in version control is a credential in everyone's checkout —
and a fixture password has a way of reaching a server that is not a fixture.

Idempotent: an existing account is left alone unless `--reset-password` is given,
so re-running this after a database reset is safe and re-running it by accident
costs nothing.

Policy (`app/services/auth/validation.py`): at least 12 characters, with
lowercase, uppercase, a digit and one of `!@#$%^&*()_+-=[]{}|;:,.<>?`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Set a new password on an account that already exists.",
    )
    args = parser.parse_args(argv)

    from app.core.config import get_settings
    from app.services.auth.auth_service import AuthDBService
    from app.services.auth.bootstrap import (
        AdminBootstrapError,
        ensure_admin_account,
        generate_password,
    )
    from app.services.auth.password_utils import generate_salt, hash_password
    from app.services.auth.validation import validate_password

    settings = get_settings()
    service = AuthDBService()

    with service._connect() as conn:
        row = conn.execute(
            "SELECT user_id, role FROM users WHERE lower(username) = ?", (args.username.lower(),)
        ).fetchone()

    if row is not None and not args.reset_password:
        print(f"'{args.username}' already exists with role '{row[1]}'; nothing to do.")
        print("Pass --reset-password to set a new password.")
        return 0

    if row is None:
        # The same call the server makes on a first run, so the script and the
        # startup path cannot disagree about what an administrator is. It
        # returns None when one already exists, which is why the reset branch
        # below stays separate rather than being folded into it.
        try:
            created = ensure_admin_account(service, username=args.username)
        except AdminBootstrapError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if created is None:
            print("An administrator already exists; this script creates the first one.")
            print(f"Pass --username {args.username} --reset-password to set a password instead.")
            return 0
        # `settings.users_path` does not exist and never did -- `Settings` has
        # `app_db_path`. This line raised AttributeError *after* the account was
        # created, so the script reported a failure having succeeded, and the
        # generated password printed below was lost with it: an admin account
        # nobody could sign in to, and no way to find out. Found 2026-09-06 by
        # running it.
        print(f"created administrator '{created.username}' in {settings.app_db_path}")
        if created.generated_password:
            print(f"password: {created.generated_password}")
            print("\nThis is printed once and stored only as a hash. Save it now.")
        else:
            print("password: (taken from ADMIN_PASSWORD)")
        return 0

    supplied = os.getenv("ADMIN_PASSWORD", "")
    password = supplied or generate_password()
    try:
        validate_password(password)
    except ValueError as exc:
        print(f"ADMIN_PASSWORD does not meet the policy: {exc}", file=sys.stderr)
        return 1

    # `change_password` verifies the old password, which a reset does not have,
    # so the hash is rewritten with the same primitives the service uses to
    # create one. Keeping the user_id matters: it owns documents.
    salt = generate_salt()
    with service._connect() as conn:
        conn.execute(
            "UPDATE users SET salt = ?, password_hash = ? WHERE user_id = ?",
            (salt, hash_password(password, salt), row[0]),
        )
        conn.commit()

    print(f"password reset for administrator '{args.username}' in {settings.app_db_path}")
    if supplied:
        print("password: (taken from ADMIN_PASSWORD)")
    else:
        print(f"password: {password}")
        print("\nThis is printed once and stored only as a hash. Save it now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
