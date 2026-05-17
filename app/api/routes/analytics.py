"""
Analytics API Routes

Provides endpoints for retrieval analytics, agent performance, and document popularity.
"""

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.services.retrieval_logger import RetrievalLogger

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def get_analytics_overview():
    """
    Get high-level analytics overview.

    Returns:
        AnalyticsOverview: Total statistics including query count, success rate,
                          performance metrics, and distribution by agent/route
    """
    logger = RetrievalLogger.get_instance()
    return logger.get_overview()


@router.get("/agents")
async def get_agent_stats():
    """
    Get agent performance analysis.

    Returns:
        list[AgentStats]: Performance statistics for each agent class,
                         sorted by query count descending
    """
    logger = RetrievalLogger.get_instance()
    return logger.get_agent_stats()


@router.get("/documents")
async def get_document_stats(limit: int = Query(default=20, ge=1, le=100)):
    """
    Get document popularity ranking.

    Args:
        limit: Maximum number of documents to return (1-100, default: 20)

    Returns:
        list[DocumentStats]: Document usage statistics sorted by retrieval count
    """
    logger = RetrievalLogger.get_instance()
    return logger.get_document_stats(limit=limit)


@router.get("/export")
async def export_logs(format: str = Query(default="json", pattern="^(json|csv)$")):
    """
    Export retrieval logs.

    Args:
        format: Export format - "json" or "csv" (default: json)

    Returns:
        Response: Exported data with appropriate Content-Type headers
    """
    logger = RetrievalLogger.get_instance()
    data = logger.export_logs(format=format)

    if format == "csv":
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=retrieval_logs.csv"},
        )
    else:
        return Response(content=data, media_type="application/json")
