"""
Integration tests for Enhanced RAG Workflow.

Tests the complete quality-enhanced RAG pipeline including:
- Route validation with retry
- Retrieval quality assessment
- Answer validation with regeneration
- Quality orchestration
- Context tracking
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from app.agents.enhanced_rag_workflow import EnhancedRAGWorkflow
from app.agents.router_agent import RouteDecision
from app.agents.quality_models import (
    RouteValidationResult,
    RetrievalQualityResult,
    RetrievalQualityMetrics,
    AnswerValidationResult,
    AnswerValidationDetails,
    QualityReport,
    QualityBreakdown,
    ExecutionStats,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def workflow():
    """Create EnhancedRAGWorkflow instance for testing."""
    return EnhancedRAGWorkflow(
        max_route_retries=1,
        max_answer_retries=1,
        enable_context_tracking=True,
    )


@pytest.fixture
def mock_route_decision():
    """Mock route decision."""
    return RouteDecision(
        route="vector",
        reason="test_routing",
        skill="answer_with_citations",
        agent_class="general",
        confidence=0.85,
    )


@pytest.fixture
def mock_route_validation_success():
    """Mock successful route validation."""
    return RouteValidationResult(
        is_valid=True,
        confidence=0.90,
        validation_method="rule_fast",
        validation_reason="high_confidence_fast_pass",
        execution_time_ms=5,
        suggested_alternative=None,
        warnings=[],
    )


@pytest.fixture
def mock_route_validation_failure():
    """Mock failed route validation with alternative."""
    return RouteValidationResult(
        is_valid=False,
        confidence=0.45,
        validation_method="llm",
        validation_reason="route_mismatch",
        execution_time_ms=350,
        suggested_alternative={
            "route": "graph",
            "skill": "compare_entities",
            "reason": "query_requires_graph"
        },
        warnings=["low_confidence"],
    )


@pytest.fixture
def mock_retrieval_quality():
    """Mock retrieval quality result."""
    return RetrievalQualityResult(
        overall_quality=0.82,
        metrics=RetrievalQualityMetrics(
            coverage_score=0.85,
            relevance_score=0.88,
            diversity_score=0.75,
            completeness_score=0.80,
        ),
        execution_time_ms=45,
        issues=[],
        suggestions=["Consider expanding search terms"],
    )


@pytest.fixture
def mock_answer_validation_approve():
    """Mock answer validation with approve action."""
    return AnswerValidationResult(
        is_valid=True,
        overall_score=0.88,
        validation_details=AnswerValidationDetails(
            factual_consistency=0.92,
            hallucination_risk=0.05,
            citation_completeness=0.85,
            answer_quality=0.87,
            safety_score=1.0,
        ),
        issues=[],
        action="approve",
        execution_time_ms=120,
        validation_method="standard",
    )


@pytest.fixture
def mock_answer_validation_regenerate():
    """Mock answer validation with regenerate action."""
    return AnswerValidationResult(
        is_valid=False,
        overall_score=0.52,
        validation_details=AnswerValidationDetails(
            factual_consistency=0.60,
            hallucination_risk=0.35,
            citation_completeness=0.45,
            answer_quality=0.50,
            safety_score=1.0,
        ),
        issues=[],
        action="regenerate",
        execution_time_ms=180,
        validation_method="deep",
    )


@pytest.fixture
def mock_quality_report():
    """Mock quality report."""
    return QualityReport(
        overall_confidence=0.85,
        quality_level="high",
        quality_label="高质量",
        user_prompt=None,
        breakdown=QualityBreakdown(
            route_decision={"score": 0.90, "status": "✓ 通过"},
            retrieval={"score": 0.82, "status": "✓ 良好"},
            answer_factuality={"score": 0.92, "status": "✓ 可信"},
            citations={"score": 0.85, "status": "✓ 完整"},
        ),
        issues=[],
        suggestions=["Consider expanding search terms"],
        execution_stats=ExecutionStats(
            total_time_ms=1500,
            validation_overhead_ms=170,
            retry_count=0,
            route_retry=0,
            answer_retry=0,
        ),
    )


@pytest.fixture
def mock_vector_rag_result():
    """Mock vector RAG result."""
    return {
        "context": "Test context from vector RAG",
        "citations": [
            {
                "source": "doc1.txt",
                "content": "Test content 1",
                "metadata": {"hybrid_score": 0.85},
            },
            {
                "source": "doc2.txt",
                "content": "Test content 2",
                "metadata": {"hybrid_score": 0.75},
            },
        ],
        "retrieved_count": 5,
    }


# ============================================================================
# Test: Basic Workflow Execution
# ============================================================================


@pytest.mark.asyncio
async def test_execute_query_success_fast_path(
    workflow,
    mock_route_decision,
    mock_route_validation_success,
    mock_retrieval_quality,
    mock_answer_validation_approve,
    mock_quality_report,
    mock_vector_rag_result,
):
    """Test successful query execution through fast path (no retries)."""

    with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_decide_route, \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate_route, \
         patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_run_vector, \
         patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_assess_retrieval, \
         patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_validate_answer, \
         patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints") as mock_get_hints, \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context") as mock_update_context:

        # Setup mocks
        mock_decide_route.return_value = mock_route_decision
        mock_validate_route.return_value = mock_route_validation_success
        mock_run_vector.return_value = mock_vector_rag_result
        mock_assess_retrieval.return_value = mock_retrieval_quality
        mock_validate_answer.return_value = mock_answer_validation_approve
        mock_orchestrate.return_value = mock_quality_report
        mock_get_hints.return_value = None
        mock_update_context.return_value = None

        # Mock LLM answer generation
        mock_llm_response = Mock()
        mock_llm_response.content = "This is a test answer based on the context."

        with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_get_model.return_value = mock_model

            # Execute query
            result = await workflow.execute_query(
                query="What is test?",
                user_id="test_user",
                session_id="test_session",
                allowed_sources=None,
                retrieval_strategy=None,
                agent_class_hint=None,
            )

        # Assertions
        assert result["answer"] == "This is a test answer based on the context."
        assert len(result["citations"]) == 2
        assert result["route_used"] == "vector"
        assert result["quality_report"].quality_level == "high"
        assert result["execution_metadata"]["route_retry"] == 0
        assert result["execution_metadata"]["answer_retry"] == 0

        # Verify no retries occurred
        mock_decide_route.assert_called_once()
        assert mock_validate_answer.call_count == 1


# ============================================================================
# Test: Route Retry Logic
# ============================================================================


@pytest.mark.asyncio
async def test_route_validation_retry(
    workflow,
    mock_route_decision,
    mock_route_validation_failure,
    mock_route_validation_success,
    mock_retrieval_quality,
    mock_answer_validation_approve,
    mock_quality_report,
    mock_vector_rag_result,
):
    """Test route validation retry when validation fails with alternative."""

    with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_decide_route, \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate_route, \
         patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_run_vector, \
         patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_assess_retrieval, \
         patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_validate_answer, \
         patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints") as mock_get_hints, \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context") as mock_update_context:

        # Setup mocks - first validation fails, second succeeds
        mock_decide_route.return_value = mock_route_decision
        mock_validate_route.side_effect = [
            mock_route_validation_failure,  # First attempt fails
            mock_route_validation_success,  # Retry succeeds
        ]
        mock_run_vector.return_value = mock_vector_rag_result
        mock_assess_retrieval.return_value = mock_retrieval_quality
        mock_validate_answer.return_value = mock_answer_validation_approve
        mock_orchestrate.return_value = mock_quality_report
        mock_get_hints.return_value = None
        mock_update_context.return_value = None

        # Mock LLM
        mock_llm_response = Mock()
        mock_llm_response.content = "Test answer"

        with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_get_model.return_value = mock_model

            result = await workflow.execute_query(
                query="Test query",
                user_id="user1",
                session_id="session1",
            )

        # Assertions
        assert result["execution_metadata"]["route_retry"] == 1
        assert mock_validate_route.call_count == 2


# ============================================================================
# Test: Answer Regeneration Logic
# ============================================================================


@pytest.mark.asyncio
async def test_answer_regeneration(
    workflow,
    mock_route_decision,
    mock_route_validation_success,
    mock_retrieval_quality,
    mock_answer_validation_regenerate,
    mock_answer_validation_approve,
    mock_quality_report,
    mock_vector_rag_result,
):
    """Test answer regeneration when validation suggests regeneration."""

    with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_decide_route, \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate_route, \
         patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_run_vector, \
         patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_assess_retrieval, \
         patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_validate_answer, \
         patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints") as mock_get_hints, \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context") as mock_update_context:

        # Setup mocks - first answer validation triggers regeneration
        mock_decide_route.return_value = mock_route_decision
        mock_validate_route.return_value = mock_route_validation_success
        mock_run_vector.return_value = mock_vector_rag_result
        mock_assess_retrieval.return_value = mock_retrieval_quality
        mock_validate_answer.side_effect = [
            mock_answer_validation_regenerate,  # First answer needs regeneration
            mock_answer_validation_approve,     # Second answer is approved
        ]
        mock_orchestrate.return_value = mock_quality_report
        mock_get_hints.return_value = None
        mock_update_context.return_value = None

        # Mock LLM - two different answers
        mock_llm_response_1 = Mock()
        mock_llm_response_1.content = "First low-quality answer"
        mock_llm_response_2 = Mock()
        mock_llm_response_2.content = "Improved second answer with better citations"

        with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.ainvoke = AsyncMock(side_effect=[
                mock_llm_response_1,
                mock_llm_response_2,
            ])
            mock_get_model.return_value = mock_model

            result = await workflow.execute_query(
                query="Test query",
                user_id="user1",
                session_id="session1",
            )

        # Assertions
        assert result["answer"] == "Improved second answer with better citations"
        assert result["execution_metadata"]["answer_retry"] == 1
        assert mock_validate_answer.call_count == 2
        assert mock_model.ainvoke.call_count == 2


# ============================================================================
# Test: Different Route Types
# ============================================================================


@pytest.mark.asyncio
async def test_graph_route_execution(workflow):
    """Test execution with graph route."""

    mock_graph_result = {
        "context": "Graph context",
        "citations": [{"source": "graph", "content": "entity data"}],
        "entities": [{"description": "Test entity"}],
    }

    with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_decide, \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
         patch("app.agents.enhanced_rag_workflow.run_graph_rag") as mock_graph, \
         patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_assess, \
         patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_validate_ans, \
         patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orch, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints") as mock_hints, \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context") as mock_update:

        # Setup for graph route
        graph_decision = RouteDecision(
            route="graph",
            reason="graph_query",
            skill="compare_entities",
            agent_class="general",
            confidence=0.80,
        )

        mock_decide.return_value = graph_decision
        mock_validate.return_value = RouteValidationResult(
            is_valid=True,
            confidence=0.85,
            validation_method="rule_fast",
            validation_reason="graph_route",
            execution_time_ms=10,
        )
        mock_graph.return_value = mock_graph_result
        mock_assess.return_value = RetrievalQualityResult(
            overall_quality=0.80,
            metrics=RetrievalQualityMetrics(
                coverage_score=0.80,
                relevance_score=0.85,
                diversity_score=0.75,
                completeness_score=0.80,
            ),
            execution_time_ms=40,
        )
        mock_validate_ans.return_value = AnswerValidationResult(
            is_valid=True,
            overall_score=0.85,
            validation_details=AnswerValidationDetails(
                factual_consistency=0.90,
                hallucination_risk=0.08,
                citation_completeness=0.80,
                answer_quality=0.85,
                safety_score=1.0,
            ),
            issues=[],
            action="approve",
            execution_time_ms=100,
            validation_method="standard",
        )
        mock_orch.return_value = QualityReport(
            overall_confidence=0.82,
            quality_level="high",
            quality_label="高质量",
            user_prompt=None,
            breakdown=QualityBreakdown(
                route_decision={"score": 0.85, "status": "✓ 通过"},
                retrieval={"score": 0.80, "status": "✓ 良好"},
                answer_factuality={"score": 0.90, "status": "✓ 可信"},
                citations={"score": 0.80, "status": "✓ 完整"},
            ),
            issues=[],
            suggestions=[],
            execution_stats=ExecutionStats(
                total_time_ms=1200,
                validation_overhead_ms=150,
                retry_count=0,
            ),
        )
        mock_hints.return_value = None
        mock_update.return_value = None

        # Mock LLM
        mock_llm_response = Mock()
        mock_llm_response.content = "Graph-based answer"

        with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_get_model.return_value = mock_model

            result = await workflow.execute_query(
                query="Compare entities",
                user_id="user1",
                session_id="session1",
            )

        # Assertions
        assert result["route_used"] == "graph"
        assert result["skill_used"] == "compare_entities"
        mock_graph.assert_called_once()


# ============================================================================
# Test: Context Tracking Integration
# ============================================================================


@pytest.mark.asyncio
async def test_context_tracking_enabled(workflow, mock_vector_rag_result):
    """Test that context tracking is properly integrated."""

    with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_decide, \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
         patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
         patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_assess, \
         patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_validate_ans, \
         patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orch, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints") as mock_get_hints, \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context") as mock_update_context, \
         patch("app.agents.enhanced_rag_workflow.get_chat_model"):

        # Setup basic mocks with proper return values
        mock_decide.return_value = RouteDecision(
            route="vector",
            reason="test",
            skill="answer_with_citations",
            agent_class="general",
            confidence=0.85,
        )
        mock_validate.return_value = RouteValidationResult(
            is_valid=True,
            confidence=0.90,
            validation_method="rule_fast",
            validation_reason="test",
            execution_time_ms=10,
        )
        mock_vector.return_value = mock_vector_rag_result
        mock_assess.return_value = RetrievalQualityResult(
            overall_quality=0.85,
            metrics=RetrievalQualityMetrics(
                coverage_score=0.85,
                relevance_score=0.85,
                diversity_score=0.85,
                completeness_score=0.85
            ),
            execution_time_ms=50,
        )
        mock_validate_ans.return_value = AnswerValidationResult(
            is_valid=True,
            overall_score=0.88,
            validation_details=AnswerValidationDetails(
                factual_consistency=0.9,
                hallucination_risk=0.05,
                citation_completeness=0.85,
                answer_quality=0.88,
                safety_score=1.0
            ),
            issues=[],
            action="approve",
            execution_time_ms=100,
            validation_method="standard",
        )
        mock_orch.return_value = QualityReport(
            overall_confidence=0.87,
            quality_level="high",
            quality_label="高质量",
            user_prompt=None,
            breakdown=QualityBreakdown(
                route_decision={"score": 0.90, "status": "✓ 通过"},
                retrieval={"score": 0.85, "status": "✓ 良好"},
                answer_factuality={"score": 0.90, "status": "✓ 可信"},
                citations={"score": 0.85, "status": "✓ 完整"},
            ),
            issues=[],
            suggestions=[],
            execution_stats=ExecutionStats(
                total_time_ms=1500,
                validation_overhead_ms=160,
                retry_count=0,
            ),
        )
        mock_get_hints.return_value = None
        mock_update_context.return_value = None

        # Mock LLM
        mock_llm_response = Mock()
        mock_llm_response.content = "Test answer"

        with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_get_model.return_value = mock_model

            await workflow.execute_query(
                query="Test query",
                user_id="user1",
                session_id="session1",
            )

        # Verify context tracking was called
        mock_get_hints.assert_called_once_with("session1", "Test query")
        mock_update_context.assert_called_once()


# ============================================================================
# Test: Performance and Latency
# ============================================================================


@pytest.mark.asyncio
async def test_execution_time_tracking(workflow, mock_vector_rag_result):
    """Test that execution time is properly tracked."""

    with patch("app.agents.enhanced_rag_workflow.decide_route"), \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
         patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
         patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_assess, \
         patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_validate_ans, \
         patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orch, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints"), \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context"), \
         patch("app.agents.enhanced_rag_workflow.get_chat_model"):

        # Setup mocks with execution times
        mock_validate.return_value = RouteValidationResult(
            is_valid=True,
            confidence=0.90,
            validation_method="rule_fast",
            validation_reason="test",
            execution_time_ms=10,
        )
        mock_vector.return_value = mock_vector_rag_result
        mock_assess.return_value = RetrievalQualityResult(
            overall_quality=0.85,
            metrics=RetrievalQualityMetrics(
                coverage_score=0.85,
                relevance_score=0.85,
                diversity_score=0.85,
                completeness_score=0.85
            ),
            execution_time_ms=50,
        )
        mock_validate_ans.return_value = AnswerValidationResult(
            is_valid=True,
            overall_score=0.88,
            validation_details=AnswerValidationDetails(
                factual_consistency=0.9,
                hallucination_risk=0.05,
                citation_completeness=0.85,
                answer_quality=0.88,
                safety_score=1.0
            ),
            issues=[],
            action="approve",
            execution_time_ms=120,
            validation_method="standard",
        )
        mock_orch.return_value = QualityReport(
            overall_confidence=0.87,
            quality_level="high",
            quality_label="高质量",
            user_prompt=None,
            breakdown=QualityBreakdown(
                route_decision={"score": 0.90, "status": "✓ 通过"},
                retrieval={"score": 0.85, "status": "✓ 良好"},
                answer_factuality={"score": 0.90, "status": "✓ 可信"},
                citations={"score": 0.85, "status": "✓ 完整"},
            ),
            issues=[],
            suggestions=[],
            execution_stats=ExecutionStats(
                total_time_ms=1500,
                validation_overhead_ms=180,  # 10 + 50 + 120
                retry_count=0,
            ),
        )

        # Mock LLM
        mock_llm_response = Mock()
        mock_llm_response.content = "Test answer"

        with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)
            mock_get_model.return_value = mock_model

            result = await workflow.execute_query(
                query="Test",
                user_id="user1",
                session_id="session1",
            )

        # Assertions
        assert "total_time_ms" in result["execution_metadata"]
        assert result["execution_metadata"]["total_time_ms"] > 0
        assert result["quality_report"].execution_stats.validation_overhead_ms == 180


# ============================================================================
# Test: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_handles_retrieval_error(workflow):
    """Test workflow handles retrieval errors gracefully."""

    with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_decide, \
         patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
         patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
         patch("app.agents.enhanced_rag_workflow.get_context_aware_routing_hints"), \
         patch("app.agents.enhanced_rag_workflow.update_conversation_context"):

        # Setup proper return values for mocks before the error
        mock_decide.return_value = RouteDecision(
            route="vector",
            reason="test",
            skill="answer_with_citations",
            agent_class="general",
            confidence=0.85,
        )
        mock_validate.return_value = RouteValidationResult(
            is_valid=True,
            confidence=0.90,
            validation_method="rule_fast",
            validation_reason="test",
            execution_time_ms=10,
        )

        # Simulate retrieval error
        mock_vector.side_effect = Exception("Retrieval failed")

        with pytest.raises(Exception, match="Retrieval failed"):
            await workflow.execute_query(
                query="Test",
                user_id="user1",
                session_id="session1",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
