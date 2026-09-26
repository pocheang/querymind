import copy
import json
import logging

from app.services.runtime.redis_connector import RedisConnector
from app.services.runtime.resilience import TTLCache

logger = logging.getLogger(__name__)

_RETRIEVAL_CACHE: TTLCache | None = None
# Bytes, not str: cached payloads are JSON that `json.loads` takes either way,
# and this is what the client was configured with before the connector existed.
_REDIS = RedisConnector(
    "retrieval_cache",
    max_connections=50,
    socket_keepalive=True,
    socket_connect_timeout=5,
    socket_timeout=5,
    decode_responses=False,
    health_check_interval=30,
)


def _mark_redis_unavailable(exc: BaseException) -> None:
    """Discard a failed client so retrieval immediately falls back to memory."""
    _REDIS.drop(exc)
    logger.warning("Redis retrieval cache unavailable; using memory cache: %s", exc)


def cache_backend(settings) -> str:
    """Determine which cache backend to use."""
    raw = str(getattr(settings, "retrieval_cache_backend", "auto") or "auto").strip().lower()
    if raw in {"off", "none", "disabled"}:
        return "off"
    if raw in {"memory", "redis"}:
        return raw
    return "auto"


def redis_client(settings):  # noqa: ARG001 -- the URL is read from settings at connect time
    """The shared client, or None while Redis is unavailable or cooling down.

    A failed connect used to leave no cooldown behind, so with Redis unreachable
    every query paid the 5 second connect timeout again; the connector waits
    `COOLDOWN_SECONDS` before the next attempt.
    """
    return _REDIS.client()


def get_retrieval_cache(settings) -> TTLCache:
    """Get or create the in-memory retrieval cache."""
    global _RETRIEVAL_CACHE
    if _RETRIEVAL_CACHE is None:
        _RETRIEVAL_CACHE = TTLCache(
            ttl_seconds=int(getattr(settings, "retrieval_cache_ttl_seconds", 45) or 45),
            max_items=int(getattr(settings, "retrieval_cache_max_items", 256) or 256),
        )
    return _RETRIEVAL_CACHE


def clear_retrieval_cache() -> None:
    """Clear both memory and Redis caches."""
    global _RETRIEVAL_CACHE
    _RETRIEVAL_CACHE = None
    try:
        from app.core.config import get_settings

        settings = get_settings()
        backend = cache_backend(settings)
        if backend not in {"redis", "auto"}:
            return
        client = redis_client(settings)
        if client is None:
            return
        keys = list(client.scan_iter(match="retrieval:*", count=500))
        if keys:
            client.delete(*keys)
    except (ImportError, AttributeError) as e:
        logger.debug(f"Cache clear skipped: {e}")
        return
    except Exception:
        logger.exception("Unexpected error clearing cache")
        return


def drop_local_retrieval_cache() -> None:
    """Forget this process's in-memory results; Redis entries are left to their keys (below)."""
    global _RETRIEVAL_CACHE
    _RETRIEVAL_CACHE = None


def _shared() -> bool:
    from app.services.runtime.shared_state import is_shared

    return is_shared()


def _redis_key(cache_key: str) -> str | None:
    """The Redis key for a result, or None when it must not be cached at all.

    With STATE_BACKEND=shared the corpus generation is part of the key (ARC-01
    phase 6). A delete on one worker used to leave its results in every other
    worker's memory layer -- which lookups fell back to -- and even in Redis a
    result computed just before a change could be stored just after it. Keyed on
    the generation, a lookup can only find results built from the corpus this
    process has caught up to. Before its first look there is no generation to
    trust, so nothing is cached.
    """
    if not _shared():
        return f"retrieval:{cache_key}"
    from app.services.runtime.invalidation import generation

    corpus = generation("corpus")
    return None if corpus is None else f"retrieval:g{corpus}:{cache_key}"


def _uses_memory_layer() -> bool:
    # Per process, so never with shared state: nothing tells one worker's memory
    # that another worker deleted a document.
    return not _shared()


def _redis_lookup(settings, key: str):
    client = redis_client(settings)
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception as e:
        _mark_redis_unavailable(e)
        logger.debug(f"Redis cache lookup failed: {type(e).__name__}")
        return None
    if not raw:
        return None
    payload = json.loads(raw)
    out_diag = dict(payload.get("diagnostics", {}))
    out_diag["cache_hit"] = True
    out_diag["cache_backend"] = "redis"
    return list(payload.get("results", [])), out_diag


def _memory_lookup(settings, cache_key: str):
    cached = get_retrieval_cache(settings).get(cache_key)
    if not cached:
        return None
    # Deep copies on the way out as well as in: Redis returns a fresh decode of
    # JSON on every hit, and a memory layer handing out the objects it holds
    # let whoever received a hit rewrite the next caller's results
    # (tests/contracts/test_retrieval_cache_contract.py).
    results, diagnostics = copy.deepcopy(cached)
    out_diag = dict(diagnostics)
    out_diag["cache_hit"] = True
    out_diag["cache_backend"] = "memory"
    return list(results), out_diag


def _enabled(settings) -> bool:
    return bool(getattr(settings, "retrieval_cache_enabled", True)) and cache_backend(settings) != "off"


def _redis_allowed(settings) -> bool:
    # Shared state forces Redis whatever RETRIEVAL_CACHE_BACKEND says (ARC-01 B2).
    return _shared() or cache_backend(settings) in {"redis", "auto"}


def cache_lookup(cache_key: str, settings, traced_span_fn):
    """Look up cached results from Redis or memory."""
    if not _enabled(settings):
        return None
    with traced_span_fn("retrieval.cache_lookup", {"backend": cache_backend(settings)}):
        key = _redis_key(cache_key)
        if key is not None and _redis_allowed(settings):
            hit = _redis_lookup(settings, key)
            if hit is not None:
                return hit
        if _uses_memory_layer():
            return _memory_lookup(settings, cache_key)
    return None


def _redis_store(settings, key: str, results: list, diagnostics: dict, ttl_seconds: int) -> None:
    client = redis_client(settings)
    if client is None:
        diagnostics["cache_backend"] = "memory" if _uses_memory_layer() else "none"
        return
    try:
        client.setex(key, ttl_seconds, json.dumps({"results": results, "diagnostics": diagnostics}, ensure_ascii=False))
        diagnostics["cache_backend"] = "redis"
        diagnostics["cache_ttl"] = ttl_seconds
    except (json.JSONEncodeError, TypeError) as e:
        logger.debug(f"Redis cache store failed (serialization): {e}")
        diagnostics["cache_backend"] = "memory" if _uses_memory_layer() else "none"
    except Exception as e:
        _mark_redis_unavailable(e)
        logger.debug(f"Redis cache store failed: {e}")
        diagnostics["cache_backend"] = "memory" if _uses_memory_layer() else "none"


def cache_store(cache_key: str, results: list, diagnostics: dict, settings, ttl_override: int = None):
    """
    Store results in cache (memory and optionally Redis).

    Args:
        cache_key: Cache key
        results: Results to cache
        diagnostics: Diagnostic information
        settings: Settings object
        ttl_override: Optional TTL override (seconds). If None, uses settings default.
    """
    if not _enabled(settings):
        return
    ttl_seconds = (
        ttl_override if ttl_override is not None else int(getattr(settings, "retrieval_cache_ttl_seconds", 45) or 45)
    )
    if _uses_memory_layer():
        # Retrieval returns the list it has just cached, and its callers go on to
        # rerank and mask it; a shallow copy kept their edits in the cache.
        get_retrieval_cache(settings).set(cache_key, copy.deepcopy((list(results), dict(diagnostics))))
    key = _redis_key(cache_key)
    if key is not None and _redis_allowed(settings):
        _redis_store(settings, key, results, diagnostics, ttl_seconds)
    elif _uses_memory_layer():
        diagnostics["cache_backend"] = "memory"
