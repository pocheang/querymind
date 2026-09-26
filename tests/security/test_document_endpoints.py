"""Document management endpoints must not reach outside what the caller can see.

Exercises the real routes, because the defect lived in the route body rather
than in a helper:

    source = normalize_string(source) or _resolve_manageable_source_for_filename(filename, user)

Supplying `?source=` skipped the visibility resolution entirely, leaving only a
directory check -- and that check granted admins the whole uploads root. So
`DELETE /documents/report.pdf?source=/uploads/bob/report.pdf` acted on Bob's
file, while the same admin could not even list it. See P0-3 in
docs/superpowers/plans/2026-08-29-user-data-isolation.md.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes.public import documents as documents_route

ALICE_SOURCE = "/uploads/alice/report.pdf"
BOB_SOURCE = "/uploads/bob/report.pdf"

_ROWS = [
    {
        "filename": "report.pdf",
        "source": ALICE_SOURCE,
        "document_id": "doc-alice",
        "owner_user_id": "alice",
        "tenant_id": "alice",
        "visibility": "private",
        "chunks": 3,
    },
    {
        "filename": "notes.pdf",
        "source": "/uploads/alice/notes.pdf",
        "document_id": "doc-alice-notes",
        "owner_user_id": "alice",
        "tenant_id": "alice",
        "visibility": "private",
        "chunks": 1,
    },
]


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """Alice's view of the world, with the destructive operations stubbed."""
    from app.api import main

    monkeypatch.setattr(documents_route, "_list_visible_documents_for_user", lambda user: [dict(r) for r in _ROWS])
    # Alice may manage her own uploads and nothing else.
    monkeypatch.setattr(
        documents_route,
        "_is_source_manageable_for_user",
        lambda source, user: str(source or "").startswith(f"/uploads/{user['user_id']}/"),
    )
    monkeypatch.setattr(
        documents_route,
        "_require_registered_filename_source",
        lambda filename, source: next(dict(r) for r in _ROWS if r["source"] == source),
    )
    monkeypatch.setattr(documents_route, "_require_permission", lambda *a, **k: None)

    performed: list[dict[str, Any]] = []
    monkeypatch.setattr(
        documents_route,
        "delete_document_index",
        lambda filename, remove_physical_file, source: (
            performed.append({"op": "delete", "filename": filename, "source": source})
            or {"ok": True, "filename": filename, "removed_chunks": 1}
        ),
    )
    # A reindex is a queued job now (ARC-01 phase 5); record which document was queued.
    monkeypatch.setattr(documents_route, "should_skip_reindex", lambda path: False)

    def queue(*, document_id, user_id):
        row = next(r for r in _ROWS if r["document_id"] == document_id)
        performed.append({"op": "reindex", "filename": row["filename"], "source": row["source"]})
        return {"status": "queued"}

    monkeypatch.setattr(documents_route, "enqueue_reindex_job", queue)

    test_client = TestClient(main.app)
    test_client.performed = performed  # type: ignore[attr-defined]
    return test_client


def _as(user_id: str, role: str = "viewer") -> dict[str, str]:
    return {"X-Test-User": user_id, "X-Test-User-Id": user_id, "X-Test-Role": role}


# --- the bypass ------------------------------------------------------------


def test_an_explicit_source_cannot_reach_another_users_file(client):
    """`?source=` narrows the candidates; it never selects one on its own."""
    response = client.delete(
        f"/documents/report.pdf?source={BOB_SOURCE}&remove_file=true",
        headers=_as("alice"),
    )

    assert response.status_code == 404
    assert client.performed == []


def test_an_admin_gets_no_further_than_anyone_else(client):
    """Role alone no longer grants the whole uploads root."""
    response = client.delete(
        f"/documents/report.pdf?source={BOB_SOURCE}",
        headers=_as("root", role="admin"),
    )

    assert response.status_code == 404
    assert client.performed == []


def test_reindex_has_the_same_boundary_as_delete(client):
    response = client.post(
        f"/documents/report.pdf/reindex?source={BOB_SOURCE}",
        headers=_as("alice"),
    )

    assert response.status_code == 404
    assert client.performed == []


# --- the ordinary path still works -----------------------------------------


def test_a_user_deletes_their_own_document_by_filename(client):
    response = client.delete("/documents/report.pdf", headers=_as("alice"))

    assert response.status_code == 200
    assert client.performed == [{"op": "delete", "filename": "report.pdf", "source": ALICE_SOURCE}]


def test_an_explicit_matching_source_still_works(client):
    """What the frontend sends: a source taken from the list it already fetched."""
    response = client.delete(
        f"/documents/report.pdf?source={ALICE_SOURCE}&remove_file=false",
        headers=_as("alice"),
    )

    assert response.status_code == 200
    assert client.performed == [{"op": "delete", "filename": "report.pdf", "source": ALICE_SOURCE}]


def test_a_user_reindexes_their_own_document(client):
    response = client.post("/documents/notes.pdf/reindex", headers=_as("alice"))

    assert response.status_code == 202
    assert client.performed == [{"op": "reindex", "filename": "notes.pdf", "source": "/uploads/alice/notes.pdf"}]


# --- addressing by immutable id --------------------------------------------


def test_delete_by_id_targets_exactly_one_document(client):
    response = client.delete("/documents/by-id/doc-alice", headers=_as("alice"))

    assert response.status_code == 200
    assert client.performed == [{"op": "delete", "filename": "report.pdf", "source": ALICE_SOURCE}]


def test_reindex_by_id_targets_exactly_one_document(client):
    response = client.post("/documents/by-id/doc-alice-notes/reindex", headers=_as("alice"))

    assert response.status_code == 202
    assert client.performed == [{"op": "reindex", "filename": "notes.pdf", "source": "/uploads/alice/notes.pdf"}]


def test_an_unknown_id_is_refused(client):
    assert client.delete("/documents/by-id/doc-bob", headers=_as("alice")).status_code == 404
    assert client.performed == []


def test_the_by_id_route_is_not_shadowed_by_the_filename_route(client):
    """`/documents/by-id/x` must not be read as a filename called `by-id`."""
    response = client.delete("/documents/by-id/doc-alice", headers=_as("alice"))

    assert response.status_code == 200
    assert client.performed[0]["filename"] == "report.pdf"


# --- audit -----------------------------------------------------------------


def test_a_successful_action_records_the_document_and_its_owner(client, monkeypatch):
    """`resource_id=filename` alone cannot tell Alice's report.pdf from Bob's."""
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(documents_route, "_audit", lambda request, **kwargs: audits.append(kwargs))

    client.delete("/documents/report.pdf", headers=_as("alice"))

    assert audits, "the action was not audited"
    detail = audits[-1]["detail"]
    assert "document_id=doc-alice" in detail
    assert "owner_user_id=alice" in detail


def test_a_refusal_is_audited_too(client, monkeypatch):
    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(documents_route, "_audit", lambda request, **kwargs: audits.append(kwargs))

    client.delete(f"/documents/report.pdf?source={BOB_SOURCE}", headers=_as("alice"))

    assert [entry["result"] for entry in audits] == ["denied"]


@pytest.mark.parametrize(("method", "suffix"), [("post", "/reindex"), ("delete", "")])
def test_a_document_with_no_chunks_is_still_reachable_by_its_id(client, monkeypatch, method, suffix):
    """A failed or not-yet-indexed document has no chunks, so its id comes only from its registry record.

    The list merged that record in and offered the retry and delete buttons;
    the action resolved against the unmerged rows and answered 404. Found by
    failing an ingest in the running stack and trying to delete the document.
    """

    from app.services.documents import registry

    source = "/uploads/alice/failed.pdf"
    on_disk_only = {"filename": "failed.pdf", "source": source, "chunks": 0, "owner_user_id": None}
    monkeypatch.setattr(documents_route, "_list_visible_documents_for_user", lambda user: [dict(on_disk_only)])
    record = {
        "document_id": "doc-alice-failed",
        "source": source,
        "filename": "failed.pdf",
        "owner_user_id": "alice",
        "tenant_id": "alice",
        "visibility": "private",
        "status": "failed",
    }
    monkeypatch.setattr(registry, "list_document_records", lambda path=None: [dict(record)])
    _ROWS.append({**on_disk_only, "document_id": "doc-alice-failed"})
    try:
        response = getattr(client, method)(f"/documents/by-id/doc-alice-failed{suffix}", headers=_as("alice"))
    finally:
        _ROWS.pop()

    assert response.status_code in {200, 202}, response.text
    assert client.performed[-1]["source"] == source
