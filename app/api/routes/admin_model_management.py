"""Admin model management and monitoring endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import _require_permission, _require_user
from app.services.model_catalog import list_providers
from app.services.runtime_metrics import RuntimeMetrics

router = APIRouter(prefix="/admin", tags=["admin-models"])
runtime_metrics = RuntimeMetrics()


@router.get("/model-providers/list")
def list_model_providers(
    request: Request,
    user: dict[str, Any] = Depends(_require_user),
) -> dict[str, Any]:
    """
    List all available model providers with their capabilities.

    Returns the immutable provider catalog with information about:
    - Provider names and display names
    - Chat and embedding support
    - Default models
    - API key requirements
    """
    _require_permission(user, "admin:model_settings", request, "model_providers")

    providers = list_providers()

    return {
        "ok": True,
        "providers": providers,
    }


@router.get("/model-monitor/stats")
def get_model_monitor_stats(
    request: Request,
    hours: int = 24,
    user: dict[str, Any] = Depends(_require_user),
) -> dict[str, Any]:
    """
    Get model usage statistics and monitoring data.

    Query parameters:
    - hours: Time window in hours (default: 24)

    Returns:
    - Total request counts
    - Usage breakdown by provider
    - Usage breakdown by model
    - Recent error information
    """
    _require_permission(user, "admin:model_settings", request, "model_monitor")

    # Get runtime metrics snapshot
    metrics_snapshot = runtime_metrics.snapshot()

    # For now, return basic aggregated stats
    # TODO: Enhance with actual request tracking from audit logs
    return {
        "ok": True,
        "stats": {
            "total_requests": 0,
            "by_provider": {},
            "by_model": {},
            "recent_errors": [],
            "time_window_hours": hours,
            "metrics_snapshot": metrics_snapshot,
        },
    }
