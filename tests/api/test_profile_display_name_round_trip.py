"""A display name that is saved must come back.

`PUT /auth/profile` stored one correctly -- verified straight out of SQLite --
and returned it in its own response, because that response is built from a
`SELECT` in the same transaction. But `GET /auth/me` reported `None`, for
everyone, always: `SessionManager.get_user_by_token` joins `auth_sessions` to
`users` and selects `role`, `status` and `credit_balance` from `users` while
**not selecting `display_name`**, so the dict handed to `AuthUser(**user)` had
no such key and the model's default filled in.

The profile page therefore said "个人资料已保存" and showed the old value on the
next load. A write nobody reads, which is the shape this repository keeps
finding -- here with the write half working perfectly, which is what made it
survive: the endpoint's own response looked right.

Found by typing a display name into the profile page and reloading.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """An `AuthDBService` over a database of this test's own.

    Not pytest's temporary-path fixture: its basetemp root needs permissions
    that are not available on every Windows checkout.
    """

    from app.core.config import get_settings
    from app.services.auth.auth_service import AuthDBService

    root = Path(tempfile.mkdtemp(prefix="querymind-profile-"))
    monkeypatch.setenv("APP_DB_PATH", str(root / "app.db"))
    get_settings.cache_clear()
    try:
        yield AuthDBService()
    finally:
        get_settings.cache_clear()
        shutil.rmtree(root, ignore_errors=True)


def _session_user(service, username: str, password: str) -> dict:
    session = service.login(username, password)
    token = session["token"] if isinstance(session, dict) else session
    return service.get_user_by_token(token)


def test_a_saved_display_name_is_returned_by_the_session_lookup(service):
    """The end that was broken. `get_user_by_token` feeds `/auth/me`."""

    created = service.register("someone", "Sup3r-Str0ng-Pass!")
    user_id = created["user_id"] if isinstance(created, dict) else created

    service.update_user_display_name(user_id, "值班组 someone")

    user = _session_user(service, "someone", "Sup3r-Str0ng-Pass!")

    assert "display_name" in user, "the session lookup does not carry it at all"
    assert user["display_name"] == "值班组 someone"


def test_the_response_model_then_reports_it(service):
    """`/auth/me` is `AuthUser(**user)`, so a missing key silently defaults."""

    from app.api.schemas import AuthUser

    created = service.register("someone", "Sup3r-Str0ng-Pass!")
    user_id = created["user_id"] if isinstance(created, dict) else created
    service.update_user_display_name(user_id, "值班组 someone")

    rendered = AuthUser(**_session_user(service, "someone", "Sup3r-Str0ng-Pass!"))

    assert rendered.display_name == "值班组 someone"


def test_an_unset_display_name_is_none_not_a_crash(service):
    """The common case: most accounts never set one."""

    service.register("someone", "Sup3r-Str0ng-Pass!")

    user = _session_user(service, "someone", "Sup3r-Str0ng-Pass!")

    assert user["display_name"] is None


def test_the_write_half_was_never_the_problem(service):
    """Pinned so a future fix cannot "solve" this by changing the writer.

    `update_user_display_name` already persisted correctly and already returned
    the stored row; only the read path was blind. That distinction is why the
    defect survived -- the endpoint's own response looked right, because it is
    built from a `SELECT` inside the writing transaction.
    """

    from app.services.auth.auth_service import AuthDBService

    created = service.register("someone", "Sup3r-Str0ng-Pass!")
    user_id = created["user_id"] if isinstance(created, dict) else created

    written = service.update_user_display_name(user_id, "值班组 someone")

    assert written is not None
    assert written["display_name"] == "值班组 someone"

    # Durable, not merely echoed inside that transaction: a SECOND service, with
    # its own connection, reads it back. `get_user_profile` deliberately does not
    # carry the field -- its two callers want existence, role and the approval
    # token -- and adding a column nothing reads is what this repository removes.
    fresh = AuthDBService()
    session = fresh.login("someone", "Sup3r-Str0ng-Pass!")
    token = session["token"] if isinstance(session, dict) else session

    assert fresh.get_user_by_token(token)["display_name"] == "值班组 someone"
