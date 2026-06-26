"""
Logging Standards for Quality Assurance Agents (P3-13).

This module defines consistent logging practices across all quality agents.
"""

import logging
from typing import Any, Dict

# Standard log levels for different scenarios
# DEBUG: Detailed information for diagnosing problems
# INFO: Confirmation that things are working as expected
# WARNING: Something unexpected happened, but the system continues
# ERROR: A serious problem that prevented a function from completing
# CRITICAL: A very serious error that may prevent the system from continuing


class QualityAgentLogger:
    """
    Standardized logger wrapper for quality agents.

    Provides consistent logging patterns and levels across all agents.
    """

    def __init__(self, name: str):
        """Initialize logger with agent name."""
        self.logger = logging.getLogger(name)

    # Performance logging
    def log_performance(self, operation: str, duration_ms: int, threshold_ms: int = 1000):
        """Log performance with appropriate level based on threshold."""
        if duration_ms > threshold_ms * 2:
            self.logger.warning(
                f"⚠️ SLOW: {operation} took {duration_ms}ms (threshold: {threshold_ms}ms)"
            )
        elif duration_ms > threshold_ms:
            self.logger.info(
                f"⏱ {operation} took {duration_ms}ms (near threshold)"
            )
        else:
            self.logger.debug(
                f"✓ {operation} completed in {duration_ms}ms"
            )

    # Validation logging
    def log_validation_start(self, agent: str, query: str):
        """Log validation start."""
        self.logger.debug(f"Starting {agent} validation for: {query[:50]}...")

    def log_validation_success(self, agent: str, score: float, method: str):
        """Log successful validation."""
        self.logger.info(
            f"✓ {agent} validation: score={score:.3f}, method={method}"
        )

    def log_validation_warning(self, agent: str, issue: str, score: float):
        """Log validation warning."""
        self.logger.warning(
            f"⚠️ {agent} validation issue: {issue} (score={score:.3f})"
        )

    def log_validation_error(self, agent: str, error: Exception):
        """Log validation error with traceback."""
        self.logger.error(
            f"❌ {agent} validation failed: {error}",
            exc_info=True
        )

    # Cache logging
    def log_cache_hit(self, cache_name: str, key: str):
        """Log cache hit."""
        self.logger.debug(f"✓ Cache hit: {cache_name}:{key[:16]}...")

    def log_cache_miss(self, cache_name: str, key: str):
        """Log cache miss."""
        self.logger.debug(f"⊗ Cache miss: {cache_name}:{key[:16]}...")

    # Retry logging
    def log_retry_attempt(self, operation: str, attempt: int, max_attempts: int, reason: str):
        """Log retry attempt."""
        self.logger.info(
            f"🔄 Retry {attempt}/{max_attempts} for {operation}: {reason}"
        )

    def log_retry_exhausted(self, operation: str, max_attempts: int):
        """Log when retries are exhausted."""
        self.logger.warning(
            f"⚠️ Max retries ({max_attempts}) exhausted for {operation}"
        )

    # Model loading
    def log_model_loading(self, model_name: str):
        """Log model loading."""
        self.logger.info(f"📦 Loading model: {model_name}")

    def log_model_loaded(self, model_name: str, duration_ms: int):
        """Log successful model load."""
        self.logger.info(f"✓ Model loaded: {model_name} ({duration_ms}ms)")

    def log_model_error(self, model_name: str, error: Exception):
        """Log model loading error."""
        self.logger.error(
            f"❌ Failed to load model {model_name}: {error}",
            exc_info=True
        )

    # Cleanup logging
    def log_cleanup(self, resource: str, count: int):
        """Log cleanup operation."""
        if count > 0:
            self.logger.info(f"🧹 Cleaned up {count} {resource}")
        else:
            self.logger.debug(f"No {resource} to clean up")

    # Stats logging
    def log_stats(self, component: str, stats: Dict[str, Any]):
        """Log component statistics."""
        stats_str = ", ".join(f"{k}={v}" for k, v in stats.items())
        self.logger.info(f"📊 {component} stats: {stats_str}")


# Standard logging patterns by scenario
LOGGING_PATTERNS = {
    "validation_start": "DEBUG",
    "validation_success": "INFO",
    "validation_warning": "WARNING",
    "validation_error": "ERROR",
    "performance_slow": "WARNING",
    "performance_normal": "INFO",
    "performance_fast": "DEBUG",
    "cache_hit": "DEBUG",
    "cache_miss": "DEBUG",
    "retry_attempt": "INFO",
    "retry_exhausted": "WARNING",
    "model_loading": "INFO",
    "model_loaded": "INFO",
    "model_error": "ERROR",
    "cleanup": "INFO",
    "stats": "INFO",
    "timeout": "WARNING",
    "fallback": "WARNING",
}


# Usage example:
"""
from app.agents.quality_logging import QualityAgentLogger

logger = QualityAgentLogger(__name__)

# Performance logging
start = time.time()
result = do_work()
duration = int((time.time() - start) * 1000)
logger.log_performance("validation", duration, threshold_ms=200)

# Validation logging
logger.log_validation_start("RouteValidator", query)
try:
    score = validate(...)
    logger.log_validation_success("RouteValidator", score, "rule_fast")
except Exception as e:
    logger.log_validation_error("RouteValidator", e)
"""
