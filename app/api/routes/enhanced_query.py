"""
API routes for Enhanced RAG with Quality Assurance.

POST /api/v1/enhanced/query - Execute quality-enhanced RAG query
GET /api/v1/enhanced/health - Health check
GET /api/v1/enhanced/config - Configuration info
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.dependencies import _require_permission, _require_user
from app.api.utils.document_helpers import _allowed_sources_for_user
from app.api.utils.error_responses import internal_error
from app.agents.enhanced_rag_workflow import EnhancedRAGWorkflow
from app.agents.quality_models import QualityReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/enhanced", tags=["enhanced-rag"])


# ============================================================================
# Request/Response Models
# ============================================================================


class EnhancedQueryRequest(BaseModel):
    """Request model for enhanced RAG query with quality assurance."""

    query: str = Field(..., min_length=1, description="User query text")
    session_id: str = Field(
        default="default",
        description="Conversation session ID for context tracking",
    )
    allowed_sources: Optional[List[str]] = Field(
        default=None,
        description="Optional list of allowed document sources",
    )
    retrieval_strategy: Optional[str] = Field(
        default=None,
        description="Optional retrieval strategy (hybrid, dense, bm25, rerank)",
    )
    agent_class_hint: Optional[str] = Field(
        default=None,
        description="Optional agent class hint (cybersecurity, general, pdf_text)",
    )
    enable_context_tracking: bool = Field(
        default=True,
        description="Enable multi-turn context tracking",
    )


class EnhancedQueryResponse(BaseModel):
    """Response model for enhanced RAG query."""

    answer: str = Field(..., description="Generated answer")
    citations: List[dict] = Field(default_factory=list, description="Source citations")
    quality_report: QualityReport = Field(..., description="Comprehensive quality report")
    route_used: str = Field(..., description="Route that was used")
    route_reason: str = Field(..., description="Routing reason")
    skill_used: str = Field(..., description="Skill that was used")
    agent_class: str = Field(..., description="Agent class used")
    execution_metadata: dict = Field(..., description="Performance metrics")


# ============================================================================
# Helper Functions
# ============================================================================


def _resolve_allowed_sources(
    user: dict[str, Any],
    requested_sources: Optional[List[str]],
) -> List[str]:
    """
    Resolve allowed sources based on user permissions and request.

    Args:
        user: User object with permissions
        requested_sources: Optionally requested sources

    Returns:
        List of allowed source names
    """
    visible_sources = _allowed_sources_for_user(user)

    if requested_sources is None:
        return visible_sources

    # Filter requested sources to only those user can access
    requested_set = {str(source or "").strip() for source in requested_sources if str(source or "").strip()}
    if not requested_set:
        return []

    return [source for source in visible_sources if source in requested_set]


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/query", response_model=EnhancedQueryResponse)
async def execute_enhanced_query(
    request_data: EnhancedQueryRequest,
    request: Request,
    user: dict[str, Any] = Depends(_require_user),
):
    """
    Execute quality-enhanced RAG query with comprehensive QA pipeline.

    This endpoint integrates all quality assurance agents:
    - Route Validator: Validates routing decisions with retry
    - Retrieval Quality: Assesses retrieval quality in parallel
    - Answer Validator: 4-level validation cascade with regeneration
    - Quality Orchestrator: Fuses scores into comprehensive report
    - Context Tracker: Multi-turn conversation awareness

    **Quality Levels:**
    - `high` (>= 0.85): High confidence, reliable answer
    - `medium` (0.7-0.85): Medium quality, verify with other sources
    - `low` (0.5-0.7): Low quality, use with caution
    - `very_low` (< 0.5): Very low quality, requires human review

    **Performance:**
    - Target added latency: <250ms
    - Fast path (high quality): <150ms
    - Retry mechanisms: max 1 route retry, max 1 answer retry

    Args:
        request_data: EnhancedQueryRequest with query and configuration

    Returns:
        EnhancedQueryResponse with answer, citations, and quality report
    """
    _require_permission(user, "query:run", request, "enhanced-query")

    try:
        # Resolve allowed sources based on user permissions
        allowed_sources = _resolve_allowed_sources(user, request_data.allowed_sources)

        # Initialize Enhanced RAG Workflow
        workflow = EnhancedRAGWorkflow(
            max_route_retries=1,
            max_answer_retries=1,
            enable_context_tracking=request_data.enable_context_tracking,
        )

        # Execute quality-enhanced RAG pipeline
        result = await workflow.execute_query(
            query=request_data.query,
            user_id=user.get("username", "anonymous"),
            session_id=request_data.session_id,
            allowed_sources=allowed_sources,
            retrieval_strategy=request_data.retrieval_strategy,
            agent_class_hint=request_data.agent_class_hint,
        )

        logger.info(
            f"Enhanced query completed: "
            f"user={user.get('username')}, "
            f"quality={result['quality_report'].quality_level}, "
            f"time={result['execution_metadata']['total_time_ms']}ms"
        )

        return EnhancedQueryResponse(**result)

    except Exception as e:
        logger.exception(f"Enhanced query failed: {e}")
        raise internal_error(f"Error processing enhanced query: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for enhanced RAG service.

    Returns:
        Service health status and feature availability
    """
    return {
        "status": "healthy",
        "service": "enhanced-rag",
        "features": {
            "route_validation": True,
            "retrieval_quality": True,
            "answer_validation": True,
            "quality_orchestration": True,
            "context_tracking": True,
        },
        "version": "1.0.0",
    }


@router.get("/config")
async def get_config():
    """
    Get current enhanced RAG configuration.

    Returns:
        Configuration parameters for quality assurance
    """
    from app.agents.quality_config import (
        ROUTE_HIGH_CONFIDENCE_THRESHOLD,
        ROUTE_MEDIUM_CONFIDENCE_THRESHOLD,
        RETRIEVAL_SAMPLE_TOP_K,
        ANSWER_APPROVE_THRESHOLD,
        ANSWER_FLAG_THRESHOLD,
        QUALITY_HIGH_THRESHOLD,
        QUALITY_MEDIUM_THRESHOLD,
    )

    return {
        "route_validation": {
            "high_confidence_threshold": ROUTE_HIGH_CONFIDENCE_THRESHOLD,
            "medium_confidence_threshold": ROUTE_MEDIUM_CONFIDENCE_THRESHOLD,
            "max_retries": 1,
        },
        "retrieval_quality": {
            "sample_top_k": RETRIEVAL_SAMPLE_TOP_K,
            "metrics": ["coverage", "relevance", "diversity", "completeness"],
        },
        "answer_validation": {
            "approve_threshold": ANSWER_APPROVE_THRESHOLD,
            "flag_threshold": ANSWER_FLAG_THRESHOLD,
            "max_retries": 1,
            "validation_levels": ["fast_path", "standard", "deep"],
        },
        "quality_thresholds": {
            "high": QUALITY_HIGH_THRESHOLD,
            "medium": QUALITY_MEDIUM_THRESHOLD,
        },
        "performance_targets": {
            "average_latency_ms": 250,
            "fast_path_latency_ms": 150,
        },
    }


@router.get("/stats")
async def get_stats():
    """
    Get runtime statistics (placeholder for future implementation).

    Returns:
        Runtime statistics for quality agents
    """
    return {
        "message": "Statistics collection not yet implemented",
        "suggested_metrics": [
            "total_queries_processed",
            "average_quality_score",
            "route_retry_rate",
            "answer_retry_rate",
            "average_latency_ms",
            "quality_level_distribution",
        ],
    }
