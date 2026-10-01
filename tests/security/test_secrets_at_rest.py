"""Stored credentials are AES-GCM, bound to their record, and nothing else is read (SEC-07).

Each test pins one of the four things v1 got wrong: a single key for both
encryption and authentication (now HKDF subkeys -- not observable from
outside, so it is pinned by the format, not by a test); no associated data, so
two rows' ciphertexts could be swapped; no key id; and an unprefixed value
handed back as if it had been decrypted, so anyone able to write the database
could plant a "credential". Plus the one-time migration that makes refusing
the old forms safe.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest

from app.services.auth.encryption import (
    SECRET_PREFIX,
    SecretFormatError,
    _legacy_keystream_xor,
    connector_secret_context,
    decrypt_secret_text,
    encrypt_secret_text,
    encryption_key_from_seed,
    key_id,
    system_secret_context,
)
from app.services.auth.secret_migration import migrate_stored_secrets

SEED = "s" * 48
KEY = encryption_key_from_seed(SEED)
OTHER_KEY = encryption_key_from_seed("t" * 48)
ALICE = connector_secret_context("alice", "github")
BOB = connector_secret_context("bob", "github")


def _v1(plaintext: str, key: bytes = KEY) -> str:
    nonce = b"\x01" * 16
    cipher = _legacy_keystream_xor(plaintext.encode("utf-8"), key, nonce)
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    return "enc:v1:" + base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")


def test_a_round_trip_names_the_key_it_was_written_under():
    stored = encrypt_secret_text("ghp-placeholder-value", KEY, context=ALICE)

    assert stored.startswith(f"{SECRET_PREFIX}{key_id(KEY)}:")
    assert decrypt_secret_text(stored, KEY, context=ALICE) == "ghp-placeholder-value"


def test_a_ciphertext_moved_to_another_record_does_not_decrypt():
    stored = encrypt_secret_text("ghp-placeholder-value", KEY, context=ALICE)

    with pytest.raises(ValueError, match="integrity"):
        decrypt_secret_text(stored, KEY, context=BOB)


@pytest.mark.parametrize("planted", ["planted-plaintext-value", _v1("planted-plaintext-value")], ids=["plain", "v1"])
def test_anything_but_the_current_format_is_refused(planted):
    with pytest.raises(SecretFormatError):
        decrypt_secret_text(planted, KEY, context=ALICE)


def test_another_key_is_named_not_reported_as_tampering():
    stored = encrypt_secret_text("ghp-placeholder-value", OTHER_KEY, context=ALICE)

    with pytest.raises(SecretFormatError, match="another key"):
        decrypt_secret_text(stored, KEY, context=ALICE)


def test_a_flipped_byte_is_refused():
    stored = encrypt_secret_text("ghp-placeholder-value", KEY, context=ALICE)
    raw = bytearray(base64.urlsafe_b64decode(stored.rsplit(":", 1)[1]))
    raw[-1] ^= 1
    tampered = stored.rsplit(":", 1)[0] + ":" + base64.urlsafe_b64encode(bytes(raw)).decode("ascii")

    with pytest.raises(ValueError, match="integrity"):
        decrypt_secret_text(tampered, KEY, context=ALICE)


def test_a_secret_must_be_bound_to_something():
    with pytest.raises(ValueError):
        encrypt_secret_text("ghp-placeholder-value", KEY, context="")


# --- the one-time migration ---------------------------------------------------


@pytest.fixture
def app_db(tmp_path):
    db = tmp_path / "app.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute(
            "CREATE TABLE connector_credentials (credential_id TEXT PRIMARY KEY, connector_id TEXT, "
            "owner_id TEXT, encrypted_secret TEXT, display_value TEXT)"
        )
        conn.execute("CREATE TABLE system_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
        conn.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY, settings TEXT)")
        rows = [("c-v1", "github", "alice", _v1("from-v1")), ("c-plain", "jira", "alice", "from-plaintext")]
        conn.executemany("INSERT INTO connector_credentials VALUES (?, ?, ?, ?, '')", rows)
        conn.execute(
            "INSERT INTO system_settings VALUES ('global_model_settings', ?, '')",
            (json.dumps({"provider": "openai", "api_key": _v1("model-key")}),),
        )
    return db


def _settings(db, seed: str = SEED):
    return SimpleNamespace(api_settings_encryption_key=seed, app_db_path=str(db))


def _credential(db, credential_id: str) -> str:
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(
            "SELECT encrypted_secret FROM connector_credentials WHERE credential_id=?", (credential_id,)
        ).fetchone()[0]


def test_the_migration_upgrades_every_store_and_runs_once(app_db):
    report = migrate_stored_secrets(_settings(app_db))

    assert report.upgraded == 3
    assert report.unreadable == []
    assert decrypt_secret_text(_credential(app_db, "c-v1"), KEY, context=ALICE) == "from-v1"
    jira = connector_secret_context("alice", "jira")
    assert decrypt_secret_text(_credential(app_db, "c-plain"), KEY, context=jira) == "from-plaintext"
    with closing(sqlite3.connect(app_db)) as conn:
        payload = json.loads(conn.execute("SELECT value FROM system_settings").fetchone()[0])
    assert payload["provider"] == "openai"
    assert decrypt_secret_text(payload["api_key"], KEY, context=system_secret_context("global_model_settings")) == (
        "model-key"
    )

    assert migrate_stored_secrets(_settings(app_db)).upgraded == 0


def test_a_value_the_key_cannot_read_is_left_alone_and_reported(app_db):
    with closing(sqlite3.connect(app_db)) as conn, conn:
        conn.execute(
            "UPDATE connector_credentials SET encrypted_secret=? WHERE credential_id='c-v1'", (_v1("x", OTHER_KEY),)
        )
    before = _credential(app_db, "c-v1")

    report = migrate_stored_secrets(_settings(app_db))

    assert report.unreadable == ["connector_credentials:c-v1"]
    assert _credential(app_db, "c-v1") == before


def test_without_a_key_nothing_is_touched(app_db):
    before = _credential(app_db, "c-plain")

    assert migrate_stored_secrets(_settings(app_db, seed="")).upgraded == 0
    assert _credential(app_db, "c-plain") == before


# --- through the credential service ---------------------------------------


def test_the_credential_service_binds_each_secret_to_its_owner_and_connector(tmp_path):
    from app.services.connectors.repository import CredentialRepository
    from app.services.connectors.service import ConnectorCredentialService

    db = tmp_path / "creds.db"
    with closing(sqlite3.connect(db)) as conn, conn:  # the credential table references users
        conn.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO users VALUES ('alice')")
    repository = CredentialRepository(db)
    service = ConnectorCredentialService(repository, encryption_key=KEY)
    alice = service.store(connector_id="github", owner_id="alice", secret="ghp-placeholder-value")

    assert service.resolve(alice.credential_id, owner_id="alice") == "ghp-placeholder-value"
    stored = repository.get_for_owner(alice.credential_id, "alice").encrypted_secret
    with pytest.raises(ValueError):
        decrypt_secret_text(stored, KEY, context=BOB)
