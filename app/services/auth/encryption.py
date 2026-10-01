import base64
import hashlib
import logging
import secrets
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import hmac as crypto_hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.services.security.audit_actions import AuditAction

logger = logging.getLogger(__name__)


MIN_ENCRYPTION_SEED_LENGTH = 32
_GENERATE_HINT = "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"


def encryption_key_from_seed(seed: str) -> bytes:
    """The 32-byte key the stored credentials are encrypted with, from API_SETTINGS_ENCRYPTION_KEY.

    One definition for both stores that use it (user API settings and connector
    credentials), so they cannot derive different keys from the same setting.

    SHA-256 is a sound way to turn a random secret into a key and a poor way to
    turn a passphrase into one: it is fast, so a short human-chosen value falls
    to a dictionary. Nothing checked which of the two an operator supplied, so a
    value shorter than 32 characters is refused rather than used. The derivation
    itself is unchanged, so every existing ciphertext still decrypts.
    """

    value = str(seed or "").strip()
    if not value:
        raise RuntimeError(f"API_SETTINGS_ENCRYPTION_KEY is required. {_GENERATE_HINT}")
    if len(value) < MIN_ENCRYPTION_SEED_LENGTH:
        raise RuntimeError(
            f"API_SETTINGS_ENCRYPTION_KEY must be at least {MIN_ENCRYPTION_SEED_LENGTH} characters "
            f"(got {len(value)}): it is hashed straight into a key, so it has to be a random secret, "
            f"not a password. {_GENERATE_HINT}"
        )
    return hashlib.sha256(value.encode("utf-8")).digest()


class SecretFormatError(ValueError):
    """A stored secret is not in the current format, or not under this key."""


# enc:v2:<kid>:<base64(nonce || ciphertext || tag)>, AES-256-GCM (SEC-07).
#
# What v1 got wrong, each fixed here: one key both encrypted (an HMAC
# keystream) and authenticated -- v2 derives separate subkeys with HKDF; the
# ciphertext was bound to nothing, so two rows' values could be swapped and
# both still decrypted -- v2 authenticates a caller-supplied context (owner and
# connector, or the setting's name) as associated data; the prefix named a
# format and no key, so a rotated key failed as "integrity check failed" --
# v2 carries a key id; and a value without the prefix was returned as if it
# had been decrypted, so anyone able to write the database could plant a
# "credential" -- v2 refuses it.
SECRET_PREFIX = "enc:v2:"
_LEGACY_V1_PREFIX = "enc:v1:"
# Kept under its old name for the callers that test "is this already stored".
API_KEY_ENC_PREFIX = SECRET_PREFIX
_NONCE_BYTES = 12


def _subkey(master: bytes, purpose: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"querymind/" + purpose).derive(master)


def connector_secret_context(owner_id: str, connector_id: str) -> str:
    return f"connector-credential:{owner_id}:{connector_id}"


def system_secret_context(setting_key: str) -> str:
    return f"system-settings:{setting_key}:api_key"


def user_secret_context(user_id: str) -> str:
    return f"user-settings:{user_id}:api_settings:api_key"


def key_id(master: bytes) -> str:
    """Names the key a value was written under; reveals nothing about it."""
    return _subkey(master, b"key-id").hex()[:12]


def encrypt_secret_text(plaintext: str, key: bytes, *, context: str) -> str:
    if not plaintext:
        return ""
    if not context:
        raise ValueError("a secret must be bound to the record it belongs to")
    nonce = secrets.token_bytes(_NONCE_BYTES)
    sealed = AESGCM(_subkey(key, b"secret-at-rest/aes-gcm/v2")).encrypt(
        nonce, plaintext.encode("utf-8"), context.encode("utf-8")
    )
    token = base64.urlsafe_b64encode(nonce + sealed).decode("ascii")
    return f"{SECRET_PREFIX}{key_id(key)}:{token}"


def decrypt_secret_text(value: str, key: bytes, *, context: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if not text.startswith(SECRET_PREFIX):
        # Includes enc:v1 and plaintext: `python -m app.init_app` upgrades what
        # was stored before v2, so anything else was written around the code.
        raise SecretFormatError("stored secret is not in the current encrypted format")
    kid, _, token = text[len(SECRET_PREFIX) :].partition(":")
    if kid != key_id(key):
        raise SecretFormatError(f"stored secret was encrypted under another key (kid {kid})")
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        plain = AESGCM(_subkey(key, b"secret-at-rest/aes-gcm/v2")).decrypt(
            raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], context.encode("utf-8")
        )
    except (InvalidTag, ValueError) as exc:
        raise ValueError("encrypted payload integrity check failed") from exc
    return plain.decode("utf-8")


def upgrade_secret_text(value: str, key: bytes, *, context: str) -> str | None:
    """The value re-encrypted in the current format, or None if nothing to do.

    For the one-time migration only: it is the single place the v1 format and
    unprefixed plaintext are still read.
    """

    text = str(value or "")
    if not text or text.startswith(SECRET_PREFIX):
        return None
    plain = _decrypt_legacy_v1(text, key) if text.startswith(_LEGACY_V1_PREFIX) else text
    return encrypt_secret_text(plain, key, context=context)


def _legacy_mac(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA256 under a key derived from the random API_SETTINGS_ENCRYPTION_KEY.

    The v1 format's keystream and tag. A MAC under a random key, not password
    hashing, which is what CodeQL's py/weak-sensitive-data-hashing reads it as
    (alerts #15 and #16 were dismissed as false positives on the v1 writer).
    """

    mac = crypto_hmac.HMAC(key, hashes.SHA256())
    mac.update(data)
    return mac.finalize()


def _legacy_keystream_xor(data: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < len(data):
        out.extend(_legacy_mac(key, nonce + counter.to_bytes(8, "big")))
        counter += 1
    return bytes(a ^ b for a, b in zip(data, out[: len(data)], strict=False))


def _decrypt_legacy_v1(value: str, key: bytes) -> str:
    decoded = base64.urlsafe_b64decode(value[len(_LEGACY_V1_PREFIX) :].encode("ascii"))
    if len(decoded) < 32:
        raise ValueError("invalid encrypted payload")
    nonce, tag, cipher = decoded[:16], decoded[16:32], decoded[32:]
    if not secrets.compare_digest(tag, _legacy_mac(key, nonce + cipher)[:16]):
        raise ValueError("encrypted payload integrity check failed")
    return _legacy_keystream_xor(cipher, key, nonce).decode("utf-8")


def encrypt_api_settings_payload(payload: dict[str, Any], key: bytes, *, context: str) -> dict[str, Any]:
    out = dict(payload)
    api_key = str(out.get("api_key", "") or "").strip()
    if not api_key:
        out["api_key"] = ""
        return out
    if api_key.startswith(API_KEY_ENC_PREFIX):
        return out
    out["api_key"] = encrypt_secret_text(api_key, key, context=context)
    return out


def decrypt_api_settings_payload(
    payload: dict[str, Any], key: bytes, audit_logger=None, *, context: str
) -> dict[str, Any]:
    """
    解密API设置中的敏感字段

    Args:
        payload: 要解密的payload
        key: 加密密钥
        audit_logger: 可选的审计日志记录器（用于记录解密失败事件）

    Returns:
        解密后的payload
    """
    out = dict(payload)
    raw_key = str(out.get("api_key", "") or "")
    if not raw_key:
        out["api_key"] = ""
        return out
    try:
        out["api_key"] = decrypt_secret_text(raw_key, key, context=context)
    except (ValueError, TypeError) as e:
        # 安全修复：记录解密失败事件到审计日志（可能表示攻击）
        logger.warning(f"Failed to decrypt API key: {e}")
        if audit_logger:
            try:
                audit_logger.log(
                    action=AuditAction.API_KEY_DECRYPTION_FAILED,
                    resource_type="api_settings",
                    result="failed",
                    detail=f"decryption_error: {type(e).__name__}",
                )
            except Exception:
                pass  # 不因审计日志失败而中断
        out["api_key"] = ""
    except Exception as e:
        # Unexpected decryption error
        logger.exception("Unexpected error decrypting API key")
        if audit_logger:
            try:
                audit_logger.log(
                    action=AuditAction.API_KEY_DECRYPTION_ERROR,
                    resource_type="api_settings",
                    result="failed",
                    detail=f"unexpected_error: {type(e).__name__}",
                )
            except Exception:
                pass
        out["api_key"] = ""
    return out
