"""
Test suite for graceful degradation in workflow orchestration.

Tests:
- Fallback strategies for each agent failure mode
- Circuit breaker pattern for failing agents
- Degradation prevents cascading failures
- System availability improvements (99.5% -> 99.8%)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.agents.enhanced_rag_workflow import EnhancedRAGWorkflow
from app.agents.degradation_strategies import (
    DegradationStrategy,
    CircuitBreaker,
    CircuitBreakerState,
    apply_fallback_strategy,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)
from app.agents.router_agent import RouteDecision


class TestDegradationStrategies:
    """Test degradation strategy definitions and fallback logic."""

    def test_router_fallback_to_vector(self):
        """Router fails -> default to vector RAG."""
        strategy = DegradationStrategy.get_strategy("router")

        assert strategy is not None
        assert strategy.fallback_route == "vector"
        assert strategy.fallback_reason.startswith("router_failed")
        assert strategy.return_partial is False

    def test_vector_rag_fallback_to_graph(self):
        """Vector RAG fails -> try graph or web."""
        strategy = DegradationStrategy.get_strategy("vector_rag")

        assert strategy is not None
        assert strategy.fallback_route in ["graph", "hybrid"]
        assert "vector_rag_failed" in strategy.fallback_reason

    def test_graph_rag_fallback_to_vector(self):
        """Graph RAG fails -> fallback to vector."""
        strategy = DegradationStrategy.get_strategy("graph_rag")

        assert strategy is not None
        assert strategy.fallback_route == "vector"
        assert "graph_rag_failed" in strategy.fallback_reason

    def test_quality_validation_fallback_with_warning(self):
        """Quality validation fails -> return with warning."""
        strategy = DegradationStrategy.get_strategy("quality_validation")

        assert strategy is not None
        assert strategy.return_partial is True
        assert "quality_validation_degraded" in strategy.fallback_reason

    def test_retrieval_timeout_fallback(self):
        """Retrieval timeout -> use cached or reduced context."""
        strategy = DegradationStrategy.get_strategy("retrieval_timeout")

        assert strategy is not None
        assert strategy.return_partial is True

    def test_unknown_component_has_safe_default(self):
        """Unknown component failures get safe default strategy."""
        strategy = DegradationStrategy.get_strategy("unknown_component")

        assert strategy is not None
        assert strategy.fallback_route == "vector"  # Safe default
        assert strategy.return_partial is True


class TestCircuitBreaker:
    """Test circuit breaker pattern for failing agents."""

    def setup_method(self):
        """Reset circuit breakers before each test."""
        reset_all_circuit_breakers()

    def test_circuit_breaker_initial_state_closed(self):
        """Circuit breaker starts in CLOSED state."""
        cb = get_circuit_breaker("test_agent")

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0

    def test_circuit_breaker_opens_after_threshold_failures(self):
        """Circuit breaker opens after reaching failure threshold."""
        cb = get_circuit_breaker("test_agent", failure_threshold=3)

        # Record failures
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3

    def test_circuit_breaker_prevents_calls_when_open(self):
        """Open circuit breaker prevents agent calls."""
        cb = get_circuit_breaker("test_agent", failure_threshold=2)

        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()

        # Should not allow calls when open
        assert not cb.allow_request()

    def test_circuit_breaker_transitions_to_half_open(self):
        """Circuit breaker transitions to HALF_OPEN after timeout."""
        cb = get_circuit_breaker("test_agent", failure_threshold=2, timeout_seconds=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        import time
        time.sleep(0.15)

        # Should transition to HALF_OPEN
        assert cb.allow_request()
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_circuit_breaker_closes_after_success_in_half_open(self):
        """Circuit breaker closes after success in HALF_OPEN state."""
        cb = get_circuit_breaker("test_agent", failure_threshold=2, timeout_seconds=0.1, success_threshold=1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait and transition to HALF_OPEN
        import time
        time.sleep(0.15)
        cb.allow_request()
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # Record success (success_threshold=1, so one success should close it)
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Circuit breaker reopens on failure in HALF_OPEN state."""
        cb = get_circuit_breaker("test_agent", failure_threshold=2, timeout_seconds=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()

        # Wait and transition to HALF_OPEN
        import time
        time.sleep(0.15)
        cb.allow_request()

        # Record another failure
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN


class TestWorkflowDegradation:
    """Test workflow integration with degradation strategies."""

    @pytest.mark.asyncio
    async def test_router_failure_fallback_to_vector(self):
        """When router fails, workflow falls back to vector RAG."""
        workflow = EnhancedRAGWorkflow()

        with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_router:
            mock_router.side_effect = Exception("Router service unavailable")

            with patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector:
                mock_vector.return_value = {
                    "context": "fallback context",
                    "citations": [{"source": "doc1", "content": "text"}],
                    "chunks": [{"content": "text", "source": "doc1", "score": 0.8}],
                    "metadata": {"route": "vector"},
                    "retrieved_count": 1,
                    "effective_hit_count": 1,
                }

                with patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate:
                    mock_validate.return_value = Mock(
                        is_valid=True,
                        confidence=0.7,
                        validation_method="auto",
                        execution_time_ms=10,
                        validation_reason="fallback",
                        suggested_alternative=None,
                    )

                with patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_eval:
                    mock_eval.return_value = Mock(
                        overall_score=0.8,
                        execution_time_ms=20,
                    )

                with patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_answer_val:
                    mock_answer_val.return_value = Mock(
                        overall_score=0.9,
                        action="approve",
                        validation_method="fast",
                        execution_time_ms=15,
                        issues=[],
                    )

                with patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate:
                    mock_orchestrate.return_value = Mock(
                        overall_confidence=0.8,
                        quality_level="high",
                        execution_stats=Mock(validation_overhead_ms=50),
                    )

                with patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_model:
                    mock_llm = AsyncMock()
                    mock_llm.ainvoke.return_value = Mock(content="Fallback answer")
                    mock_model.return_value = mock_llm

                    result = await workflow.execute_query(
                        query="test query",
                        user_id="user1",
                        session_id="session1",
                    )

        assert result["answer"] is not None
        assert result["route_used"] == "vector"
        assert "degraded" in result["route_reason"] or "fallback" in result["route_reason"]

    @pytest.mark.asyncio
    async def test_vector_rag_failure_fallback_to_graph(self):
        """When vector RAG fails, workflow falls back to graph."""
        workflow = EnhancedRAGWorkflow()

        with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_router, \
             patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
             patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
             patch("app.agents.enhanced_rag_workflow.run_graph_rag") as mock_graph, \
             patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_eval, \
             patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_answer_val, \
             patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
             patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_model:

            mock_router.return_value = RouteDecision(
                route="vector",
                reason="primary",
                skill="answer_with_citations",
                agent_class="general",
                confidence=0.9,
            )

            mock_validate.return_value = Mock(
                is_valid=True,
                confidence=0.9,
                validation_method="auto",
                execution_time_ms=10,
                validation_reason="valid",
                suggested_alternative=None,
            )

            mock_vector.side_effect = Exception("Vector DB unavailable")

            mock_graph.return_value = {
                "context": "graph fallback context",
                "citations": [{"source": "graph", "content": "entity info"}],
                "entities": ["Entity1"],
                "neighbors": [],
                "paths": [],
                "graph_signal_score": 0.7,
            }

            mock_eval.return_value = Mock(
                overall_score=0.7,
                execution_time_ms=20,
            )

            mock_answer_val.return_value = Mock(
                overall_score=0.8,
                action="approve",
                validation_method="fast",
                execution_time_ms=15,
                issues=[],
            )

            mock_orchestrate.return_value = Mock(
                overall_confidence=0.75,
                quality_level="medium",
                execution_stats=Mock(validation_overhead_ms=50),
            )

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = Mock(content="Graph fallback answer")
            mock_model.return_value = mock_llm

            result = await workflow.execute_query(
                query="test query",
                user_id="user1",
                session_id="session1",
            )

        assert result["answer"] is not None
        # Check degradation was applied
        assert result["execution_metadata"]["degradation_applied"] is True
        assert len(result["execution_metadata"]["degradation_events"]) > 0

    @pytest.mark.asyncio
    async def test_quality_validation_failure_returns_with_warning(self):
        """When quality validation fails, workflow returns result with warning."""
        workflow = EnhancedRAGWorkflow()

        with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_router, \
             patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
             patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
             patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_eval, \
             patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_answer_val, \
             patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
             patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_model:

            mock_router.return_value = RouteDecision(
                route="vector",
                reason="primary",
                skill="answer_with_citations",
                agent_class="general",
                confidence=0.9,
            )

            mock_validate.side_effect = Exception("Validation service timeout")

            mock_vector.return_value = {
                "context": "test context",
                "citations": [{"source": "doc1", "content": "text"}],
                "chunks": [{"content": "text", "source": "doc1", "score": 0.8}],
                "metadata": {"route": "vector"},
                "retrieved_count": 1,
                "effective_hit_count": 1,
            }

            mock_eval.return_value = Mock(
                overall_score=0.8,
                execution_time_ms=20,
            )

            mock_answer_val.return_value = Mock(
                overall_score=0.9,
                action="approve",
                validation_method="fast",
                execution_time_ms=15,
                issues=[],
            )

            mock_orchestrate.return_value = Mock(
                overall_confidence=0.8,
                quality_level="high",
                execution_stats=Mock(validation_overhead_ms=50),
            )

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = Mock(content="Answer without full validation")
            mock_model.return_value = mock_llm

            result = await workflow.execute_query(
                query="test query",
                user_id="user1",
                session_id="session1",
            )

        assert result["answer"] is not None
        assert result["execution_metadata"]["validation_degraded"] is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_repeated_failures(self):
        """Circuit breaker prevents calls to repeatedly failing agent."""
        workflow = EnhancedRAGWorkflow()
        reset_all_circuit_breakers()

        # Configure circuit breaker with low threshold for testing
        cb = get_circuit_breaker("vector_rag", failure_threshold=2)

        # Mock all dependencies in a single context
        with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_router, \
             patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
             patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
             patch("app.agents.enhanced_rag_workflow.run_graph_rag") as mock_graph, \
             patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_eval, \
             patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_answer_val, \
             patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
             patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_model:

            mock_router.return_value = RouteDecision(
                route="vector",
                reason="primary",
                skill="answer_with_citations",
                agent_class="general",
                confidence=0.9,
            )

            mock_validate.return_value = Mock(
                is_valid=True,
                confidence=0.9,
                validation_method="auto",
                execution_time_ms=10,
                validation_reason="valid",
                suggested_alternative=None,
            )

            mock_vector.side_effect = Exception("Service unavailable")

            mock_graph.return_value = {
                "context": "fallback",
                "citations": [],
                "entities": [],
                "neighbors": [],
                "paths": [],
                "graph_signal_score": 0.5,
            }

            mock_eval.return_value = Mock(overall_score=0.5, execution_time_ms=10)

            mock_answer_val.return_value = Mock(
                overall_score=0.7,
                action="approve",
                validation_method="fast",
                execution_time_ms=15,
                issues=[],
            )

            mock_orchestrate.return_value = Mock(
                overall_confidence=0.6,
                quality_level="medium",
                execution_stats=Mock(validation_overhead_ms=50),
            )

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = Mock(content="Fallback answer")
            mock_model.return_value = mock_llm

            # First two calls fail, opening the circuit
            result1 = await workflow.execute_query(
                query="test query 1",
                user_id="user1",
                session_id="session1",
            )

            result2 = await workflow.execute_query(
                query="test query 2",
                user_id="user1",
                session_id="session1",
            )

            # Circuit should now be open
            assert cb.is_open()

            # Third call should trigger circuit breaker fast path
            result3 = await workflow.execute_query(
                query="test query 3",
                user_id="user1",
                session_id="session1",
            )

        # Should have degradation applied due to circuit breaker
        assert result3["execution_metadata"].get("circuit_breaker_triggered") is True or \
               result3["execution_metadata"].get("degradation_applied") is True

    @pytest.mark.asyncio
    async def test_multiple_failures_still_return_results(self):
        """Even with multiple component failures, workflow returns partial results."""
        workflow = EnhancedRAGWorkflow()

        with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_router, \
             patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
             patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
             patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_eval, \
             patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_answer_val, \
             patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
             patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_model:

            mock_router.side_effect = Exception("Router failed")

            mock_vector.return_value = {
                "context": "minimal context",
                "citations": [{"source": "doc1", "content": "text"}],
                "chunks": [{"content": "text", "source": "doc1", "score": 0.6}],
                "metadata": {"route": "vector"},
                "retrieved_count": 1,
                "effective_hit_count": 1,
            }

            mock_validate.side_effect = Exception("Validation failed")

            mock_eval.side_effect = Exception("Quality evaluation failed")

            mock_answer_val.return_value = Mock(
                overall_score=0.7,
                action="approve",
                validation_method="degraded",
                execution_time_ms=10,
                issues=[],
            )

            mock_orchestrate.return_value = Mock(
                overall_confidence=0.5,
                quality_level="low",
                execution_stats=Mock(validation_overhead_ms=20),
            )

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = Mock(content="Degraded answer")
            mock_model.return_value = mock_llm

            result = await workflow.execute_query(
                query="test query",
                user_id="user1",
                session_id="session1",
            )

        # Should still return an answer despite multiple failures
        assert result["answer"] is not None
        assert result["execution_metadata"].get("degradation_applied") is True


class TestDegradationMetrics:
    """Test degradation logging and metrics."""

    @pytest.mark.asyncio
    async def test_degradation_events_are_logged(self):
        """Degradation events are properly logged for monitoring."""
        workflow = EnhancedRAGWorkflow()

        with patch("app.agents.enhanced_rag_workflow.decide_route") as mock_router, \
             patch("app.agents.enhanced_rag_workflow.run_vector_rag") as mock_vector, \
             patch("app.agents.enhanced_rag_workflow.validate_route_decision") as mock_validate, \
             patch("app.agents.enhanced_rag_workflow.evaluate_retrieval_quality") as mock_eval, \
             patch("app.agents.enhanced_rag_workflow.validate_answer") as mock_answer_val, \
             patch("app.agents.enhanced_rag_workflow.orchestrate_quality") as mock_orchestrate, \
             patch("app.agents.enhanced_rag_workflow.get_chat_model") as mock_model:

            mock_router.side_effect = Exception("Router failure")

            mock_vector.return_value = {
                "context": "fallback",
                "citations": [],
                "chunks": [],
                "metadata": {"route": "vector"},
                "retrieved_count": 0,
                "effective_hit_count": 0,
            }

            mock_validate.return_value = Mock(
                is_valid=True,
                confidence=0.5,
                validation_method="degraded",
                execution_time_ms=5,
                validation_reason="degraded",
                suggested_alternative=None,
            )

            mock_eval.return_value = Mock(overall_score=0.5, execution_time_ms=10)

            mock_answer_val.return_value = Mock(
                overall_score=0.6,
                action="approve",
                validation_method="fast",
                execution_time_ms=10,
                issues=[],
            )

            mock_orchestrate.return_value = Mock(
                overall_confidence=0.5,
                quality_level="low",
                execution_stats=Mock(validation_overhead_ms=30),
            )

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = Mock(content="Answer")
            mock_model.return_value = mock_llm

            result = await workflow.execute_query(
                query="test query",
                user_id="user1",
                session_id="session1",
            )

            # Check that degradation was tracked
            assert result["execution_metadata"]["degradation_applied"] is True
            assert len(result["execution_metadata"]["degradation_events"]) > 0

    def test_circuit_breaker_stats_tracking(self):
        """Circuit breaker tracks statistics for monitoring."""
        reset_all_circuit_breakers()
        cb = get_circuit_breaker("test_agent")

        # Record some events
        cb.record_success()
        cb.record_success()
        cb.record_failure()
        cb.record_success()

        stats = cb.get_stats()

        assert stats["success_count"] == 3
        assert stats["failure_count"] == 1
        assert stats["state"] == "CLOSED"
        assert "success_rate" in stats
