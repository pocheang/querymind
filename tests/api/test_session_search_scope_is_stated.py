"""Session search covers metadata, and the empty state has to say so.

`POST /sessions` creates a session in `HistoryStore` and writes **no**
`SessionMetadata`; the only writers are the metadata endpoint (when a user
edits tags, category or description) and session import. `POST
/api/v1/sessions/search` reads `SessionMetadata` alone, and its text query
matches `description` -- `SessionMetadata` has no title field at all.

So on an ordinary account every search returns `{"results": [], "total": 0}`,
and the panel said "No sessions found -- try adjusting your search criteria or
filters". That sends the reader to fix a query that could never have matched,
about sessions they can see in the sidebar.

The plumbing is coherent -- it is a metadata search, not a session search -- so
what was wrong is the sentence. Making it a session search means merging two
stores, with pagination and scoring across both, and is a design change rather
than a correction.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"


def test_session_creation_writes_no_metadata():
    """The fact the sentence has to describe. If this stops being true the
    empty state is misleading in the other direction."""

    source = (ROOT / "app" / "api" / "routes" / "public" / "sessions.py").read_text(encoding="utf-8")
    create = source[source.index("def create_session(") : source.index('@router.get("/{session_id}"')]

    assert "create_metadata" not in create
    assert "_history_store_for_user(user).create_session()" in create


def test_the_text_query_has_no_title_to_match():
    """`SessionMetadata` carries no title, so searching one cannot ever work."""

    from app.services.sessions.metadata import SessionMetadata

    fields = set(SessionMetadata.__dataclass_fields__)

    assert "title" not in fields
    assert {"tags", "category", "description"} <= fields


@pytest.mark.parametrize("locale", ["en", "zh"])
def test_the_empty_state_names_what_is_searched(locale: str):
    entries = json.loads((FRONTEND / "i18n" / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
    text = entries["sessionManagement"]["searchesMetadataOnly"]

    assert text, "the key is empty"
    if locale == "en":
        assert "tags" in text.lower()
        assert "description" in text.lower()
    else:
        assert "标签" in text
        assert "描述" in text


def test_the_panel_stopped_telling_readers_to_fix_their_query():
    source = (FRONTEND / "components" / "SessionManagement" / "SessionSearch.tsx").read_text(encoding="utf-8")

    assert "sessionManagement.searchesMetadataOnly" in source
    assert "sessionManagement.tryDifferentSearch" not in source, (
        "the empty state again blames the reader's search for a store that is empty"
    )
