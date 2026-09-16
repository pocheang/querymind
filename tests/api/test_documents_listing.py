"""Listing documents must not 500 for anyone who actually has one.

`GET /documents` answered a bare `500 Internal Server Error` to every caller
with at least one visible document, from 2026-09-09 (`e6beeacd`, the commit
that added `can_manage`) until this fix. The handler's last loop was written
against `IndexedFileSummary` objects:

    source = str(getattr(summary, "source", "") or "").strip()
    summary.can_manage = ...

but `merge_visible_document_status` returns plain dicts -- `response_model`
coerces them into the model on the way *out*, which is what made the object
form look right. So `getattr(row, "source")` silently answered `""` (defect
one: `can_manage` could only ever have been False), and the assignment raised
`AttributeError` (defect two, which hid the first).

Two things kept it alive. A caller with **no** documents never enters the loop
and gets a clean `200 []`, so a fresh account looks healthy -- which is why a
test asserting only the status code would have passed on the broken code for
the easiest fixture to write. And nothing in `tests/` touched this endpoint at
all.

What the reader saw was worse than an error: the sidebar rendered "No indexed
docs yet" with no toast, on an account holding two indexed documents. A page
reporting the opposite of the truth.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps.auth import _require_user
from app.api.routes.public import documents as documents_routes

OWNED = "data/uploads/u-1/report.pdf"
SHARED = "data/docs/corpus/handbook.md"

USER: dict[str, Any] = {"user_id": "u-1", "username": "owner", "role": "viewer"}


def _row(source: str, filename: str) -> dict[str, Any]:
    return {"source": source, "filename": filename, "chunks": 3, "owner_user_id": "u-1"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """The real handler, with only its collaborators stubbed.

    `_require_permission` and the two document helpers are replaced; the loop
    under test, the `response_model` coercion and the routing are real.
    """
    monkeypatch.setattr(documents_routes, "_require_permission", lambda *a, **k: None)
    # Manageable is "under uploads_path" -- the shared corpus never is.
    monkeypatch.setattr(
        documents_routes,
        "_is_source_manageable_for_user",
        lambda source, user: source.startswith("data/uploads/"),
    )

    app = FastAPI()
    app.include_router(documents_routes.router)
    app.dependency_overrides[_require_user] = lambda: USER
    return TestClient(app)


def _serve(monkeypatch: pytest.MonkeyPatch, rows: list[dict[str, Any]]) -> None:
    monkeypatch.setattr(documents_routes, "_list_visible_documents_for_user", lambda user: list(rows))
    monkeypatch.setattr(
        documents_routes,
        "merge_visible_document_status",
        lambda indexed_rows, **kwargs: [dict(row) for row in indexed_rows],
    )


def test_merge_visible_document_status_hands_back_plain_dicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """The assumption the handler is written against, pinned at the source.

    Without this, the stub in `_serve` below would be asserting its own shape:
    if the registry ever started returning models, these tests would keep
    passing while the handler broke again in the other direction.
    """
    from app.services.documents import registry

    monkeypatch.setattr(registry, "list_document_records", lambda: [])
    merged = registry.merge_visible_document_status([_row(OWNED, "report.pdf")], user_id="u-1", role="viewer")

    assert merged, "expected the indexed row to survive the merge"
    assert all(isinstance(item, dict) for item in merged)


def test_a_caller_with_documents_gets_them(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """The case that 500'd: one visible document is enough to enter the loop."""
    _serve(monkeypatch, [_row(OWNED, "report.pdf")])

    response = client.get("/documents")

    assert response.status_code == 200, response.text
    assert [item["filename"] for item in response.json()] == ["report.pdf"]


def test_can_manage_is_computed_per_row_rather_than_left_at_its_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both values in one response, because `can_manage` defaults to False.

    Asserting only the False case would pass on a handler that never set the
    field at all -- and on the shipped one, whose `getattr(dict, "source")`
    made every row unmanageable before the assignment even raised.
    """
    _serve(monkeypatch, [_row(OWNED, "report.pdf"), _row(SHARED, "handbook.md")])

    body = client.get("/documents").json()
    by_name = {item["filename"]: item["can_manage"] for item in body}

    assert by_name == {"report.pdf": True, "handbook.md": False}


def test_a_caller_with_no_documents_still_gets_an_empty_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The state that masked the defect for nine days: the loop never runs."""
    _serve(monkeypatch, [])

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []
