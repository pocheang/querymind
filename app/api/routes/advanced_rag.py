"""
API routes for advanced RAG functionality.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.dependencies import _require_permission, _require_user
from app.api.utils.document_helpers import _allowed_sources_for_user
from app.api.utils.error_responses import internal_error
from app.models.advanced_rag_models import AdvancedRAGResult
from app.workflow.advanced_rag_workflow import AdvancedRAGWorkflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advanced-rag", tags=["advanced-rag"])


class AdvancedRAGRequest(BaseModel):
    """Request model for advanced RAG query."""

    query: str = Field(..., description="User query")
    enable_decomposition: bool = Field(
        default=False,
        description="Enable query decomposition",
    )
    enable_self_rag: bool = Field(
        default=False,
        description="Enable Self-RAG evaluation",
    )
    allowed_sources: list[str] | None = Field(
        default=None,
        description="Optional list of allowed sources",
    )
    retrieval_strategy: str | None = Field(
        default=None,
        description="Optional retrieval strategy",
    )


def _resolve_advanced_allowed_sources(
    user: dict[str, Any],
    requested_sources: list[str] | None,
) -> list[str]:
    visible_sources = _allowed_sources_for_user(user)
    if requested_sources is None:
        return visible_sources

    requested = {str(source or "").strip() for source in requested_sources if str(source or "").strip()}
    if not requested:
        return []
    return [source for source in visible_sources if source in requested]


@router.post("/query", response_model=AdvancedRAGResult)
async def process_advanced_rag_query(
    request_data: AdvancedRAGRequest,
    request: Request,
    user: dict[str, Any] = Depends(_require_user),
):
    """
    Process query with advanced RAG techniques.

    This endpoint supports:
    - Query decomposition: Break complex queries into simpler sub-queries
    - Self-RAG: Evaluate retrieval relevance and answer quality

    Args:
        request_data: AdvancedRAGRequest with query and configuration

    Returns:
        AdvancedRAGResult with complete processing results
    """
    _require_permission(user, "query:run", request, "advanced-rag")
    try:
        workflow = AdvancedRAGWorkflow(
            enable_decomposition=request_data.enable_decomposition,
            enable_self_rag=request_data.enable_self_rag,
        )
        allowed_sources = _resolve_advanced_allowed_sources(user, request_data.allowed_sources)

        return await workflow.process_query(
            query=request_data.query,
            allowed_sources=allowed_sources,
            retrieval_strategy=request_data.retrieval_strategy,
        )
    except Exception as e:
        logger.error(f"Error processing advanced RAG query: {e}", exc_info=True)
        raise internal_error(f"Error processing query: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "advanced-rag",
        "features": {
            "query_decomposition": True,
            "self_rag": True,
        },
    }


@router.get("/config")
async def get_config():
    """Get current advanced RAG configuration."""
    import os

    return {
        "query_decomposition": {
            "enabled_by_default": os.getenv("ENABLE_QUERY_DECOMPOSITION", "false").lower() == "true",
            "max_sub_queries": int(os.getenv("QUERY_DECOMPOSITION_MAX_SUBQUERIES", "4")),
        },
        "self_rag": {
            "enabled_by_default": os.getenv("ENABLE_SELF_RAG", "false").lower() == "true",
            "relevance_threshold": float(os.getenv("SELF_RAG_RELEVANCE_THRESHOLD", "0.6")),
            "quality_threshold": float(os.getenv("SELF_RAG_QUALITY_THRESHOLD", "0.7")),
        },
    }
