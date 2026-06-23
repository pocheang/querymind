"""Token hashing utilities for admin operations."""

import hashlib


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256.

    Args:
        token: Token string to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token_hash(token: str, expected_hash: str) -> bool:
    """
    Verify a token against an expected hash.

    Args:
        token: Token string to verify
        expected_hash: Expected hash value

    Returns:
        True if token matches hash
    """
    return hash_token(token) == expected_hash
