"""A first run must be able to open the console that manages it.

Until 2026-09-08 a checkout had no account with the `admin` role, so every
`/admin/*` endpoint and all ten tabs of the console were unreachable by anybody
who had not read the documentation and run `scripts/create_admin.py`.

Most of this file is negative: the ways a first-run bootstrap turns into a
vulnerability are better known than the ways it fails to work. A default
password ships a credential; promoting whoever happens to hold the username is
privilege escalation by name collision; and re-creating an administrator beside
an existing one is a second door into the same building.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.services.auth.bootstrap import (
    DEFAULT_ADMIN_USERNAME,
    AdminBootstrapError,
    active_admin_exists,
    describe_bootstrap,
    ensure_admin_account,
    generate_password,
)
from app.services.auth.validation import validate_password


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """An `AuthDBService` over a database of this test's own.

    Deliberately not pytest's temporary-path fixture: its basetemp root needs
    permissions that are not available on every Windows checkout, which this
    repository already hit twice.
    """

    from app.core.config import get_settings
    from app.services.auth.auth_service import AuthDBService

    root = Path(tempfile.mkdtemp(prefix="querymind-admin-"))
    monkeypatch.setenv("APP_DB_PATH", str(root / "app.db"))
    # The two the bootstrap reads from the real environment: a developer with
    # either one exported would otherwise get a different test run.
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()
    try:
        yield AuthDBService()
    finally:
        get_settings.cache_clear()
        shutil.rmtree(root, ignore_errors=True)


# --- it happens at all -------------------------------------------------------


def test_a_fresh_installation_has_no_administrator(service) -> None:
    """The premise. Without it the rest of the file is solving nothing."""

    assert active_admin_exists(service) is False


def test_the_first_start_creates_one(service) -> None:
    created = ensure_admin_account(service)

    assert created is not None
    assert created.username == DEFAULT_ADMIN_USERNAME
    assert active_admin_exists(service) is True


def test_the_new_administrator_can_actually_sign_in(service) -> None:
    """Creating a row is not the same as creating an account somebody can use.

    The password is hashed by the service, and a bootstrap that produced an
    unusable hash would look identical from the database.
    """

    created = ensure_admin_account(service)
    assert created is not None and created.generated_password

    # `login` rather than the user manager underneath it, because signing in
    # is the thing that has to work -- the browser takes this exact path.
    session = service.login(created.username, created.generated_password)

    assert session["user"]["role"] == "admin"
    assert session["user"]["status"] == "active"
    assert session["token"]


def test_a_later_start_creates_nothing(service) -> None:
    """Every start after the first. A second administrator is a second door."""

    assert ensure_admin_account(service) is not None
    assert ensure_admin_account(service) is None

    with service._connect() as conn:
        (admins,) = conn.execute("SELECT count(*) FROM users WHERE lower(role) = 'admin'").fetchone()
    assert admins == 1


def test_an_installation_whose_only_admin_is_disabled_gets_one(service) -> None:
    """ "No users" is the wrong question, and so is "no admin row".

    A disabled administrator cannot sign in, so an installation holding only
    disabled ones has no way into the console -- which is the state this exists
    for. Keying on the row alone would leave it locked out.
    """

    created = ensure_admin_account(service)
    assert created is not None
    with service._connect() as conn:
        conn.execute("UPDATE users SET status = 'disabled' WHERE lower(role) = 'admin'")
        conn.commit()

    assert active_admin_exists(service) is False
    assert ensure_admin_account(service, username="admin2") is not None


def test_an_ordinary_account_does_not_prevent_the_bootstrap(service) -> None:
    """Somebody registering first must not lock the console shut forever."""

    service.create_user_with_role(username="alice", password="Alice-Passw0rd!", role="viewer")

    assert ensure_admin_account(service) is not None


# --- the ways it would become a vulnerability --------------------------------


def test_there_is_no_default_password(service) -> None:
    """The generated password must be unguessable, not a shipped constant.

    Two runs against two databases must not produce the same secret; if they
    did, reading this repository would be enough to sign in to any first-run
    installation on the internet.
    """

    first = ensure_admin_account(service)
    assert first is not None and first.generated_password

    with service._connect() as conn:
        conn.execute("DELETE FROM users")
        conn.commit()
    second = ensure_admin_account(service)

    assert second is not None and second.generated_password
    assert second.generated_password != first.generated_password
    assert len(first.generated_password) >= 20


@pytest.mark.parametrize("_run", range(8))
def test_a_generated_password_always_satisfies_the_policy(_run: int) -> None:
    """By construction rather than by retrying, so it cannot loop or emit a
    password the service would then refuse."""

    validate_password(generate_password())


def test_an_existing_account_is_never_promoted(service) -> None:
    """A username collision must not hand somebody the admin role.

    `admin` is a name an ordinary person can register. Raising their role
    because the bootstrap wanted that name is privilege escalation triggered by
    a string.
    """

    service.create_user_with_role(username=DEFAULT_ADMIN_USERNAME, password="Regular-Passw0rd!", role="viewer")

    with pytest.raises(AdminBootstrapError, match="will not be promoted"):
        ensure_admin_account(service)

    with service._connect() as conn:
        (role,) = conn.execute("SELECT role FROM users WHERE lower(username) = ?", (DEFAULT_ADMIN_USERNAME,)).fetchone()
    assert role == "viewer"
    assert active_admin_exists(service) is False


def test_a_weak_supplied_password_is_refused_rather_than_replaced(service) -> None:
    """Generating a different one would leave the operator unable to sign in
    with what they set, and nothing would say why."""

    with pytest.raises(AdminBootstrapError, match="does not meet the policy"):
        ensure_admin_account(service, password="short")

    assert active_admin_exists(service) is False


def test_a_supplied_password_is_used_and_never_echoed(service, monkeypatch: pytest.MonkeyPatch) -> None:
    """The operator already has it; repeating it puts a secret somewhere new."""

    monkeypatch.setenv("ADMIN_PASSWORD", "Operator-Chosen-1!")

    created = ensure_admin_account(service)

    assert created is not None
    assert created.generated_password is None
    assert service.login(created.username, "Operator-Chosen-1!")["user"]["role"] == "admin"
    assert "Operator-Chosen-1!" not in describe_bootstrap(created)


def test_the_username_can_be_chosen(service, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "root-operator")

    created = ensure_admin_account(service)

    assert created is not None
    assert created.username == "root-operator"


# --- what the operator is shown ----------------------------------------------


def test_the_generated_password_is_shown_once(service) -> None:
    created = ensure_admin_account(service)
    assert created is not None and created.generated_password

    shown = describe_bootstrap(created)

    assert created.generated_password in shown
    assert created.username in shown


def test_the_password_is_never_written_through_the_logger(service, caplog: pytest.LogCaptureFixture) -> None:
    """`setup_log_capture()` buffers records for the admin console's log viewer.

    A generated password sitting in that buffer is readable by every
    administrator added later, which is a wider audience than the one person
    who is supposed to see it. It goes to stderr instead.
    """

    with caplog.at_level("DEBUG"):
        created = ensure_admin_account(service)

    assert created is not None and created.generated_password
    assert created.generated_password not in caplog.text
    assert created.username in caplog.text


def test_the_bootstrap_reads_no_committed_default(service) -> None:
    """A credential in a tracked configuration layer is a shipped credential.

    `ADMIN_PASSWORD` deliberately is not a `Settings` field, so the render step
    cannot place one -- but a plain grep is what catches somebody adding it to
    `config/env/*` anyway, where it would look exactly like a live setting.
    """

    repo = Path(__file__).resolve().parents[2]
    layers = [*(repo / "config" / "env").rglob("*"), *(repo / "config" / "profiles").rglob("*")]
    offenders = [
        path.relative_to(repo)
        for path in layers
        if path.is_file() and "ADMIN_PASSWORD" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not offenders, f"a committed layer sets ADMIN_PASSWORD: {offenders}"
    assert os.getenv("ADMIN_PASSWORD") is None
