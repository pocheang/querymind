"""Exporting a session must not require metadata nobody wrote.

`POST /sessions` creates a session in the history store and **no**
`SessionMetadata`; the only writers of metadata are the edit-metadata endpoint
and import itself. `export_session` opened by fetching that metadata and raising
`KeyError` when it was absent, and the route turns any exception into
`500 "Export failed"`.

So **exporting any session a user had not tagged by hand returned 500** -- which
is every session, for anybody who just asks questions. Found by pressing the
export control on a real session.

This shares a root cause with session search finding nothing: one empty metadata
store, two symptoms. The search half is a labelling problem (it really is a
metadata search); this half is a bug, because messages are the substance of a
session and tags are decoration.
"""

from __future__ import annotations

import json
from dataclasses import asdict

import pytest

from app.services.sessions.export import SessionExportService
from app.services.sessions.metadata import SessionCategory, SessionMetadata, utc_now


class _NoMetadata:
    def get_metadata(self, session_id: str):
        return None


class _WithMetadata:
    def get_metadata(self, session_id: str):
        return SessionMetadata(
            session_id=session_id,
            tags=["值班", "runbook"],
            category=SessionCategory.OTHER if hasattr(SessionCategory, "OTHER") else None,
            description="Falcon 值班复盘",
            created_at=utc_now(),
            updated_at=utc_now(),
            query_count=3,
        )


MESSAGES = [
    {"role": "user", "content": "什么是 RRF"},
    {"role": "assistant", "content": "倒数排名融合[1]。"},
]


def test_an_untagged_session_exports():
    """The regression proper: this raised `KeyError` and surfaced as a 500."""

    service = SessionExportService(metadata_service=_NoMetadata())

    exported = service.export_session(session_id="s-1", messages=MESSAGES, context=None)

    assert exported.session_id == "s-1"
    # The messages are the point of an export.
    assert exported.messages == MESSAGES


def test_the_absent_block_has_the_same_shape_as_a_present_one():
    """An importer must read one shape whether or not there was metadata."""

    absent = asdict(SessionExportService(metadata_service=_NoMetadata()).export_session("s-1", MESSAGES))
    present = asdict(SessionExportService(metadata_service=_WithMetadata()).export_session("s-1", MESSAGES))

    assert set(absent["metadata"]) == set(present["metadata"])
    assert absent["metadata"]["tags"] == []
    assert absent["metadata"]["session_id"] == "s-1"


def test_no_date_is_invented_on_export():
    """`created_at` is left null rather than stamped with the export time.

    Guessing it would give a re-imported session a date it never had, which is
    worse than admitting there is none.
    """

    exported = asdict(SessionExportService(metadata_service=_NoMetadata()).export_session("s-1", MESSAGES))

    assert exported["metadata"]["created_at"] is None
    assert exported["metadata"]["updated_at"] is None
    assert exported["metadata"]["last_query_at"] is None


def test_that_export_can_be_imported_again():
    """The half that would have broken if only the exporter were fixed.

    `_dict_to_metadata` called `datetime.fromisoformat` on those fields, and
    `fromisoformat(None)` raises -- so an export with no metadata would have
    written a file the importer could not read.
    """

    service = SessionExportService(metadata_service=_NoMetadata())
    blob = json.loads(json.dumps(asdict(service.export_session("s-1", MESSAGES))))

    restored = service._dict_to_metadata("s-1", blob["metadata"])

    assert restored.session_id == "s-1"
    assert restored.tags == []
    # A missing date becomes now, which is the truth: this metadata is being
    # created at import time.
    assert restored.created_at is not None
    assert restored.last_query_at is None


@pytest.mark.parametrize("bad", ["", "not-a-date", None])
def test_an_unreadable_date_does_not_break_an_import(bad):
    """Import is the one place a hand-edited or foreign file arrives."""

    service = SessionExportService(metadata_service=_NoMetadata())

    restored = service._dict_to_metadata("s-1", {"created_at": bad, "updated_at": bad, "last_query_at": bad})

    assert restored.created_at is not None
    assert restored.last_query_at is None
