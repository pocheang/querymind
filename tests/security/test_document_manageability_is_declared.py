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

from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_the_row_schema_carries_the_answer():
    from app.api.schemas import IndexedFileSummary

    assert "can_manage" in IndexedFileSummary.model_fields
    # Absent means "no", which is the safe direction for a control that deletes.
    assert IndexedFileSummary.model_fields["can_manage"].default is False


def test_the_listing_fills_it_from_the_predicate_the_writes_use():
    """Not a second implementation: the same function, or it will drift."""

    source = (APP / "api" / "routes" / "public" / "documents.py").read_text(encoding="utf-8")

    assert "summary.can_manage = bool(source) and _is_source_manageable_for_user(source, user)" in source
    # And the write paths still go through the resolver that applies it.
    assert "_resolve_manageable_document(filename, user, normalize_string(source))" in source


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
