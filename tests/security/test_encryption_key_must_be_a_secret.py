"""API_SETTINGS_ENCRYPTION_KEY has to be a random secret, not a password.

It is hashed once with SHA-256 into the key that encrypts stored credentials
(user API settings, connector secrets). That is a sound derivation for a random
value and a weak one for a passphrase, and nothing checked which one an operator
supplied, so a short value is refused. CodeQL (#15, #16) read the SHA-256 as
password hashing, which it is not; this closes the gap its alert pointed near.

The derivation is unchanged, which is what keeps existing ciphertext readable:
that is asserted too.
"""

from __future__ import annotations

import hashlib

import pytest

from app.services.auth.encryption import (
    MIN_ENCRYPTION_SEED_LENGTH,
    decrypt_secret_text,
    encrypt_secret_text,
    encryption_key_from_seed,
)

GOOD_SEED = "q" * MIN_ENCRYPTION_SEED_LENGTH


@pytest.mark.parametrize("seed", ["", "   ", "correct horse battery", "x" * (MIN_ENCRYPTION_SEED_LENGTH - 1)])
def test_a_missing_or_short_seed_is_refused(seed):
    with pytest.raises(RuntimeError, match="API_SETTINGS_ENCRYPTION_KEY"):
        encryption_key_from_seed(seed)


def test_the_refusal_says_how_to_make_one():
    with pytest.raises(RuntimeError, match="secrets.token_urlsafe"):
        encryption_key_from_seed("short")


def test_the_derivation_is_unchanged_so_old_ciphertext_still_decrypts():
    legacy_key = hashlib.sha256(GOOD_SEED.encode("utf-8")).digest()
    stored = encrypt_secret_text("sk-live-value", legacy_key)

    assert encryption_key_from_seed(GOOD_SEED) == legacy_key
    assert decrypt_secret_text(stored, encryption_key_from_seed(GOOD_SEED)) == "sk-live-value"


def test_surrounding_whitespace_does_not_change_the_key():
    """The stores always stripped the setting before hashing; still true."""

    assert encryption_key_from_seed(f"  {GOOD_SEED}\n") == encryption_key_from_seed(GOOD_SEED)


def test_the_user_settings_store_refuses_a_short_key(monkeypatch, tmp_path):
    from app.core.config import get_settings
    from app.services.auth.auth_service import AuthDBService

    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "too-short")
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.db"))
    get_settings.cache_clear()
    try:
        service = AuthDBService()
        with pytest.raises(RuntimeError, match="at least"):
            service._api_settings_data_key()
    finally:
        get_settings.cache_clear()


def test_the_connector_store_refuses_a_short_key(monkeypatch):
    from app.core.config import get_settings
    from app.mcp import runtime

    monkeypatch.setenv("API_SETTINGS_ENCRYPTION_KEY", "too-short")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="at least"):
            runtime._build_tool_stack()
    finally:
        get_settings.cache_clear()
