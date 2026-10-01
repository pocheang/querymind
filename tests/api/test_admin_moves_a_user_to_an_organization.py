"""`PATCH /api/v1/admin/users/{id}/tenant` moves the account and the documents it owns (BUG-04).

The route is driven through a bare app with its collaborators replaced, so these
assert the route's rules: the account moves first, its documents second, the
move is audited, an invalid organization is refused with its reason, and the
shared-corpus tenant is never an organization.
"""

from __future__ import annotations

import chromadb
import pytest
from chromadb.config import Settings as ChromaSettings
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.admin import users as users_routes
from app.retrievers.stores import vector as vector_store
from app.services.documents import tenancy
from app.services.security.audit_actions import AuditAction

ADMIN = {"X-Test-User": "root", "X-Test-User-Id": "root", "X-Test-Role": "admin"}
VIEWER = {"X-Test-User": "vera", "X-Test-User-Id": "vera", "X-Test-Role": "viewer"}


class _FakeAuth:
    def __init__(self):
        self.moved: list[tuple[str, str]] = []

    def update_user_tenant(self, user_id, tenant_id):
        tenant_id = tenancy.validate_tenant_id(tenant_id)
        if user_id == "missing":
            return None
        self.moved.append((user_id, tenant_id))
        return {"user_id": user_id, "username": "alice", "role": "viewer", "status": "active", "tenant_id": tenant_id}


@pytest.fixture
def client(monkeypatch):
    auth = _FakeAuth()
    retagged: list[tuple[str, str]] = []
    audited: list[dict] = []
    monkeypatch.setattr(users_routes, "auth_service", auth)
    monkeypatch.setattr(users_routes, "_audit", lambda request, **kwargs: audited.append(kwargs))
    monkeypatch.setattr(
        tenancy,
        "retag_owner",
        lambda owner, tenant: retagged.append((owner, tenant)) or tenancy.RetagReport(registry=2),
    )
    app = FastAPI()
    app.include_router(users_routes.router, prefix="/api/v1")
    return TestClient(app), auth, retagged, audited


def test_the_account_and_its_documents_move_and_the_move_is_audited(client):
    http, auth, retagged, audited = client

    response = http.patch("/api/v1/admin/users/alice/tenant", json={"tenant_id": "globex"}, headers=ADMIN)

    assert response.status_code == 200, response.text
    assert response.json()["tenant_id"] == "globex"
    assert auth.moved == [("alice", "globex")]
    assert retagged == [("alice", "globex")]
    assert audited[-1]["action"] == AuditAction.ADMIN_USER_TENANT_UPDATE
    assert "documents=2" in audited[-1]["detail"]


@pytest.mark.parametrize("tenant", ["shared", "a/b", "-x"])
def test_an_invalid_organization_is_refused_and_nothing_moves(client, tenant):
    http, auth, retagged, _ = client

    response = http.patch("/api/v1/admin/users/alice/tenant", json={"tenant_id": tenant}, headers=ADMIN)

    assert response.status_code == 400, response.text
    assert auth.moved == []
    assert retagged == []


def test_an_unknown_user_is_404_and_nothing_moves(client):
    http, _, retagged, _ = client

    response = http.patch("/api/v1/admin/users/missing/tenant", json={"tenant_id": "acme"}, headers=ADMIN)

    assert response.status_code == 404
    assert retagged == []


def test_a_viewer_may_not_move_anyone(client):
    http, auth, _, _ = client

    response = http.patch("/api/v1/admin/users/alice/tenant", json={"tenant_id": "acme"}, headers=VIEWER)

    assert response.status_code == 403
    assert auth.moved == []


class _Store:
    """What `retag_owner_metadata` needs of a langchain Chroma store: its collection and client."""

    def __init__(self, collection, client):
        self._collection = collection
        self._client = client


def test_vector_metadata_is_retagged_without_touching_other_owners(monkeypatch):
    # The same settings as every other ephemeral client in the suite: Chroma keeps
    # one in-process instance and refuses a second with different settings.
    client = chromadb.EphemeralClient(settings=ChromaSettings(anonymized_telemetry=False))
    collection = client.get_or_create_collection("retag_probe")
    collection.upsert(
        ids=["a1", "a2", "b1"],
        embeddings=[[0.1, 0.2], [0.2, 0.1], [0.3, 0.3]],
        metadatas=[
            {"owner_user_id": "alice", "tenant_id": "alice", "source": "s1"},
            {"owner_user_id": "alice", "tenant_id": "acme", "source": "s2"},
            {"owner_user_id": "bob", "tenant_id": "bob", "source": "s3"},
        ],
    )
    monkeypatch.setattr(vector_store, "_store_for", lambda name: _Store(collection, client))

    moved = vector_store.retag_owner_metadata(None, "alice", "globex", only_from="alice")

    rows = collection.get(include=["metadatas"])
    tenants = dict(zip(rows["ids"], (m["tenant_id"] for m in rows["metadatas"]), strict=True))
    assert moved == 1
    assert tenants == {"a1": "globex", "a2": "acme", "b1": "bob"}
    source = dict(zip(rows["ids"], (m["source"] for m in rows["metadatas"]), strict=True))
    assert source["a1"] == "s1", "the rest of the metadata is kept"
