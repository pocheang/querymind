"""
API routes for advanced RAG functionality.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.utils.error_responses import internal_error

from app.workflow.advanced_rag_workflow import AdvancedRAGWorkflow
from app.models.advanced_rag_models import AdvancedRAGResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advanced-rag", tags=["advanced-rag"])


class AdvancedRAGRequest(BaseModel):
    """Request model for advanced RAG query."""

    query: str = Field(..., description="User query")
    enable_decomposition: bool = Field(
        default=False,
        description="Enable query decomposition"
    )
    enable_self_rag: bool = Field(
        default=False,
        description="Enable Self-RAG evaluation"
    )
    allowed_sources: Optional[List[str]] = Field(
        default=None,
        description="Optional list of allowed sources"
    )
    retrieval_strategy: Optional[str] = Field(
        default=None,
        description="Optional retrieval strategy"
    )


@router.post("/query", response_model=AdvancedRAGResult)
async def process_advanced_rag_query(request: AdvancedRAGRequest):
    """
    Process query with advanced RAG techniques.

    This endpoint supports:
    - Query decomposition: Break complex queries into simpler sub-queries
    - Self-RAG: Evaluate retrieval relevance and answer quality

    Args:
        request: AdvancedRAGRequest with query and configuration

    Returns:
        AdvancedRAGResult with complete processing results
    """
    try:
        # Initialize workflow with requested configuration
        workflow = AdvancedRAGWorkflow(
            enable_decomposition=request.enable_decomposition,
            enable_self_rag=request.enable_self_rag
        )

        # Process query
        result = await workflow.process_query(
            query=request.query,
            allowed_sources=request.allowed_sources,
            retrieval_strategy=request.retrieval_strategy
        )

        return result

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
            "self_rag": True
        }
    }


@router.get("/config")
async def get_config():
    """Get current advanced RAG configuration."""
    import os
    return {
        "query_decomposition": {
            "enabled_by_default": os.getenv("ENABLE_QUERY_DECOMPOSITION", "false").lower() == "true",
            "max_sub_queries": int(os.getenv("QUERY_DECOMPOSITION_MAX_SUBQUERIES", "4"))
        },
        "self_rag": {
            "enabled_by_default": os.getenv("ENABLE_SELF_RAG", "false").lower() == "true",
            "relevance_threshold": float(os.getenv("SELF_RAG_RELEVANCE_THRESHOLD", "0.6")),
            "quality_threshold": float(os.getenv("SELF_RAG_QUALITY_THRESHOLD", "0.7"))
        }
    }
