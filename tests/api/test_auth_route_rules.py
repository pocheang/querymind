"""What `/auth` does around the auth service, which is where the rules live.

`AuthDBService` is covered elsewhere. The route module was at 26%, and what was
missing is not the happy path -- it is every rule the route adds on top of a
`login()` call: which key the failure counter is scoped to, what the client is
told when it is wrong, which of the token's two exits is on by default, and what
happens to a session whose password just changed.

Driven through a bare app carrying only this router, with fakes for the auth
service and the two limiters. Not the real application: these assertions are
about the route, and mounting the whole thing would put the middleware rate
limiter (already pinned in `tests/security/test_rate_limits_apply.py`) and the
developer's own SQLite in front of them.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.routes.public.auth as auth_routes
import app.api.utils.auth_helpers as auth_helpers

GOOD = "right-password"


class RecordingLimiter:
    """A limiter that records the keys it is asked about.

    The keys are the point of most of this file: what a limit is scoped to
    decides who a failed login costs.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.limited: set[str] = set()
        self.info = {"retry_after": 125, "attempts_used": 5, "max_attempts": 5, "window_seconds": 900}

    def _note(self, verb: str, key: str) -> None:
        self.calls.append((verb, key))

    def keys(self, verb: str) -> list[str]:
        return [key for seen, key in self.calls if seen == verb]

    def is_limited(self, key: str) -> bool:
        self._note("is_limited", key)
        return key in self.limited

    def get_limit_info(self, key: str) -> dict[str, int]:
        return dict(self.info)

    def record(self, key: str) -> None:
        self._note("record", key)

    def reset(self, key: str) -> None:
        self._note("reset", key)

    def try_acquire(self, key: str) -> bool:
        self._note("try_acquire", key)
        return key not in self.limited


class FakeAuthService:
    def __init__(self) -> None:
        self.audit_rows: list[dict[str, Any]] = []
        self.rotation_succeeds = True

    @staticmethod
    def _user(username: str) -> dict[str, Any]:
        return {
            "user_id": "u-1",
            "username": username,
            "role": "user",
            "status": "active",
            "credit_balance": 10,
        }

    def login(self, username: str, password: str) -> dict[str, Any]:
        if password != GOOD:
            # Deliberately disclosive, so the test can watch the route drop it.
            raise ValueError(f"no account named {username!r}")
        return {
            "token": "session-token-aaa",
            "token_type": "bearer",
            "expires_at": "2099-01-01T00:00:00Z",
            "user": self._user(username),
        }

    def register(self, username: str, password: str) -> dict[str, Any]:
        return self._user(username)

    def change_password(self, **kwargs: Any) -> dict[str, Any] | None:
        return {"token": "session-token-bbb"} if self.rotation_succeeds else None

    def add_audit_log(self, **fields: Any) -> None:
        self.audit_rows.append(fields)


@pytest.fixture
def service() -> FakeAuthService:
    return FakeAuthService()


@pytest.fixture
def login_limiter() -> RecordingLimiter:
    return RecordingLimiter()


@pytest.fixture
def register_limiter() -> RecordingLimiter:
    return RecordingLimiter()


@pytest.fixture
def client(
    monkeypatch: pytest.MonkeyPatch,
    service: FakeAuthService,
    login_limiter: RecordingLimiter,
    register_limiter: RecordingLimiter,
) -> Iterator[TestClient]:
    monkeypatch.setattr(auth_routes, "auth_service", service)
    monkeypatch.setattr(auth_routes, "login_limiter", login_limiter)
    monkeypatch.setattr(auth_routes, "register_limiter", register_limiter)
    # `_audit` reads its service as a module global of the helpers module, so
    # patching the route's name alone leaves the audit rows going to the real
    # database.
    monkeypatch.setattr(auth_helpers, "auth_service", service)

    app = FastAPI()
    app.include_router(auth_routes.router)
    app.dependency_overrides[auth_routes._require_user_and_token] = lambda: (
        FakeAuthService._user("alice"),
        "session-token-aaa",
    )
    with TestClient(app) as client:
        yield client


def _login(client: TestClient, username: str = "Alice", password: str = GOOD):
    # `_client_ip` reads `request.client.host`, which TestClient reports as
    # "testclient" -- hence that literal in every expected key below.
    return client.post("/auth/login", json={"username": username, "password": password})


class TestTheFailureCounterIsScopedToBothTheAddressAndTheAccount:
    """`login::{ip}::{username}`, and neither half is optional.

    Dropping the username makes one person's typos lock out everyone behind the
    same NAT; dropping the address lets anyone lock any account out from
    anywhere. The key is the whole control, so it is asserted directly rather
    than through the count.
    """

    def test_a_failure_is_recorded_against_the_address_and_the_account(
        self, client: TestClient, login_limiter: RecordingLimiter
    ) -> None:
        _login(client, "Alice", "wrong")

        assert login_limiter.keys("record") == ["login::testclient::alice"]

    def test_two_accounts_from_one_address_do_not_share_a_counter(
        self, client: TestClient, login_limiter: RecordingLimiter
    ) -> None:
        _login(client, "Alice", "wrong")
        _login(client, "Bob", "wrong")

        assert login_limiter.keys("record") == ["login::testclient::alice", "login::testclient::bob"]

    def test_the_username_is_case_folded_into_the_key(
        self, client: TestClient, login_limiter: RecordingLimiter
    ) -> None:
        """Otherwise `alice`, `Alice` and `ALICE` are three budgets against one
        account, and the limit is worth as many attempts as the name has
        spellings."""

        _login(client, "Alice", "wrong")
        _login(client, "ALICE", "wrong")
        _login(client, "  alice  ", "wrong")

        assert set(login_limiter.keys("record")) == {"login::testclient::alice"}

    def test_a_blank_username_still_gets_a_key(self, client: TestClient, login_limiter: RecordingLimiter) -> None:
        """`SlidingWindowLimiter.is_limited` returns False for an empty key, so
        a key that collapsed to nothing would be an unlimited login attempt."""

        _login(client, "   ", "wrong")

        assert login_limiter.keys("record") == ["login::testclient::unknown"]

    def test_a_success_clears_the_failures(self, client: TestClient, login_limiter: RecordingLimiter) -> None:
        """Without the reset, four typos followed by a correct password leave
        the account one mistake from a lockout it has already recovered from."""

        _login(client, "Alice", "wrong")
        _login(client, "Alice", GOOD)

        assert login_limiter.keys("reset") == ["login::testclient::alice"]

    def test_a_success_records_nothing(self, client: TestClient, login_limiter: RecordingLimiter) -> None:
        assert _login(client, "Alice", GOOD).status_code == 200
        assert login_limiter.keys("record") == []


class TestWhatAFailedLoginDiscloses:
    def test_the_client_is_told_only_that_the_credentials_are_invalid(self, client: TestClient) -> None:
        """The service says which half was wrong. Passing that through is user
        enumeration: "no such account" and "wrong password" are different
        answers, and one of them confirms the account exists."""

        response = _login(client, "Alice", "wrong")

        assert response.status_code == 401
        assert response.json()["detail"] == "invalid credentials"
        assert "Alice" not in response.text

    def test_the_audit_row_keeps_what_the_response_drops(self, client: TestClient, service: FakeAuthService) -> None:
        """The same split `handle_service_exception` makes next door: the
        operator gets the cause, the caller gets a flat refusal."""

        _login(client, "Alice", "wrong")

        failed = [row for row in service.audit_rows if row["result"] == "failed"]
        assert len(failed) == 1
        assert "no account named" in failed[0]["detail"]

    def test_a_rate_limited_login_is_audited_as_blocked_not_failed(
        self, client: TestClient, service: FakeAuthService, login_limiter: RecordingLimiter
    ) -> None:
        """Two different events. Counting a lockout as a credential failure
        inflates exactly the signal a reader of this log is looking for."""

        login_limiter.limited.add("login::testclient::alice")

        response = _login(client, "Alice", GOOD)

        assert response.status_code == 429
        assert [row["result"] for row in service.audit_rows] == ["blocked"]

    def test_the_refusal_says_when_to_come_back(self, client: TestClient, login_limiter: RecordingLimiter) -> None:
        """A 429 with no retry hint gives a client nothing but a retry loop."""

        login_limiter.limited.add("login::testclient::alice")

        response = _login(client, "Alice", GOOD)
        detail = response.json()["detail"]

        assert response.headers["Retry-After"] == "125"
        assert detail["retry_after_seconds"] == 125
        assert detail["error"] == "rate_limited"
        assert "2分5秒" in detail["message"], "the human-readable form is minutes and seconds, not raw seconds"


class TestWhereTheTokenGoes:
    """The cookie always; the body only when the deployment asks for it.

    `AUTH_EXPOSE_TOKEN_IN_RESPONSE` defaults false and has been quietly flipped
    once already, so what is asserted here is the effect on the wire rather than
    the value of the setting.
    """

    def test_the_body_carries_no_token_by_default(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(auth_routes.settings, "auth_expose_token_in_response", False)

        assert _login(client).json()["token"] == ""

    def test_the_cookie_carries_it_anyway(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """The blanking happens after `_set_auth_cookie`. Reversing those two
        lines sets an empty cookie and nobody can sign in at all."""

        monkeypatch.setattr(auth_routes.settings, "auth_expose_token_in_response", False)

        response = _login(client)

        assert response.cookies["auth_token"] == "session-token-aaa"

    def test_the_body_carries_it_when_the_deployment_asks(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(auth_routes.settings, "auth_expose_token_in_response", True)

        assert _login(client).json()["token"] == "session-token-aaa"

    def test_the_cookie_is_httponly_and_same_site(self, client: TestClient) -> None:
        """`AUTH_COOKIE_SECURE=true` and `AUTH_COOKIE_SAMESITE=strict` are code
        defaults that were relaxed once and put back. Read off the header, so
        this fails if a relaxation reaches the default layer again rather than
        the development env file where it belongs."""

        header = _login(client).headers["set-cookie"].lower()

        assert "httponly" in header
        assert "samesite=strict" in header
        assert "secure" in header


class TestRegistration:
    def test_the_limit_is_per_address_only(self, client: TestClient, register_limiter: RecordingLimiter) -> None:
        """Deliberately unlike login, and correct: there is no account yet to
        scope to, so scoping to the requested username would let one address
        register unlimited accounts by varying the name."""

        client.post("/auth/register", json={"username": "alice", "password": "x"})
        client.post("/auth/register", json={"username": "bob", "password": "x"})

        assert register_limiter.keys("try_acquire") == ["register::testclient", "register::testclient"]

    def test_a_limited_address_is_refused_and_audited(
        self, client: TestClient, service: FakeAuthService, register_limiter: RecordingLimiter
    ) -> None:
        register_limiter.limited.add("register::testclient")

        response = client.post("/auth/register", json={"username": "alice", "password": "x"})

        assert response.status_code == 429
        assert [row["result"] for row in service.audit_rows] == ["blocked"]


class TestChangingAPassword:
    def test_a_rotated_session_replaces_the_cookie(self, client: TestClient, service: FakeAuthService) -> None:
        service.rotation_succeeds = True

        response = client.post("/auth/change-password", json={"old_password": "a", "new_password": "b"})

        assert response.json() == {"ok": True, "message": "密码已成功更改", "token_rotated": True}
        assert response.cookies["auth_token"] == "session-token-bbb"

    def test_a_failed_rotation_clears_the_cookie_instead(self, client: TestClient, service: FakeAuthService) -> None:
        """The password changed and the old token did not. Leaving the cookie in
        place keeps a live session authenticated by a credential its owner has
        just replaced -- which is the state a password change exists to end.
        """

        service.rotation_succeeds = False

        response = client.post("/auth/change-password", json={"old_password": "a", "new_password": "b"})
        body = response.json()

        assert body["ok"] is True, "the password really did change; this is not a failure to report as one"
        assert body["token_rotated"] is False
        assert body["requires_relogin"] is True
        assert response.headers["set-cookie"].startswith('auth_token=""'), "the cookie is deleted, not left alone"

    def test_the_two_outcomes_are_audited_apart(self, client: TestClient, service: FakeAuthService) -> None:
        """Both are successes, and only one leaves the user signed in. One
        result string for both would hide every forced re-authentication."""

        service.rotation_succeeds = True
        client.post("/auth/change-password", json={"old_password": "a", "new_password": "b"})
        service.rotation_succeeds = False
        client.post("/auth/change-password", json={"old_password": "a", "new_password": "b"})

        assert [row["result"] for row in service.audit_rows] == ["success", "success_needs_reauth"]


class TestGoogleSignInWhenTheDeploymentHasNotConfiguredIt:
    """Both routes answered 500, and the 501 beside them could not be reached.

    `oauth.google` resolves through authlib's `__getattr__`, which raises
    `AttributeError: No such client: google` for a name that was never
    registered -- and registration is conditional on `GOOGLE_CLIENT_ID` and
    `GOOGLE_CLIENT_SECRET`, which a default checkout does not set. So
    `if not oauth.google:` had no true branch: either the client exists and is
    truthy, or reading it raises past the refusal it guards.

    The difference is the one this repository already draws between 500 and 503
    on the retrieval path. 500 sends an operator to look at this service; 501
    tells them Google sign-in was never configured here, which is the true and
    actionable answer.
    """

    @staticmethod
    def _bare_client() -> TestClient:
        """No fakes: this is about the module as a fresh checkout imports it.

        `raise_server_exceptions=False` so an unhandled error arrives as the 500
        a real deployment would serve rather than as a test-side traceback --
        without it the assertion could not tell the two apart.
        """

        app = FastAPI()
        app.include_router(auth_routes.router)
        return TestClient(app, raise_server_exceptions=False)

    @pytest.mark.parametrize("path", ["/auth/google/login", "/auth/google/callback"])
    def test_the_route_says_not_implemented_rather_than_failing(self, path: str) -> None:
        assert self._bare_client().get(path).status_code == 501

    def test_no_google_client_is_registered_in_this_configuration(self) -> None:
        """The precondition the two assertions above rest on.

        If a checkout ever did register one they would be testing the configured
        path while still reading as though they covered the unconfigured one.
        """

        assert auth_routes._google_client() is None

    def test_reading_the_client_directly_is_what_used_to_raise(self) -> None:
        """Pinned because the fix is a `getattr` default, which looks like
        defensive noise until you know the attribute raises."""

        with pytest.raises(AttributeError):
            _ = auth_routes.oauth.google

    def test_an_install_without_authlib_is_the_same_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`oauth` is None when the import at the top of the module fails.

        Covered by substitution rather than by uninstalling authlib, which is in
        `requirements/ci.txt` and so present in every run.

        It also settled how `_google_client` should be written. A first version
        opened with an explicit `if oauth is None: return None`; deleting that
        arm reddened nothing, because `getattr(None, "google", None)` is already
        None. The branch was removed rather than left with this test standing in
        front of it -- a guard that cannot change an answer reads like one that
        can.
        """

        monkeypatch.setattr(auth_routes, "oauth", None)

        assert auth_routes._google_client() is None
        assert self._bare_client().get("/auth/google/login").status_code == 501
