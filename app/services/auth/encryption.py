import base64
import hashlib
import hmac
import logging
import secrets
from typing import Any

from app.services.security.audit_actions import AuditAction

logger = logging.getLogger(__name__)


API_KEY_ENC_PREFIX = "enc:v1:"

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


def stream_xor(data: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < len(data):
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(data, out[: len(data)], strict=False))


def encrypt_secret_text(plaintext: str, key: bytes) -> str:
    if not plaintext:
        return ""
    nonce = secrets.token_bytes(16)
    cipher = stream_xor(plaintext.encode("utf-8"), key, nonce)
    tag = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    token = base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")
    return f"{API_KEY_ENC_PREFIX}{token}"


def decrypt_secret_text(value: str, key: bytes) -> str:
    text = str(value or "")
    if not text:
        return ""
    if not text.startswith(API_KEY_ENC_PREFIX):
        return text
    raw = text[len(API_KEY_ENC_PREFIX) :]
    decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    if len(decoded) < 32:
        raise ValueError("invalid encrypted payload")
    nonce = decoded[:16]
    tag = decoded[16:32]
    cipher = decoded[32:]
    expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("encrypted payload integrity check failed")
    plain = stream_xor(cipher, key, nonce)
    return plain.decode("utf-8")


def encrypt_api_settings_payload(payload: dict[str, Any], key: bytes) -> dict[str, Any]:
    out = dict(payload)
    api_key = str(out.get("api_key", "") or "").strip()
    if not api_key:
        out["api_key"] = ""
        return out
    if api_key.startswith(API_KEY_ENC_PREFIX):
        return out
    out["api_key"] = encrypt_secret_text(api_key, key)
    return out


def decrypt_api_settings_payload(payload: dict[str, Any], key: bytes, audit_logger=None) -> dict[str, Any]:
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
        out["api_key"] = decrypt_secret_text(raw_key, key)
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
