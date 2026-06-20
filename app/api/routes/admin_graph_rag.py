"""
Admin endpoints for Graph RAG monitoring and management.

Provides endpoints to:
- View cache statistics
- Clear caches
- View configuration
- Monitor performance
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import _require_permission, _require_user
from app.agents.graph_rag_cache import (
    clear_all_caches,
    get_cache_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/graph-rag", tags=["admin", "graph-rag"])


@router.get("/cache/stats")
async def get_graph_rag_cache_stats(
    request: Request,
    user: dict = Depends(_require_user),
) -> dict[str, Any]:
    """
    Get Graph RAG cache statistics.

    Returns cache hit rates, sizes, and other metrics for:
    - PDF quality analysis cache
    - Entity extraction cache
    - Document context cache

    Requires admin permission.
    """
    _require_permission(user, "admin:audit_read", request, "admin")
    stats = get_cache_stats()

    # Calculate aggregate stats
    total_hits = sum(cache["hits"] for cache in stats.values())
    total_misses = sum(cache["misses"] for cache in stats.values())
    total_requests = total_hits + total_misses
    overall_hit_rate = total_hits / total_requests if total_requests > 0 else 0.0

    return {
        "caches": stats,
        "aggregate": {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_requests": total_requests,
            "overall_hit_rate": overall_hit_rate,
        },
    }


@router.post("/cache/clear")
async def clear_graph_rag_caches(
    request: Request,
    user: dict = Depends(_require_user),
) -> dict[str, str]:
    """
    Clear all Graph RAG caches.

    This will force all subsequent queries to recompute:
    - PDF quality analysis
    - Entity extraction
    - Document context

    Use this when:
    - Configuration has changed
    - Document content has been updated
    - Testing different strategies

    Requires admin permission.
    """
    _require_permission(user, "admin:ops_manage", request, "admin")
    clear_all_caches()
    logger.info("Graph RAG caches cleared by admin")

    return {
        "status": "success",
        "message": "All Graph RAG caches cleared",
    }


@router.get("/config")
async def get_graph_rag_config(
    request: Request,
    user: dict = Depends(_require_user),
) -> dict[str, Any]:
    """
    Get current Graph RAG configuration.

    Returns key thresholds, parameters, and settings.

    Requires admin permission.
    """
    _require_permission(user, "admin:audit_read", request, "admin")
    from app.agents.graph_rag_config import (
        DENSITY_ACCEPTABLE_MAX,
        DENSITY_ACCEPTABLE_MIN,
        DENSITY_OPTIMAL_MAX,
        DENSITY_OPTIMAL_MIN,
        GRAPH_PARAMS_HIGH_QUALITY,
        GRAPH_PARAMS_LOW_QUALITY,
        GRAPH_PARAMS_MEDIUM_QUALITY,
        MIN_ENTITIES_FOR_HIGH_CONFIDENCE,
        MIN_ENTITIES_FOR_MEDIUM_CONFIDENCE,
        QUALITY_THRESHOLD_HIGH,
        QUALITY_THRESHOLD_LOW,
        QUALITY_THRESHOLD_MEDIUM,
    )
    from app.core.config import get_settings

    settings = get_settings()

    return {
        "enhanced_mode": settings.graph_rag_enhanced,
        "min_pdf_quality": settings.graph_rag_min_pdf_quality,
        "thresholds": {
            "quality_high": QUALITY_THRESHOLD_HIGH,
            "quality_medium": QUALITY_THRESHOLD_MEDIUM,
            "quality_low": QUALITY_THRESHOLD_LOW,
            "entities_high_confidence": MIN_ENTITIES_FOR_HIGH_CONFIDENCE,
            "entities_medium_confidence": MIN_ENTITIES_FOR_MEDIUM_CONFIDENCE,
        },
        "density_ranges": {
            "optimal": [DENSITY_OPTIMAL_MIN, DENSITY_OPTIMAL_MAX],
            "acceptable": [DENSITY_ACCEPTABLE_MIN, DENSITY_ACCEPTABLE_MAX],
        },
        "graph_parameters": {
            "high_quality": GRAPH_PARAMS_HIGH_QUALITY,
            "medium_quality": GRAPH_PARAMS_MEDIUM_QUALITY,
            "low_quality": GRAPH_PARAMS_LOW_QUALITY,
        },
    }


@router.get("/health")
async def graph_rag_health_check(
    request: Request,
    user: dict = Depends(_require_user),
) -> dict[str, Any]:
    """
    Health check for Graph RAG system.

    Checks:
    - Neo4j connectivity
    - Cache status
    - Configuration validity

    Requires admin permission.
    """
    _require_permission(user, "admin:audit_read", request, "admin")
    from app.graph.neo4j_client import Neo4jClient

    health = {
        "status": "healthy",
        "checks": {},
    }

    # Check Neo4j connectivity
    try:
        client = Neo4jClient()
        client.close()
        health["checks"]["neo4j"] = {"status": "ok"}
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["neo4j"] = {
            "status": "error",
            "error": str(e),
        }

    # Check cache status
    try:
        stats = get_cache_stats()
        total_size = sum(cache["size"] for cache in stats.values())
        health["checks"]["cache"] = {
            "status": "ok",
            "total_entries": total_size,
        }
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["cache"] = {
            "status": "error",
            "error": str(e),
        }

    return health
