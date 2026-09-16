"""A listed document says whether this caller may act on it.

Visible is wider than manageable, and the gap is not derivable by the client:

* `list_visible_document_rows` includes the shared corpus under `docs_path`,
  which every signed-in user can search.
* `_is_source_manageable_for_user` requires the source to sit under
  `uploads_path` -- for administrators too, deliberately, so that a `?source=`
  cannot reach another tenant's upload.

So every shared-corpus document is readable by everyone and writable by nobody.
The Knowledge Base panel guessed instead, with a clause reading "no owner, so
anyone may manage it" -- exactly backwards here, since a `data/docs/` file has
no owner precisely because it belongs to the deployment. It therefore offered
Reindex, Del Index and Del File on every shared document, and all three answered
404. Found by dropping one file into `data/docs/` and pressing the button.

`can_manage` is answered by the same predicate the write endpoints enforce, so
an offered button is a request that will be accepted.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_the_row_schema_carries_the_answer():
    from app.api.schemas import IndexedFileSummary

    assert "can_manage" in IndexedFileSummary.model_fields
    # Absent means "no", which is the safe direction for a control that deletes.
    assert IndexedFileSummary.model_fields["can_manage"].default is False


def _list_documents_ast() -> ast.FunctionDef:
    source = (APP / "api" / "routes" / "public" / "documents.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "list_documents":
            return node
    raise AssertionError("list_documents is gone from app/api/routes/public/documents.py")


def test_the_listing_fills_it_from_the_predicate_the_writes_use():
    """Not a second implementation: the same function, or it will drift."""

    called = {
        ast.unparse(node.func)
        for node in ast.walk(_list_documents_ast())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }

    assert "_is_source_manageable_for_user" in called
    # And the write paths still go through the resolver that applies it.
    source = (APP / "api" / "routes" / "public" / "documents.py").read_text(encoding="utf-8")
    assert "_resolve_manageable_document(filename, user, normalize_string(source))" in source


def test_the_listing_writes_can_manage_onto_a_dict_rather_than_an_attribute():
    """This test used to assert the broken line, verbatim, and pass.

    It read:

        assert "summary.can_manage = bool(source) and _is_source_manageable_..."

    -- a substring match on the source text, which is true of code that raises
    the moment it runs. `merge_visible_document_status` returns plain dicts
    (`response_model` coerces them into `IndexedFileSummary` on the way out),
    so that assignment was an `AttributeError` on every caller who had a
    document, and the endpoint answered a bare 500 from 2026-09-09 until
    2026-09-16. A caller with none never entered the loop, so the shape that is
    cheapest to fixture looked healthy.

    The behaviour is pinned by `tests/api/test_documents_listing.py`, which
    drives the real handler and would have caught it. This one keeps the
    structural half, stated as the thing that actually went wrong: the rows are
    dicts, so the write must be a subscript.
    """

    targets = [
        target
        for node in ast.walk(_list_documents_ast())
        if isinstance(node, ast.Assign)
        for target in node.targets
        if "can_manage" in ast.unparse(target)
    ]

    assert targets, "nothing in list_documents sets can_manage any more"
    assert all(isinstance(target, ast.Subscript) for target in targets), (
        "can_manage is being set as an attribute again; the rows are dicts and "
        "this raises AttributeError for every caller who owns a document"
    )


def test_the_shared_corpus_is_manageable_by_nobody(monkeypatch: pytest.MonkeyPatch):
    """The property the panel got wrong, asserted directly.

    An administrator is included on purpose -- the rule is about *where the file
    lives*, not about role, and an admin reading this test should see that
    stated rather than infer it.
    """

    from app.api.deps import documents as deps

    settings = deps.settings
    shared = settings.docs_path / "falcon-runbook.md"
    own_upload = settings.uploads_path / "u-1" / "report.pdf"

    viewer = {"user_id": "u-1", "role": "viewer"}
    admin = {"user_id": "u-9", "role": "admin"}

    assert deps._is_source_manageable_for_user(str(shared), viewer) is False
    assert deps._is_source_manageable_for_user(str(shared), admin) is False
    assert deps._is_source_manageable_for_user(str(own_upload), viewer) is True

    # And the empty case, which is the one that fails open if it is forgotten.
    assert deps._is_source_manageable_for_user("", admin) is False
    assert deps._is_source_manageable_for_user(None, admin) is False


def test_the_panel_no_longer_guesses():
    """The four-clause guess must be gone, not merely joined by the real answer."""

    source = (FRONTEND / "pages" / "chat" / "components" / "DocumentItem.tsx").read_text(encoding="utf-8")

    assert "doc.can_manage" in source
    assert "!doc.owner_user_id ||" not in source, (
        "the clause that read 'nobody owns it, so anyone may manage it' is back; "
        "for the shared corpus that is exactly backwards"
    )
