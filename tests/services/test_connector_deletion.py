"""A credential a user handed over must be one they can take back.

Connectors could be created, listed, enabled, disabled and probed. There was no
delete -- not on the router, not on `ConnectorManagementService`, not on either
repository. So an encrypted third-party secret, once stored, stayed stored: its
owner could stop it being used and never remove it.

Found by cleaning up after an end-to-end run on 2026-09-09, when
`DELETE /api/v1/connectors/falcon-runbook` returned 404 and grepping the router
showed why. It is the same class as the per-user model API keys purged earlier
that day -- a store the person who filled it cannot empty.

`disable` is not the same thing and must stay: stopping a suspect integration
while keeping the record of it is a real need, which is why this is a new verb
rather than a change to that one.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.services.connectors.management import ConnectorManagementService
from app.services.connectors.metadata_repository import ConnectorMetadataRepository
from app.services.connectors.repository import CredentialRepository
from app.services.connectors.service import ConnectorCredentialService

_OWNER = "user-alice"
_INTRUDER = "user-mallory"
_KEY = b"0" * 32
# Deliberately not shaped like a real credential. The first version of this
# fixture was, and the pre-commit gate refused the commit -- correctly. What
# these tests need is a string that round-trips through encryption and then
# stops resolving, not something that looks like anybody's token.
_SECRET = "connector-secret-for-this-test"


@pytest.fixture
def db_path():
    # Deliberately not the tmp_path fixture, for the reason its sibling suite
    # gives: that basetemp root needs directory permissions which are not
    # available on every Windows checkout.
    root = Path(tempfile.mkdtemp(prefix="querymind-connector-delete-"))
    path = root / "app.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO users VALUES (?)", [(_OWNER,), (_INTRUDER,)])
    conn.commit()
    conn.close()
    try:
        yield path
    finally:
        shutil.rmtree(root, ignore_errors=True)


async def _unreachable_probe(base_url, allowed_hosts):  # pragma: no cover - never called here
    raise AssertionError("deletion must not probe anything")


@pytest.fixture
def parts(db_path):
    metadata_repo = ConnectorMetadataRepository(db_path)
    credential_repo = CredentialRepository(db_path)
    credentials = ConnectorCredentialService(credential_repo, encryption_key=_KEY)
    service = ConnectorManagementService(metadata_repo, credentials, probe=_unreachable_probe)
    return service, metadata_repo, credential_repo, credentials


def _create(service, connector_id: str = "falcon-runbook", owner_id: str = _OWNER):
    return service.create(
        connector_id=connector_id,
        owner_id=owner_id,
        name="Falcon runbook",
        base_url="https://api.example.com/v1",
        allowed_hosts=frozenset({"api.example.com"}),
        secret=_SECRET,
    )


def _credential_id(service, connector_id: str) -> str:
    metadata = service._repository.get(connector_id, _OWNER)
    assert metadata is not None
    return metadata.credential_id


def test_deleting_a_connector_removes_it(parts):
    """The regression proper: there was no `delete` to call at all."""

    service, *_ = parts
    _create(service)

    service.delete("falcon-runbook", _OWNER)

    assert service.list_for_owner(_OWNER) == ()


def test_the_credential_goes_with_it(parts):
    """The half that matters. Metadata is a label; the credential is the secret.

    A delete that left the ciphertext behind would remove the only name anything
    had for it -- strictly worse than not deleting, because the row would then be
    unreachable by its owner and still on disk.
    """

    service, _metadata_repo, credential_repo, _credentials = parts
    created = _create(service)
    credential_id = _credential_id(service, created.connector_id)
    assert credential_repo.get_for_owner(credential_id, _OWNER) is not None

    service.delete(created.connector_id, _OWNER)

    with sqlite3.connect(credential_repo.db_path) as conn:
        remaining = conn.execute("SELECT COUNT(*) FROM connector_credentials").fetchone()[0]
    assert remaining == 0, "the encrypted secret outlived the connector that named it"


def test_the_secret_cannot_be_resolved_afterwards(parts):
    """Resolution is the only reader; after a delete it must refuse."""

    service, _metadata_repo, _credential_repo, credentials = parts
    created = _create(service)
    credential_id = _credential_id(service, created.connector_id)
    assert credentials.resolve(credential_id, owner_id=_OWNER) == _SECRET

    service.delete(created.connector_id, _OWNER)

    with pytest.raises(PermissionError):
        credentials.resolve(credential_id, owner_id=_OWNER)


def test_another_owner_cannot_delete_it(parts):
    """Scoped like every other verb here, and checked before anything is
    destroyed -- a refusal that had already dropped the credential would be a
    denial of service anyone could trigger."""

    service, _metadata_repo, credential_repo, credentials = parts
    created = _create(service)
    credential_id = _credential_id(service, created.connector_id)

    with pytest.raises(KeyError):
        service.delete(created.connector_id, _INTRUDER)

    assert service.list_for_owner(_OWNER)[0].connector_id == created.connector_id
    assert credentials.resolve(credential_id, owner_id=_OWNER) == _SECRET
    assert credential_repo.get_for_owner(credential_id, _INTRUDER) is None


def test_an_unknown_connector_raises_rather_than_reporting_success(parts):
    """The route turns this into 404. Reporting success would tell somebody
    their credential was destroyed when it was not."""

    service, *_ = parts

    with pytest.raises(KeyError):
        service.delete("never-existed", _OWNER)


def test_the_credential_is_destroyed_before_the_metadata(parts):
    """The residue an interrupted delete leaves is a choice, so it is pinned.

    The two stores are separate connections on the app database -- this codebase
    has no shared pool on purpose -- so the pair is not atomic. Metadata gone
    with ciphertext left is a secret nothing can name; metadata left with the
    ciphertext gone is a connector its owner can see and delete again. Only the
    second is recoverable, so the credential goes first.
    """

    service, metadata_repo, credential_repo, _credentials = parts
    created = _create(service)
    credential_id = _credential_id(service, created.connector_id)

    def _explode(connector_id: str, owner_id: str) -> bool:
        raise sqlite3.OperationalError("database is locked")

    metadata_repo.delete = _explode  # type: ignore[method-assign]

    with pytest.raises(sqlite3.OperationalError):
        service.delete(created.connector_id, _OWNER)

    assert credential_repo.get_for_owner(credential_id, _OWNER) is None


def test_deleting_twice_is_not_a_crash_at_the_store(parts):
    """Both halves are idempotent, which is what makes the retry above work."""

    service, metadata_repo, credential_repo, _credentials = parts
    created = _create(service)
    credential_id = _credential_id(service, created.connector_id)

    assert metadata_repo.delete(created.connector_id, _OWNER) is True
    assert metadata_repo.delete(created.connector_id, _OWNER) is False
    assert credential_repo.delete_for_owner(credential_id, _OWNER) is True
    assert credential_repo.delete_for_owner(credential_id, _OWNER) is False


def test_deleting_one_connector_leaves_the_others(parts):
    """A delete keyed on the owner alone would empty the drawer."""

    service, *_ = parts
    _create(service, "falcon-runbook")
    _create(service, "pager")

    service.delete("falcon-runbook", _OWNER)

    assert [item.connector_id for item in service.list_for_owner(_OWNER)] == ["pager"]


# --- over HTTP, which is where the missing verb was noticed ------------------


@pytest.fixture
def client(parts):
    """The real router, with only the service dependency swapped for this
    fixture's own stores. The route body is what turns a `KeyError` into a 404,
    so it has to be exercised rather than reasoned about."""

    from fastapi.testclient import TestClient

    import app.api.main as main
    from app.api.deps.runtime import get_connector_service

    service, *_ = parts
    main.app.dependency_overrides[get_connector_service] = lambda: service
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.pop(get_connector_service, None)


def _as(user_id: str) -> dict[str, str]:
    return {"X-Test-User": user_id, "X-Test-User-Id": user_id, "X-Test-Role": "viewer"}


def test_the_endpoint_exists_and_is_a_delete():
    """The one that would have caught the whole gap: there was no such route."""

    import app.api.main as main

    operations = main.app.openapi()["paths"]["/api/v1/connectors/{connector_id}"]

    assert "delete" in operations, "DELETE /api/v1/connectors/{connector_id} is missing"


def test_a_delete_returns_204_with_no_body(client, parts):
    service, *_ = parts
    _create(service)

    response = client.delete("/api/v1/connectors/falcon-runbook", headers=_as(_OWNER))

    assert response.status_code == 204
    assert response.content == b""
    assert service.list_for_owner(_OWNER) == ()


def test_deleting_somebody_elses_connector_is_a_404(client, parts):
    """404 rather than 403, like every other owner-scoped route here: telling
    the caller the connector exists is itself a disclosure.

    Both 404 tests assert the *message* as well as the status, and that is not
    decoration. With no route registered at all, FastAPI answers this DELETE
    with its own 404 -- so status alone passes on exactly the code these exist
    to reject, which is the vacuous assertion this repository keeps recording.
    `not_found("Connector")` is the route speaking.
    """

    service, *_ = parts
    _create(service)

    response = client.delete("/api/v1/connectors/falcon-runbook", headers=_as(_INTRUDER))

    assert response.status_code == 404
    assert response.json()["detail"] == "Connector not found"
    assert service.list_for_owner(_OWNER)[0].connector_id == "falcon-runbook"


def test_deleting_an_unknown_connector_is_a_404(client):
    response = client.delete("/api/v1/connectors/never-existed", headers=_as(_OWNER))

    assert response.status_code == 404
    assert response.json()["detail"] == "Connector not found"
