"""A public document is visible to its owner's organization, and only to it (BUG-04).

Before organizations existed the uploader *was* the tenant: uploads were tagged
with the uploader's user id, the tenant boundary ran ahead of the `public`
grant, and a document approved as public stayed visible to its uploader alone.
Measured then: alice (owner) True, bob (viewer) False, carol (admin) False.

These tests use the row shape the upload path writes -- `tenant_id` from the
signed-in user dict, which now carries the organization -- rather than a shape
written for the test (TST-01).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.api.routes.public import documents as documents_routes
from app.services.documents import tenancy
from app.services.security.access_scope import list_visible_document_rows

_ROOT = (Path(__file__).resolve().parent / "_visibility_fixture").resolve()


class _Settings:
    docs_path = _ROOT / "docs"
    uploads_path = _ROOT / "uploads"


def _user(user_id: str, tenant_id: str, role: str = "viewer") -> dict:
    """The signed-in user dict `get_user_by_token` returns."""
    return {"user_id": user_id, "tenant_id": tenant_id, "role": role, "permissions": ()}


def _upload_row(owner: dict, name: str, visibility: str) -> dict:
    """What `register_and_enqueue_uploads` records for an upload by `owner`."""
    return {
        "source": str(_ROOT / "uploads" / owner["user_id"] / name),
        "document_id": f"doc-{name}",
        "owner_user_id": owner["user_id"],
        "tenant_id": tenancy.tenant_of(owner),
        "visibility": visibility,
    }


def _sees(user: dict, rows: list[dict]) -> set[str]:
    return {row["document_id"] for row in list_visible_document_rows(user, indexed_rows=rows, settings=_Settings())}


ALICE = _user("alice", "acme")
BOB = _user("bob", "acme")
CAROL = _user("carol", "globex")


def test_a_public_upload_is_visible_to_the_rest_of_the_organization():
    rows = [_upload_row(ALICE, "handbook.pdf", "public")]

    assert _sees(ALICE, rows) == {"doc-handbook.pdf"}
    assert _sees(BOB, rows) == {"doc-handbook.pdf"}


def test_a_public_upload_does_not_cross_into_another_organization():
    rows = [_upload_row(ALICE, "handbook.pdf", "public")]

    assert _sees(CAROL, rows) == set()


def test_a_private_upload_stays_with_its_owner_inside_the_organization():
    rows = [_upload_row(ALICE, "salary.xlsx", "private")]

    assert _sees(ALICE, rows) == {"doc-salary.xlsx"}
    assert _sees(BOB, rows) == set()


def test_an_owner_reaches_a_row_still_tagged_the_pre_organization_way():
    """Until the one-time migration runs, rows carry the owner's user id as tenant."""
    legacy = {**_upload_row(ALICE, "notes.md", "private"), "tenant_id": "alice"}

    assert _sees(ALICE, [legacy]) == {"doc-notes.md"}
    assert _sees(BOB, [legacy]) == set()


def test_an_owner_moved_to_another_organization_still_reaches_their_documents():
    row = _upload_row(ALICE, "notes.md", "public")
    moved_alice = _user("alice", "globex")

    assert _sees(moved_alice, [row]) == {"doc-notes.md"}


def test_the_upload_route_tags_a_document_with_the_organization_not_the_user():
    """The route reads the tenant through `tenant_of`; the regression was the user id here."""
    assert "tenant_id=tenant_of(user)" in Path(documents_routes.__file__).read_text(encoding="utf-8")
    assert tenancy.tenant_of(ALICE) == "acme"


def test_a_user_dict_without_an_organization_is_its_own_tenant():
    assert tenancy.tenant_of({"user_id": "dave"}) == "dave"


@pytest.mark.parametrize("bad", ["shared", "", " ", "a/b", "../x", "x" * 65, "-lead"])
def test_an_organization_id_is_validated(bad):
    with pytest.raises(ValueError):
        tenancy.validate_tenant_id(bad)


def test_an_ordinary_organization_id_is_accepted():
    assert tenancy.validate_tenant_id("acme-eu_2") == "acme-eu_2"
