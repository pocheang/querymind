"""
Query complexity analyzer and adaptive strategy router for v0.4.4.

Automatically detects query complexity and routes to appropriate retrieval strategy:
- Simple queries → Fast mode (400ms)
- Medium queries → Standard mode (800ms)
- Complex queries → Precise mode (1500ms)

Optimizes average response time while maintaining quality.
"""

import logging
import re
from typing import Literal

from app.services.tracing import traced_span

logger = logging.getLogger(__name__)

ComplexityLevel = Literal["simple", "medium", "complex"]


class QueryComplexityAnalyzer:
    """
    Analyzes query complexity using fast heuristics.

    Complexity indicators:
    - Query length
    - Number of question words
    - Number of entities/concepts
    - Presence of connectors (and, or, also)
    - Multi-part questions

    Analysis time: ~1ms (pure heuristics, no LLM)
    """

    def __init__(self):
        self.question_words_en = {
            "what", "how", "why", "when", "where", "who", "which",
            "can", "could", "would", "should", "does", "do", "is", "are",
        }

        self.question_words_zh = {
            "什么", "如何", "为什么", "怎么", "哪里", "谁", "哪个",
            "怎样", "为何", "何时", "何地", "是否", "能否",
        }

        self.connectors = {
            # English
            "and", "or", "also", "as well as", "in addition", "furthermore",
            "moreover", "besides", "plus",
            # Chinese
            "和", "与", "以及", "还有", "另外", "并且", "同时", "而且",
        }

        self.complexity_indicators = {
            # Comparison
            "comparison": ["compare", "difference", "versus", "vs", "比较", "对比", "区别"],
            # Sequential/process
            "sequential": ["step", "process", "how to", "procedure", "步骤", "流程", "过程"],
            # Analytical
            "analytical": ["analyze", "explain", "why", "reason", "因为", "原因", "分析", "解释"],
            # Aggregate
            "aggregate": ["all", "every", "list", "summarize", "总结", "列出", "所有"],
        }

    def analyze(self, query: str) -> tuple[ComplexityLevel, dict]:
        """
        Analyze query complexity.

        Args:
            query: User query

        Returns:
            Tuple of (complexity level, analysis details)
        """
        with traced_span("analysis.query_complexity", {}):
            query_lower = query.lower()

            # Feature extraction
            features = {
                "length": len(query),
                "word_count": len(query.split()),
                "question_word_count": self._count_question_words(query_lower),
                "connector_count": self._count_connectors(query_lower),
                "punctuation_count": query.count("?") + query.count("？"),
                "has_comparison": self._has_indicator(query_lower, "comparison"),
                "has_sequential": self._has_indicator(query_lower, "sequential"),
                "has_analytical": self._has_indicator(query_lower, "analytical"),
                "has_aggregate": self._has_indicator(query_lower, "aggregate"),
            }

            # Compute complexity score
            complexity_score = self._compute_complexity_score(features)

            # Classify complexity
            if complexity_score <= 2:
                level = "simple"
            elif complexity_score <= 5:
                level = "medium"
            else:
                level = "complex"

            analysis = {
                "level": level,
                "score": complexity_score,
                "features": features,
                "recommended_strategy": self._get_strategy_for_level(level),
            }

            logger.info(
                f"Query complexity: {level} (score: {complexity_score:.1f}) - "
                f"Length: {features['length']}, Questions: {features['question_word_count']}, "
                f"Connectors: {features['connector_count']}"
            )

            return level, analysis

    def _count_question_words(self, query: str) -> int:
        """Count question words in query."""
        count = 0
        words = query.split()

        for word in words:
            if word in self.question_words_en or word in self.question_words_zh:
                count += 1

        return count

    def _count_connectors(self, query: str) -> int:
        """Count connector words/phrases in query."""
        count = 0

        for connector in self.connectors:
            if connector in query:
                count += 1

        return count

    def _has_indicator(self, query: str, category: str) -> bool:
        """Check if query has indicators of a specific category."""
        indicators = self.complexity_indicators.get(category, [])

        for indicator in indicators:
            if indicator in query:
                return True

        return False

    def _compute_complexity_score(self, features: dict) -> float:
        """
        Compute complexity score from features.

        Score components:
        - Length: 0-3 points
        - Question words: 0-2 points
        - Connectors: 0-2 points
        - Multiple questions: 0-1 point
        - Special indicators: 0-2 points

        Total range: 0-10
        """
        score = 0.0

        # 1. Length score (0-3)
        if features["length"] < 20:
            score += 0  # Very short = simple
        elif features["length"] < 50:
            score += 1  # Short-medium
        elif features["length"] < 100:
            score += 2  # Medium-long
        else:
            score += 3  # Very long = complex

        # 2. Question words (0-2)
        q_count = features["question_word_count"]
        if q_count == 0:
            score += 0.5  # Statement query
        elif q_count == 1:
            score += 0  # Single question = simple
        elif q_count == 2:
            score += 1  # Two questions
        else:
            score += 2  # Multiple questions = complex

        # 3. Connectors (0-2)
        conn_count = features["connector_count"]
        if conn_count >= 3:
            score += 2
        elif conn_count >= 1:
            score += 1

        # 4. Multiple punctuation (0-1)
        if features["punctuation_count"] > 1:
            score += 1

        # 5. Special indicators (0-2)
        indicator_bonus = 0
        if features["has_comparison"]:
            indicator_bonus += 1
        if features["has_sequential"]:
            indicator_bonus += 0.5
        if features["has_analytical"]:
            indicator_bonus += 0.5
        if features["has_aggregate"]:
            indicator_bonus += 0.5

        score += min(2, indicator_bonus)

        return score

    def _get_strategy_for_level(self, level: ComplexityLevel) -> str:
        """Get recommended retrieval strategy for complexity level."""
        strategy_map = {
            "simple": "fast",
            "medium": "standard",
            "complex": "precise",
        }
        return strategy_map.get(level, "standard")


class AdaptiveStrategyRouter:
    """
    Routes queries to appropriate retrieval strategy based on complexity.

    Strategies:
    - Fast mode: 2-path retrieval, no rerank, ~400ms
    - Standard mode: 3-path retrieval, fast rerank, ~800ms
    - Precise mode: 3-path retrieval, full rerank, verification, ~1500ms
    """

    def __init__(self):
        self.analyzer = QueryComplexityAnalyzer()

        # Strategy configurations
        self.strategies = {
            "fast": {
                "paths": ["vector", "bm25"],  # 2 paths only
                "enable_rerank": False,
                "rerank_candidates": 0,
                "compression_ratio": 0.7,  # More aggressive
                "target_time_ms": 400,
            },
            "standard": {
                "paths": ["vector", "bm25", "hybrid"],  # 3 paths
                "enable_rerank": True,
                "rerank_candidates": 20,
                "compression_ratio": 0.6,
                "target_time_ms": 800,
            },
            "precise": {
                "paths": ["vector", "bm25", "hybrid"],  # 3 paths
                "enable_rerank": True,
                "rerank_candidates": 30,
                "compression_ratio": 0.6,
                "verification": True,
                "target_time_ms": 1500,
            },
        }

    def route(self, query: str) -> tuple[str, dict]:
        """
        Route query to appropriate strategy.

        Args:
            query: User query

        Returns:
            Tuple of (strategy name, strategy config)
        """
        complexity, analysis = self.analyzer.analyze(query)

        strategy_name = analysis["recommended_strategy"]
        strategy_config = self.strategies[strategy_name]

        logger.info(
            f"Routing query to '{strategy_name}' strategy "
            f"(complexity: {complexity}, score: {analysis['score']:.1f})"
        )

        return strategy_name, {
            **strategy_config,
            "complexity_analysis": analysis,
        }

    def get_strategy_config(self, strategy_name: str) -> dict:
        """Get configuration for a specific strategy."""
        return self.strategies.get(strategy_name, self.strategies["standard"])


# Global instances
_analyzer: QueryComplexityAnalyzer | None = None
_router: AdaptiveStrategyRouter | None = None


def get_complexity_analyzer() -> QueryComplexityAnalyzer:
    """Get or create global complexity analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = QueryComplexityAnalyzer()
    return _analyzer


def get_adaptive_router() -> AdaptiveStrategyRouter:
    """Get or create global adaptive router."""
    global _router
    if _router is None:
        _router = AdaptiveStrategyRouter()
    return _router


def analyze_query_complexity(query: str) -> tuple[ComplexityLevel, dict]:
    """
    Convenience function for query complexity analysis.

    Args:
        query: User query

    Returns:
        Tuple of (complexity level, analysis details)
    """
    analyzer = get_complexity_analyzer()
    return analyzer.analyze(query)


def route_query_adaptive(query: str) -> tuple[str, dict]:
    """
    Convenience function for adaptive query routing.

    Args:
        query: User query

    Returns:
        Tuple of (strategy name, strategy config)
    """
    router = get_adaptive_router()
    return router.route(query)
