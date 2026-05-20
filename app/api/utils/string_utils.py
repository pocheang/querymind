"""String utility functions for input normalization and validation."""


def normalize_string(value: str | None, lowercase: bool = False) -> str:
    """
    Normalize a string by stripping whitespace and optionally converting to lowercase.

    Args:
        value: Input string (can be None)
        lowercase: Whether to convert to lowercase

    Returns:
        Normalized string (empty string if input is None)
    """
    result = (value or "").strip()
    return result.lower() if lowercase else result


def normalize_optional(value: str | None, lowercase: bool = False) -> str | None:
    """
    Normalize a string and return None if empty.

    Args:
        value: Input string (can be None)
        lowercase: Whether to convert to lowercase

    Returns:
        Normalized string or None if empty
    """
    result = normalize_string(value, lowercase)
    return result if result else None


def is_empty(value: str | None) -> bool:
    """Check if a string is empty after normalization."""
    return not normalize_string(value)
