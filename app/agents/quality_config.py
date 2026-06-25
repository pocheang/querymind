"""
Configuration constants for quality assurance system.
"""

from typing import Final

# ============================================================================
# Global Switches
# ============================================================================

ENABLE_QUALITY_VALIDATION: Final[bool] = True
ENABLE_CONTEXT_TRACKING: Final[bool] = True
ENABLE_VERBOSE_LOGGING: Final[bool] = False


# ============================================================================
# Route Validator Configuration
# ============================================================================

ROUTE_HIGH_CONFIDENCE_THRESHOLD: Final[float] = 0.85
ROUTE_MEDIUM_CONFIDENCE_THRESHOLD: Final[float] = 0.60
ROUTE_LOW_CONFIDENCE_THRESHOLD: Final[float] = 0.40
ROUTE_VALIDATOR_USE_CACHE: Final[bool] = True
ROUTE_VALIDATOR_CACHE_TTL: Final[int] = 3600


# ============================================================================
# Retrieval Quality Configuration
# ============================================================================

RETRIEVAL_WEIGHT_COVERAGE: Final[float] = 0.30
RETRIEVAL_WEIGHT_RELEVANCE: Final[float] = 0.40
RETRIEVAL_WEIGHT_DIVERSITY: Final[float] = 0.15
RETRIEVAL_WEIGHT_COMPLETENESS: Final[float] = 0.15
RETRIEVAL_QUALITY_GOOD_THRESHOLD: Final[float] = 0.70
RETRIEVAL_QUALITY_POOR_THRESHOLD: Final[float] = 0.50
RETRIEVAL_SAMPLE_TOP_K: Final[int] = 3


# ============================================================================
# Answer Validator Configuration
# ============================================================================

ANSWER_FAST_PATH_THRESHOLD: Final[float] = 0.80
ANSWER_STANDARD_PATH_THRESHOLD: Final[float] = 0.60
ANSWER_WEIGHT_FACTUALITY: Final[float] = 0.40
ANSWER_WEIGHT_CITATION: Final[float] = 0.25
ANSWER_WEIGHT_QUALITY: Final[float] = 0.25
ANSWER_WEIGHT_SAFETY: Final[float] = 0.10
HALLUCINATION_HIGH_RISK_THRESHOLD: Final[float] = 0.30
HALLUCINATION_MEDIUM_RISK_THRESHOLD: Final[float] = 0.15
ANSWER_APPROVE_THRESHOLD: Final[float] = 0.80
ANSWER_FLAG_THRESHOLD: Final[float] = 0.60
NLI_MODEL_NAME: Final[str] = "cross-encoder/nli-MiniLM2-L6-H768"
NLI_MAX_CHECKS: Final[int] = 5


# ============================================================================
# Quality Orchestrator Configuration
# ============================================================================

QUALITY_WEIGHT_ROUTE: Final[float] = 0.15
QUALITY_WEIGHT_RETRIEVAL: Final[float] = 0.25
QUALITY_WEIGHT_ANSWER_FACT: Final[float] = 0.40
QUALITY_WEIGHT_ANSWER_QUALITY: Final[float] = 0.15
QUALITY_WEIGHT_CITATION: Final[float] = 0.05
QUALITY_HIGH_THRESHOLD: Final[float] = 0.85
QUALITY_MEDIUM_THRESHOLD: Final[float] = 0.70
QUALITY_LOW_THRESHOLD: Final[float] = 0.50


# ============================================================================
# Context Tracker Configuration
# ============================================================================

CONTEXT_MAX_HISTORY_TURNS: Final[int] = 10
CONTEXT_SUMMARY_FREQUENCY: Final[int] = 5
CONTEXT_SUMMARY_MIN_TURNS: Final[int] = 3
CONTEXT_TTL_SECONDS: Final[int] = 3600


# ============================================================================
# Retry Strategy Configuration
# ============================================================================

MAX_ROUTE_RETRIES: Final[int] = 1
MAX_ANSWER_RETRIES: Final[int] = 1
MAX_TOTAL_RETRIES: Final[int] = 2
MAX_TOTAL_TIME_MS: Final[int] = 10000
ROUTE_VALIDATOR_TIMEOUT_MS: Final[int] = 500
RETRIEVAL_QUALITY_TIMEOUT_MS: Final[int] = 200
ANSWER_VALIDATOR_TIMEOUT_MS: Final[int] = 1000


# ============================================================================
# Performance Monitoring Configuration
# ============================================================================

PERF_THRESHOLD_FAST: Final[int] = 2000
PERF_THRESHOLD_MEDIUM: Final[int] = 5000
PERF_THRESHOLD_SLOW: Final[int] = 8000
ENABLE_PERFORMANCE_LOGGING: Final[bool] = True


# ============================================================================
# Fallback Configuration
# ============================================================================

FALLBACK_ROUTE_MAP: Final[dict] = {
    "hybrid": "vector",
    "graph": "vector",
    "react": "vector"
}
ENABLE_AUTO_FALLBACK: Final[bool] = True
