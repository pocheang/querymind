"""Session tokens are stored as digests (SEC-05); login does not name users (SEC-06).

SEC-05: `auth_sessions.token` held the bearer token itself, so anything that
could read app.db -- a backup, a copied volume -- could sign in as every user
with a live session. It holds `sha256:<hex>` now, and the upgrade rewrites
existing rows in place so nobody is signed out.

SEC-06: an unknown username returned at once while a known one cost a 600k
PBKDF2 run, and a disabled account was reported before its password was
checked. Both told an unauthenticated caller which usernames exist. Here the
PBKDF2 runs are counted rather than timed: a clock is a bad thing to assert
on, and the count is what produced the difference.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from app.services.auth import user_manager as user_manager_module
from app.services.auth.auth_service import AuthDBService
from app.services.auth.session_manager import hash_stored_session_tokens, stored_token

PASSWORD = "Correct-Horse-Battery-9"


@pytest.fixture
def auth(tmp_path):
    service = AuthDBService(db_path=tmp_path / "auth.db", token_ttl_hours=1)
    service.register("alice", PASSWORD)
    return service, tmp_path / "auth.db"


def _stored_tokens(db_path) -> list[str]:
    with closing(sqlite3.connect(db_path)) as conn:
        return [row[0] for row in conn.execute("SELECT token FROM auth_sessions")]


# --- SEC-05 --------------------------------------------------------------------


def test_the_database_never_holds_the_bearer_token(auth):
    service, db = auth
    token = service.login("alice", PASSWORD)["token"]

    assert token not in _stored_tokens(db)
    assert _stored_tokens(db) == [stored_token(token)]


def test_the_token_still_signs_in_and_out(auth):
    service, db = auth
    token = service.login("alice", PASSWORD)["token"]

    assert service.get_user_by_token(token)["username"] == "alice"
    service.logout(token)
    assert service.get_user_by_token(token) is None
    assert _stored_tokens(db) == []


def test_the_digest_itself_is_not_a_credential(auth):
    """Reading the table must not be enough to sign in."""
    service, db = auth
    service.login("alice", PASSWORD)

    assert service.get_user_by_token(_stored_tokens(db)[0]) is None


def test_an_existing_plaintext_session_survives_the_upgrade(auth):
    service, db = auth
    token = service.login("alice", PASSWORD)["token"]
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE auth_sessions SET token=?", (token,))  # as the old code stored it

    with closing(sqlite3.connect(db)) as conn:
        assert hash_stored_session_tokens(lambda: conn) == 1
        assert hash_stored_session_tokens(lambda: conn) == 0  # idempotent

    assert _stored_tokens(db) == [stored_token(token)]
    assert service.get_user_by_token(token)["username"] == "alice"


# --- SEC-06 --------------------------------------------------------------------


@pytest.fixture
def pbkdf2_runs(monkeypatch) -> list[int]:
    runs: list[int] = []
    real = user_manager_module.verify_password

    def counting(*args, **kwargs):
        runs.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(user_manager_module, "verify_password", counting)
    return runs


@pytest.mark.parametrize(
    ("username", "password"),
    [("alice", "wrong-password-1A"), ("nobody", "wrong-password-1A"), ("nobody", PASSWORD)],
    ids=["known-wrong", "unknown", "unknown-with-a-real-password"],
)
def test_every_failed_login_costs_one_hash(auth, pbkdf2_runs, username, password):
    service, _ = auth

    with pytest.raises(ValueError, match="invalid credentials"):
        service.login(username, password)

    assert len(pbkdf2_runs) == 1


def test_a_disabled_account_is_not_named_to_someone_without_its_password(auth, pbkdf2_runs):
    service, _ = auth
    user_id = service.user_manager.authenticate("alice", PASSWORD)["user_id"]
    service.update_user_status(user_id, "disabled")
    pbkdf2_runs.clear()

    with pytest.raises(ValueError, match="invalid credentials"):
        service.login("alice", "wrong-password-1A")
    with pytest.raises(ValueError, match="user disabled"):
        service.login("alice", PASSWORD)

    assert len(pbkdf2_runs) == 2
