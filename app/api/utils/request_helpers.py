"""Request parameter extraction helpers."""

from typing import Any


def get_string_param(
    data: dict[str, Any],
    key: str,
    default: str = "",
    lowercase: bool = False,
) -> str:
    """
    Extract and normalize a string parameter from request data.

    Args:
        data: Request data dictionary
        key: Parameter key
        default: Default value if key not found
        lowercase: Whether to convert to lowercase

    Returns:
        Normalized string value
    """
    value = str(data.get(key, default) or default).strip()
    return value.lower() if lowercase else value


def get_optional_string_param(
    data: dict[str, Any],
    key: str,
    lowercase: bool = False,
) -> str | None:
    """
    Extract and normalize an optional string parameter.

    Args:
        data: Request data dictionary
        key: Parameter key
        lowercase: Whether to convert to lowercase

    Returns:
        Normalized string value or None if empty
    """
    value = get_string_param(data, key, "", lowercase)
    return value if value else None


def get_int_param(
    data: dict[str, Any],
    key: str,
    default: int = 0,
) -> int:
    """
    Extract an integer parameter from request data.

    Args:
        data: Request data dictionary
        key: Parameter key
        default: Default value if key not found or invalid

    Returns:
        Integer value
    """
    try:
        return int(data.get(key, default))
    except (ValueError, TypeError):
        return default


def get_bool_param(
    data: dict[str, Any],
    key: str,
    default: bool = False,
) -> bool:
    """
    Extract a boolean parameter from request data.

    Args:
        data: Request data dictionary
        key: Parameter key
        default: Default value if key not found

    Returns:
        Boolean value
    """
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return default
