"""Cache manager initialization and lifecycle management."""

import logging

from app.core.singleton import Cell
from app.services.caching.cache_manager import CACHE_PREFIX_PATTERN, CacheManager

logger = logging.getLogger(__name__)

_cache_manager_instance = Cell[CacheManager | None](None)


def initialize_cache_manager(
    l1_max_size: int = 256,
    l1_ttl: int = 300,
    l2_enabled: bool = False,
    l2_ttl: int = 3600,
    redis_url: str | None = None,
) -> None:
    """Initialize the global cache manager.

    Args:
        l1_max_size: Maximum number of items in L1 cache
        l1_ttl: L1 cache TTL in seconds
        l2_enabled: Whether to enable L2 (Redis) cache
        l2_ttl: L2 cache TTL in seconds
        redis_url: Redis connection URL
    """

    if _cache_manager_instance.value is not None:
        logger.warning("Cache manager already initialized")
        return

    _cache_manager_instance.value = CacheManager(
        l1_max_size=l1_max_size,
        l1_ttl=l1_ttl,
        l2_enabled=l2_enabled,
        l2_ttl=l2_ttl,
        redis_url=redis_url,
    )

    _cache_manager_instance.value.initialize()
    logger.info(f"Cache manager initialized: L1={l1_max_size}, L2={'enabled' if l2_enabled else 'disabled'}")


async def close_cache_manager() -> None:
    """Close the global cache manager."""

    if _cache_manager_instance.value is None:
        return

    await _cache_manager_instance.value.close()
    _cache_manager_instance.value = None
    logger.info("Cache manager closed")


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance.

    Returns:
        CacheManager instance

    Raises:
        RuntimeError: If cache manager is not initialized
    """
    if _cache_manager_instance.value is None:
        raise RuntimeError("Cache manager not initialized. Call initialize_cache_manager() first.")

    return _cache_manager_instance.value


__all__ = ["CACHE_PREFIX_PATTERN", "initialize_cache_manager", "close_cache_manager", "get_cache_manager"]
