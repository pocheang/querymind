"""Session tags and descriptions behave the same in memory and in SQLite (ARC-01 phase 10).

`get_metadata_service` returns `SessionMetadataService` (memory) or
`SessionMetadataDB` (the default, and required by STATE_BACKEND=shared), and
session search holds whichever it got. Two differences turned up by running
one suite against both, and the database's answer is the one kept, because it
is the backend a deployment runs:

- **Order.** The database lists most recently *updated* first; memory listed
  most recently *used* first, so reading a session's metadata moved it up the
  list.
- **Snapshots.** The database hands back a fresh object on every read; memory
  handed back the object it stored, so a caller editing the value it was given
  edited the store without going through `update`.
"""

from __future__ import annotations

import time
import uuid

import pytest

from app.services.sessions.metadata import MetadataUpdate
from app.services.sessions.service import get_metadata_service


@pytest.fixture(params=["memory", "database"])
def service(request, settings_env):
    settings_env(SESSION_METADATA_BACKEND=request.param)
    return get_metadata_service(f"user-{uuid.uuid4().hex}")


def test_created_metadata_reads_back_normalised(service):
    service.create_metadata("s1", tags=["Budget", "budget", " EU "], category="work", description="  Q3 plan  ")

    stored = service.get_metadata("s1")

    assert (stored.tags, stored.category, stored.description) == (["budget", "eu"], "work", "Q3 plan")


def test_metadata_cannot_be_created_twice(service):
    service.create_metadata("s1")

    with pytest.raises(ValueError):
        service.create_metadata("s1")


def test_an_update_changes_only_what_it_names(service):
    service.create_metadata("s1", tags=["a"], description="keep")

    service.update_metadata("s1", MetadataUpdate(tags=["B"], increment_query_count=True))

    stored = service.get_metadata("s1")
    assert (stored.tags, stored.description, stored.query_count) == (["b"], "keep", 1)
    assert stored.last_query_at is not None


def test_updating_or_tagging_unknown_metadata_is_a_key_error(service):
    with pytest.raises(KeyError):
        service.update_metadata("missing", MetadataUpdate(tags=["x"]))
    with pytest.raises(KeyError):
        service.extract_and_update_auto_tags("missing", [{"role": "user", "content": "hello"}])


def test_deleting_metadata(service):
    service.create_metadata("s1")

    assert service.delete_metadata("s1") is True
    assert service.delete_metadata("s1") is False
    assert service.get_metadata("s1") is None


def test_the_list_is_most_recently_updated_first_and_reading_does_not_reorder_it(service):
    for session_id in ("a", "b", "c"):
        service.create_metadata(session_id)
        time.sleep(0.002)
    service.update_metadata("a", MetadataUpdate(description="touched"))

    service.get_metadata("c")  # a read, not an update

    assert [m.session_id for m in service.list_all_metadata()] == ["a", "c", "b"]


def test_a_returned_value_is_a_snapshot(service):
    service.create_metadata("s1", tags=["kept"])

    service.get_metadata("s1").tags.append("smuggled")
    service.list_all_metadata()[0].description = "smuggled"

    stored = service.get_metadata("s1")
    assert (stored.tags, stored.description) == (["kept"], None)


def test_tags_are_collected_across_sessions(service):
    service.create_metadata("s1", tags=["budget"])
    service.create_metadata("s2", tags=["travel", "budget"])

    assert service.get_all_tags() == ["budget", "travel"]
    stats = service.get_stats()
    assert (stats["total_sessions"], stats["total_tags"]) == (2, 2)


@pytest.mark.parametrize("backend", ["memory", "database"])
def test_one_users_metadata_is_invisible_to_another(settings_env, backend):
    settings_env(SESSION_METADATA_BACKEND=backend)
    alice = get_metadata_service(f"alice-{uuid.uuid4().hex}")
    bob = get_metadata_service(f"bob-{uuid.uuid4().hex}")
    alice.create_metadata("s1", tags=["private"])

    assert bob.get_metadata("s1") is None
    assert bob.get_all_tags() == []
