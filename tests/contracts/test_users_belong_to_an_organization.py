"""Accounts belong to an organization, and documents follow their owner's (BUG-04).

Driven through the real `AuthDBService` and the real registry and corpus files,
because the defect lived in what the signed-in user dict carried: with no
`tenant_id` on it, every caller fell back to the user id, and a public document
could only ever be seen by its uploader.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.core.config import Settings, get_settings
from app.retrievers.stores.corpus import read_corpus_records, write_corpus_records
from app.retrievers.stores.parent import read_parent_records, write_parent_records
from app.services.auth.auth_service import AUTH_MIGRATIONS, AuthDBService
from app.services.documents import tenancy
from app.services.documents.registry import create_document_record, list_document_records
from app.services.runtime.sqlite_schema import ensure_schema
from app.services.security.access_scope import list_visible_document_rows
from app.services.tables.store import TableStore

PASSWORD = "Tenant-Test-Passw0rd-2026"


@pytest.fixture
def env(settings_env, tmp_path, monkeypatch):
    settings_env(
        CORPUS_STORE_PATH=str(tmp_path / "chunks" / "chunks.jsonl"),
        PARENT_STORE_PATH=str(tmp_path / "chunks" / "parents.jsonl"),
        UPLOADS_DIR=str(tmp_path / "uploads"),
        DATA_DIR=str(tmp_path / "docs"),
    )
    tables = TableStore()
    monkeypatch.setattr("app.services.tables.store._GLOBAL_TABLE_STORE._value", tables)
    vector_calls: list[tuple] = []

    def fake_vectors(collection, owner, tenant, only_from):
        vector_calls.append((collection, owner, tenant, only_from))
        return 0

    monkeypatch.setattr("app.retrievers.stores.vector.retag_owner_metadata", fake_vectors)
    monkeypatch.setattr("app.services.runtime.invalidation.announce", lambda *_: None)
    return {"tmp": tmp_path, "tables": tables, "vector_calls": vector_calls}


def _signed_in(service: AuthDBService, username: str) -> dict:
    created = service.register(username, PASSWORD)
    token = service.create_session_for_user(created)["token"]
    return service.get_user_by_token(token)


def test_a_new_account_joins_the_default_organization(env):
    service = AuthDBService()
    user = _signed_in(service, "alice")

    assert user["tenant_id"] == get_settings().default_tenant_id == "default"
    assert service.get_user_profile(user["user_id"])["tenant_id"] == "default"


def test_two_accounts_see_each_others_public_uploads(env):
    """The measurement BUG-04 recorded, end to end through the user dict: bob saw nothing."""
    service = AuthDBService()
    alice, bob = _signed_in(service, "alice"), _signed_in(service, "bob")
    source = str(env["tmp"] / "uploads" / alice["user_id"] / "handbook.pdf")
    rows = [
        {
            "source": source,
            "document_id": "doc-1",
            "owner_user_id": alice["user_id"],
            "tenant_id": tenancy.tenant_of(alice),
            "visibility": "public",
        }
    ]

    def sees(user):
        return [r["document_id"] for r in list_visible_document_rows(user, indexed_rows=rows)]

    assert sees(alice) == ["doc-1"]
    assert sees(bob) == ["doc-1"]


def test_the_migration_puts_existing_accounts_in_the_default_organization(tmp_path, settings_env):
    settings_env()
    db = tmp_path / "old.db"
    ensure_schema(db, "auth", AUTH_MIGRATIONS[:1], wal=True)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute(
            "INSERT INTO users(user_id, username, salt, password_hash, created_at) VALUES('u1','old','s','h','t')"
        )
        conn.commit()

    ensure_schema(db, "auth", AUTH_MIGRATIONS, wal=True)

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT tenant_id FROM users WHERE user_id='u1'").fetchone() == ("default",)


def test_the_default_organization_may_not_be_the_shared_corpus():
    with pytest.raises(ValueError):
        Settings(DEFAULT_TENANT_ID="shared")


def _seed_legacy_documents(env, owner_id: str) -> None:
    source = str(env["tmp"] / "uploads" / owner_id / "a.txt")
    create_document_record(
        source=source,
        filename="a.txt",
        sha256="0" * 64,
        owner_user_id=owner_id,
        visibility="public",
        agent_class="general",
        tenant_id=owner_id,
    )
    meta = {"source": source, "owner_user_id": owner_id, "tenant_id": owner_id}
    write_corpus_records([{"id": "c1", "text": "x", "metadata": dict(meta)}])
    write_parent_records([{"id": "p1", "text": "x", "metadata": dict(meta)}])


def test_retagging_moves_an_owners_documents_in_every_store(env):
    _seed_legacy_documents(env, "alice")

    report = tenancy.retag_owner("alice", "acme")

    assert (report.registry, report.chunks, report.parents) == (1, 1, 1)
    assert list_document_records()[0]["tenant_id"] == "acme"
    assert read_corpus_records()[0]["metadata"]["tenant_id"] == "acme"
    assert read_parent_records()[0]["metadata"]["tenant_id"] == "acme"
    assert {call[0] for call in env["vector_calls"]} == {None, "image_descriptions", "table_summaries"}
    assert tenancy.retag_owner("alice", "acme").total == 0, "a second run changes nothing"


def test_only_from_leaves_already_moved_rows_alone(env):
    _seed_legacy_documents(env, "alice")
    tenancy.retag_owner("alice", "acme")

    report = tenancy.retag_owner("alice", "default", only_from="alice")

    assert report.total == 0
    assert list_document_records()[0]["tenant_id"] == "acme"


def test_the_one_time_migration_moves_legacy_rows_to_the_owners_organization(env):
    service = AuthDBService()
    alice = _signed_in(service, "alice")
    _seed_legacy_documents(env, alice["user_id"])
    app_db = get_settings().app_db_path

    assert tenancy.migrate_legacy_document_tenants(app_db) == []

    assert list_document_records()[0]["tenant_id"] == "default"
    assert json.loads(json.dumps(read_corpus_records()))[0]["metadata"]["tenant_id"] == "default"
    assert (Path(app_db).parent / ".tenants-migrated-v1").exists()
    _seed_legacy_documents(env, alice["user_id"])
    assert tenancy.migrate_legacy_document_tenants(app_db) == []
    assert read_corpus_records()[0]["metadata"]["tenant_id"] == alice["user_id"], "the marker makes it run once"


def test_memory_stays_where_it_is_when_a_user_changes_organization(tmp_path):
    from app.memory.long_term import memory_base_dir

    assert memory_base_dir(tmp_path, tenant_id="acme", user_id="alice") == memory_base_dir(
        tmp_path, tenant_id="alice", user_id="alice"
    )
