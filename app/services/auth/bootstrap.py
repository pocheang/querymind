"""The administrator a fresh installation starts with.

Until 2026-09-08 a checkout had no account with the `admin` role, and the only
way to get one was to know that `scripts/create_admin.py` exists. So the admin
console -- ten tabs of it, plus every `/admin/*` endpoint -- could not be opened
on a first run by anybody who had not read the documentation. That is not a
feature that is switched off; it is a feature nobody can find.

Four decisions here, each of which is the point rather than an implementation
detail:

**There is no default password.** A shipped credential is a shipped
vulnerability the first time an installation reaches a network, and
`admin/admin` is the first pair anything scanning the internet tries. The
password comes from `ADMIN_PASSWORD` when the operator sets it, and is
otherwise generated here. It is stored only as a hash, and never written to a
file in this repository.

**It fires when there is no *active administrator*, not when there are no
users.** An installation where somebody registered an ordinary account first
would otherwise never get one and would be locked out of the console with no
way in short of editing the database by hand. Recreating one on restart when
every admin is gone is a recovery path and not a way past authentication:
whoever can restart the process can already read the database it would be
protecting.

**An existing account is never promoted.** If the chosen username is taken by a
non-admin, this refuses and says so. Quietly raising somebody's role because
their username collided is privilege escalation triggered by a name.

**An `ADMIN_PASSWORD` that fails the policy is an error, not a fallback.**
Generating a different password instead would leave the operator unable to sign
in with the one they set, and nothing would say why.

`ADMIN_USERNAME` and `ADMIN_PASSWORD` are read from the real process
environment rather than becoming `Settings` fields, for the reason
`NACOS_PASSWORD` is not one either: a credential that becomes a field is a
credential that can reach a configuration endpoint.
"""

from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass

from app.services.auth.auth_service import AuthDBService
from app.services.auth.validation import validate_password

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USERNAME = "admin"

# Ambiguous glyphs are left out: this password gets read off a terminal and
# typed into a browser, and `l`/`1`/`I` and `0`/`O` are where that goes wrong.
_LOWER = "abcdefghijkmnopqrstuvwxyz"
_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_DIGITS = "23456789"
_SPECIAL = "!@#$%^&*_+-=?"


class AdminBootstrapError(RuntimeError):
    """The installation has no administrator and one could not be created."""


@dataclass(frozen=True)
class AdminBootstrap:
    """What was created, and whether the caller has to show the password."""

    username: str
    #: Set only when this function generated it. An operator-supplied password
    #: is never echoed -- they already have it, and repeating it puts a secret
    #: somewhere it did not need to be.
    generated_password: str | None


def generate_password(length: int = 20) -> str:
    """A password that satisfies the policy by construction, not by retrying."""

    alphabet = _LOWER + _UPPER + _DIGITS + _SPECIAL
    required = [
        secrets.choice(_LOWER),
        secrets.choice(_UPPER),
        secrets.choice(_DIGITS),
        secrets.choice(_SPECIAL),
    ]
    chars = required + [secrets.choice(alphabet) for _ in range(max(length - len(required), 0))]
    # Shuffle so the guaranteed characters are not always in the same places.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def active_admin_exists(service: AuthDBService) -> bool:
    """Whether anybody can currently open the admin console.

    `status` is part of the question: a disabled administrator cannot sign in,
    so an installation holding only disabled ones has no way into the console
    and is exactly the case this exists for.
    """

    with service._connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE lower(role) = 'admin' AND lower(status) = 'active' LIMIT 1"
        ).fetchone()
    return row is not None


def ensure_admin_account(
    service: AuthDBService | None = None,
    *,
    username: str | None = None,
    password: str | None = None,
) -> AdminBootstrap | None:
    """Create the first administrator when this installation has none.

    Returns None when one already exists, which is every start after the first.
    Raises `AdminBootstrapError` when an administrator is needed and cannot be
    created, so the caller can report it rather than start up looking healthy
    with no way in.
    """

    service = service or AuthDBService()
    if active_admin_exists(service):
        return None

    name = (username or os.getenv("ADMIN_USERNAME") or DEFAULT_ADMIN_USERNAME).strip()
    if not name:
        raise AdminBootstrapError("ADMIN_USERNAME is empty")

    supplied = password if password is not None else os.getenv("ADMIN_PASSWORD", "")
    secret = supplied or generate_password()
    try:
        validate_password(secret)
    except ValueError as exc:
        raise AdminBootstrapError(f"the supplied administrator password does not meet the policy: {exc}") from exc

    with service._connect() as conn:
        taken = conn.execute("SELECT role FROM users WHERE lower(username) = ?", (name.lower(),)).fetchone()
    if taken is not None:
        raise AdminBootstrapError(
            f"'{name}' already exists with role '{taken[0]}' and will not be promoted. "
            "Set ADMIN_USERNAME to a free name, or grant the role deliberately."
        )

    service.create_user_with_role(username=name, password=secret, role="admin")
    logger.warning("admin_bootstrap_created username=%s", name)
    return AdminBootstrap(username=name, generated_password=None if supplied else secret)


def describe_bootstrap(result: AdminBootstrap) -> str:
    """The lines an operator has to see, for stderr rather than for a log.

    Deliberately not written through `logging`: `setup_log_capture()` buffers
    records for the admin console's log viewer, so a generated password sent
    there would be readable by every administrator added afterwards. stderr
    reaches the terminal (and `docker logs`) and nothing that persists it here.
    """

    lines = [
        "",
        "=" * 68,
        f"  A first administrator was created: {result.username}",
    ]
    if result.generated_password:
        lines += [
            f"  password: {result.generated_password}",
            "",
            "  Shown once and stored only as a hash. Save it now, then sign in",
            "  and change it. Set ADMIN_PASSWORD to choose your own instead.",
        ]
    else:
        lines.append("  password: the one you set in ADMIN_PASSWORD")
    lines += ["=" * 68, ""]
    return "\n".join(lines)


__all__ = [
    "AdminBootstrap",
    "AdminBootstrapError",
    "DEFAULT_ADMIN_USERNAME",
    "active_admin_exists",
    "describe_bootstrap",
    "ensure_admin_account",
    "generate_password",
]
