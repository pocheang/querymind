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


def _mark_redis_unavailable(settings, exc: BaseException) -> None:  # noqa: ARG001 -- kept for its callers
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


def cache_lookup(cache_key: str, settings, traced_span_fn):
    """Look up cached results from Redis or memory."""
    backend = cache_backend(settings)
    use_cache = bool(getattr(settings, "retrieval_cache_enabled", True)) and backend != "off"
    if not use_cache:
        return None

    with traced_span_fn("retrieval.cache_lookup", {"backend": backend}):
        if backend in {"redis", "auto"}:
            client = redis_client(settings)
        else:
            client = None
        if client is not None:
            try:
                raw = client.get(f"retrieval:{cache_key}")
                if raw:
                    payload = json.loads(raw)
                    out_diag = dict(payload.get("diagnostics", {}))
                    out_diag["cache_hit"] = True
                    out_diag["cache_backend"] = "redis"
                    return list(payload.get("results", [])), out_diag
            except Exception as e:
                _mark_redis_unavailable(settings, e)
                import logging

                logging.getLogger(__name__).debug(
                    f"Redis cache lookup failed, falling back to memory: {type(e).__name__}"
                )
        cache = get_retrieval_cache(settings)
        cached = cache.get(cache_key)
        if cached:
            results, diagnostics = cached
            out_diag = dict(diagnostics)
            out_diag["cache_hit"] = True
            out_diag["cache_backend"] = "memory"
            return list(results), out_diag
    return None


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
    backend = cache_backend(settings)
    use_cache = bool(getattr(settings, "retrieval_cache_enabled", True)) and backend != "off"
    if not use_cache:
        return

    # Use adaptive TTL if provided, otherwise fall back to settings
    ttl_seconds = (
        ttl_override if ttl_override is not None else int(getattr(settings, "retrieval_cache_ttl_seconds", 45) or 45)
    )

    cache = get_retrieval_cache(settings)
    cache.set(cache_key, (list(results), dict(diagnostics)))
    if backend in {"redis", "auto"}:
        client = redis_client(settings)
        if client is not None:
            try:
                client.setex(
                    f"retrieval:{cache_key}",
                    ttl_seconds,
                    json.dumps({"results": results, "diagnostics": diagnostics}, ensure_ascii=False),
                )
                diagnostics["cache_backend"] = "redis"
                diagnostics["cache_ttl"] = ttl_seconds
            except (json.JSONEncodeError, TypeError) as e:
                logger.debug(f"Redis cache store failed (serialization): {e}")
                diagnostics["cache_backend"] = "memory"
            except Exception as e:
                _mark_redis_unavailable(settings, e)
                logger.debug(f"Redis cache store failed: {e}")
                diagnostics["cache_backend"] = "memory"
        else:
            diagnostics["cache_backend"] = "memory"
