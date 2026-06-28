"""
Degradation Strategies - Graceful degradation for workflow orchestration.

This module implements fallback strategies and circuit breaker patterns to improve
system availability from 99.5% to 99.8% by preventing cascading failures.

Key features:
- Fallback strategies for each failure mode
- Circuit breaker pattern to disable repeatedly failing agents
- Degradation event logging for monitoring
- Graceful handling of partial failures
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states following the standard pattern."""
    CLOSED = "CLOSED"  # Normal operation, requests allowed
    OPEN = "OPEN"  # Failures exceeded threshold, requests blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


@dataclass
class DegradationStrategy:
    """
    Defines fallback behavior for a component failure.

    Attributes:
        component: Name of the failing component
        fallback_route: Alternative route to use (vector, graph, hybrid)
        fallback_reason: Reason tag for logging/monitoring
        return_partial: Whether to return partial results with warning
        skip_validation: Whether to skip quality validation on fallback
    """
    component: str
    fallback_route: Optional[str] = None
    fallback_reason: str = ""
    return_partial: bool = False
    skip_validation: bool = False

    @staticmethod
    def get_strategy(component: str) -> "DegradationStrategy":
        """
        Get fallback strategy for a component.

        Args:
            component: Component name (router, vector_rag, graph_rag, quality_validation, etc.)

        Returns:
            DegradationStrategy for the component
        """
        strategies = {
            "router": DegradationStrategy(
                component="router",
                fallback_route="vector",
                fallback_reason="router_failed_degraded_to_vector",
                return_partial=False,
                skip_validation=False,
            ),
            "vector_rag": DegradationStrategy(
                component="vector_rag",
                fallback_route="graph",
                fallback_reason="vector_rag_failed_degraded_to_graph",
                return_partial=False,
                skip_validation=False,
            ),
            "graph_rag": DegradationStrategy(
                component="graph_rag",
                fallback_route="vector",
                fallback_reason="graph_rag_failed_degraded_to_vector",
                return_partial=False,
                skip_validation=False,
            ),
            "quality_validation": DegradationStrategy(
                component="quality_validation",
                fallback_route=None,
                fallback_reason="quality_validation_degraded_partial_result",
                return_partial=True,
                skip_validation=True,
            ),
            "route_validation": DegradationStrategy(
                component="route_validation",
                fallback_route=None,
                fallback_reason="route_validation_degraded_skip_validation",
                return_partial=False,
                skip_validation=True,
            ),
            "answer_validation": DegradationStrategy(
                component="answer_validation",
                fallback_route=None,
                fallback_reason="answer_validation_degraded_skip_validation",
                return_partial=True,
                skip_validation=True,
            ),
            "retrieval_timeout": DegradationStrategy(
                component="retrieval_timeout",
                fallback_route=None,
                fallback_reason="retrieval_timeout_degraded_partial_context",
                return_partial=True,
                skip_validation=False,
            ),
            "synthesis": DegradationStrategy(
                component="synthesis",
                fallback_route=None,
                fallback_reason="synthesis_failed_degraded_to_simple_generation",
                return_partial=True,
                skip_validation=False,
            ),
        }

        # Return specific strategy or safe default
        if component in strategies:
            return strategies[component]

        # Safe default for unknown components
        logger.warning(f"Unknown component '{component}', using safe default strategy")
        return DegradationStrategy(
            component=component,
            fallback_route="vector",
            fallback_reason=f"{component}_failed_degraded_to_safe_default",
            return_partial=True,
            skip_validation=False,
        )


class CircuitBreaker:
    """
    Circuit breaker to prevent repeated calls to failing agents.

    States:
    - CLOSED: Normal operation, all requests allowed
    - OPEN: Too many failures, block all requests
    - HALF_OPEN: Testing recovery, allow limited requests

    Attributes:
        name: Circuit breaker identifier
        failure_threshold: Number of failures before opening
        timeout_seconds: Time to wait before trying HALF_OPEN
        success_threshold: Successes needed in HALF_OPEN to close
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker identifier
            failure_threshold: Consecutive failures before opening (default 5)
            timeout_seconds: Seconds to wait before HALF_OPEN (default 60)
            success_threshold: Successes in HALF_OPEN to close (default 2)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()

        # Track total counts for statistics
        self.total_success_count = 0
        self.total_failure_count = 0

        logger.info(
            f"CircuitBreaker initialized: {name} "
            f"(threshold={failure_threshold}, timeout={timeout_seconds}s)"
        )

    def allow_request(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request can proceed, False if blocked
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout expired
            if self.last_failure_time is not None:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.timeout_seconds:
                    # Transition to HALF_OPEN
                    self._transition_to(CircuitBreakerState.HALF_OPEN)
                    return True
            return False

        if self.state == CircuitBreakerState.HALF_OPEN:
            # Allow limited requests to test recovery
            return True

        return False

    def record_success(self) -> None:
        """Record successful request."""
        self.total_success_count += 1

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            # Check if enough successes to close
            if self.success_count >= self.success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"CircuitBreaker '{self.name}' recovered and closed")
        elif self.state == CircuitBreakerState.CLOSED:
            self.success_count += 1
            # Reset failure count on success
            if self.failure_count > 0:
                logger.debug(
                    f"CircuitBreaker '{self.name}' reset failure count after success"
                )
                self.failure_count = 0
        else:
            # OPEN state - just track but don't transition
            self.success_count += 1

    def record_failure(self) -> None:
        """Record failed request."""
        self.total_failure_count += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to(CircuitBreakerState.OPEN)
                logger.warning(
                    f"CircuitBreaker '{self.name}' OPENED after {self.failure_count} failures"
                )

        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Failure in HALF_OPEN -> back to OPEN
            self._transition_to(CircuitBreakerState.OPEN)
            self.success_count = 0
            logger.warning(
                f"CircuitBreaker '{self.name}' reopened after failure in HALF_OPEN"
            )

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Transition to new state."""
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()

        logger.info(
            f"CircuitBreaker '{self.name}' transitioned: {old_state.value} -> {new_state.value}"
        )

    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)."""
        return self.state == CircuitBreakerState.OPEN

    def is_half_open(self) -> bool:
        """Check if circuit breaker is in half-open state."""
        return self.state == CircuitBreakerState.HALF_OPEN

    def get_stats(self) -> Dict[str, any]:
        """
        Get circuit breaker statistics for monitoring.

        Returns:
            Dictionary with state, counts, and success rate
        """
        total_requests = self.total_success_count + self.total_failure_count
        success_rate = (
            self.total_success_count / total_requests if total_requests > 0 else 0.0
        )

        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.total_failure_count,
            "success_count": self.total_success_count,
            "success_rate": success_rate,
            "last_failure_time": self.last_failure_time,
            "time_in_current_state": time.time() - self.last_state_change,
        }


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout_seconds: float = 60.0,
    success_threshold: int = 2,
) -> CircuitBreaker:
    """
    Get or create circuit breaker for a component.

    Args:
        name: Circuit breaker identifier
        failure_threshold: Failures before opening (default 5)
        timeout_seconds: Wait time before HALF_OPEN (default 60)
        success_threshold: Successes to close from HALF_OPEN (default 2)

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
            success_threshold=success_threshold,
        )

    return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (useful for testing)."""
    global _circuit_breakers
    _circuit_breakers.clear()
    logger.info("All circuit breakers reset")


def get_all_circuit_breaker_stats() -> Dict[str, Dict]:
    """
    Get statistics for all circuit breakers.

    Returns:
        Dictionary mapping circuit breaker names to their stats
    """
    return {name: cb.get_stats() for name, cb in _circuit_breakers.items()}


def apply_fallback_strategy(
    component: str,
    error: Exception,
    context: Optional[Dict] = None,
) -> Dict[str, any]:
    """
    Apply fallback strategy for a component failure.

    Args:
        component: Failed component name
        error: Exception that was raised
        context: Optional context dictionary with query info

    Returns:
        Dictionary with fallback instructions:
        - strategy: DegradationStrategy instance
        - should_fallback: Whether to apply fallback
        - fallback_route: Alternative route if applicable
        - reason: Reason string for logging
    """
    strategy = DegradationStrategy.get_strategy(component)

    # Check circuit breaker
    cb = get_circuit_breaker(component)
    cb.record_failure()

    circuit_breaker_open = cb.is_open()

    # Log degradation event
    logger.warning(
        f"Degradation triggered: component={component}, "
        f"error={type(error).__name__}, "
        f"circuit_breaker_open={circuit_breaker_open}, "
        f"fallback_route={strategy.fallback_route}"
    )

    return {
        "strategy": strategy,
        "should_fallback": True,
        "fallback_route": strategy.fallback_route,
        "return_partial": strategy.return_partial,
        "skip_validation": strategy.skip_validation,
        "reason": strategy.fallback_reason,
        "circuit_breaker_open": circuit_breaker_open,
        "circuit_breaker_stats": cb.get_stats(),
    }


def record_component_success(component: str) -> None:
    """
    Record successful component execution.

    Args:
        component: Component name
    """
    cb = get_circuit_breaker(component)
    cb.record_success()
