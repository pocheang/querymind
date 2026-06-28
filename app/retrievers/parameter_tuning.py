"""
Dynamic parameter tuning based on query complexity.

Adjusts top-k and RRF weights dynamically to optimize retrieval quality
for different query types.
"""

import re
from typing import Literal

# Complexity classification patterns
_COMPLEX_KEYWORDS = re.compile(
    r"(对比|比较|compare|trade[-\s]?off|versus|vs\.|优缺点|architecture|"
    r"root cause|复盘|多阶段|attack chain|drawback|benefit|advantage|disadvantage)",
    flags=re.IGNORECASE,
)

_MEDIUM_KEYWORDS = re.compile(
    r"(how does|how do|explain|describe|工作原理|如何|怎样|解释|说明)",
    flags=re.IGNORECASE,
)

ComplexityLevel = Literal["simple", "medium", "complex"]


def classify_query_complexity(query: str | None) -> ComplexityLevel:
    """
    Classify query complexity into simple, medium, or complex.

    Rules:
    - Simple: Short keyword queries or basic questions (< 10 tokens)
    - Medium: Moderate length with some detail (10-20 tokens) or contains "how/explain"
    - Complex: Long queries (> 20 tokens), comparisons, multi-part questions

    Args:
        query: User query string

    Returns:
        Complexity level: "simple", "medium", or "complex"
    """
    if not query or not query.strip():
        return "simple"

    query_str = str(query).strip()

    # Count tokens (words + Chinese characters)
    # Use word boundaries for English and character count for Chinese
    english_tokens = len(re.findall(r"\b[a-zA-Z0-9_]+\b", query_str))
    chinese_chars = len(re.findall(r"[一-鿿]", query_str))
    # Approximate: ~2 Chinese chars = 1 token
    total_tokens = english_tokens + (chinese_chars // 2)

    # Check for complexity indicators
    has_complex_keyword = bool(_COMPLEX_KEYWORDS.search(query_str))
    has_medium_keyword = bool(_MEDIUM_KEYWORDS.search(query_str))
    question_marks = query_str.count("?") + query_str.count("？")

    # Classification logic
    if has_complex_keyword or question_marks >= 2 or total_tokens > 20:
        return "complex"

    if has_medium_keyword or (10 <= total_tokens <= 20):
        return "medium"

    return "simple"


def get_dynamic_top_k(complexity: ComplexityLevel | None) -> int:
    """
    Get dynamic top-k based on query complexity.

    Args:
        complexity: Query complexity level

    Returns:
        top_k value: 15 (simple), 20 (medium), 30 (complex)
    """
    if complexity == "medium":
        return 20
    elif complexity == "complex":
        return 30
    else:
        # Default to simple
        return 15


def get_dynamic_rrf_weights(complexity: ComplexityLevel | None) -> tuple[float, float]:
    """
    Get dynamic vector:BM25 weights based on query type.

    Strategy:
    - Simple queries: Favor BM25 for exact keyword matching (0.3:0.7)
    - Medium queries: Balanced weights (0.5:0.5)
    - Complex queries: Favor vector for semantic understanding (0.7:0.3)

    Args:
        complexity: Query complexity level

    Returns:
        Tuple of (vector_weight, bm25_weight) that sum to 1.0
    """
    if complexity == "simple":
        # Favor BM25 for keyword matching
        return (0.3, 0.7)
    elif complexity == "medium":
        # Balanced
        return (0.5, 0.5)
    elif complexity == "complex":
        # Favor vector for semantic understanding
        return (0.7, 0.3)
    else:
        # Default to balanced
        return (0.5, 0.5)


def apply_dynamic_parameters(query: str | None) -> dict:
    """
    Apply dynamic parameter tuning based on query.

    Args:
        query: User query string

    Returns:
        Dictionary containing:
        - complexity: Query complexity level
        - top_k: Dynamic top-k value
        - vector_weight: Vector search weight
        - bm25_weight: BM25 search weight
    """
    complexity = classify_query_complexity(query)
    top_k = get_dynamic_top_k(complexity)
    vector_weight, bm25_weight = get_dynamic_rrf_weights(complexity)

    return {
        "complexity": complexity,
        "top_k": top_k,
        "vector_weight": vector_weight,
        "bm25_weight": bm25_weight,
    }
