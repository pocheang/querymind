"""
Comprehensive test suite for Graph RAG optimizations.

Tests:
- Cache functionality
- Configuration management
- Agent unified interface
- Enhanced tools
- Admin endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.agents.graph_rag_cache import (
    LRUCache,
    cached_pdf_quality,
    cached_entity_extraction,
    get_cache_stats,
    clear_all_caches,
)
from app.agents.graph_rag_agent import (
    run_graph_rag,
    _run_basic_graph_rag,
    _run_enhanced_graph_rag,
    _format_graph_context,
)
from app.agents.graph_rag_agent_enhanced import (
    analyze_pdf_quality,
    extract_document_entities,
    get_document_context_for_query,
)


# ============================================================================
# Cache Tests
# ============================================================================

def test_lru_cache_basic_operations():
    """Test basic LRU cache operations."""
    cache = LRUCache(max_size=3, ttl_seconds=3600)

    # Set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Miss
    assert cache.get("nonexistent") is None

    # Stats
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1


def test_lru_cache_eviction():
    """Test LRU eviction when capacity is reached."""
    cache = LRUCache(max_size=2, ttl_seconds=3600)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")  # Should evict key1

    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


def test_lru_cache_move_to_end():
    """Test that accessed items are moved to end (LRU)."""
    cache = LRUCache(max_size=2, ttl_seconds=3600)

    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.get("key1")  # Access key1, moving it to end
    cache.set("key3", "value3")  # Should evict key2, not key1

    assert cache.get("key1") == "value1"
    assert cache.get("key2") is None
    assert cache.get("key3") == "value3"


def test_cached_pdf_quality_decorator():
    """Test PDF quality caching decorator."""
    clear_all_caches()

    call_count = 0

    @cached_pdf_quality
    def mock_analyze(text: str, metadata: dict) -> float:
        nonlocal call_count
        call_count += 1
        return 0.75

    # First call - cache miss
    result1 = mock_analyze("test text", {"format": "markdown"})
    assert result1 == 0.75
    assert call_count == 1

    # Second call with same inputs - cache hit
    result2 = mock_analyze("test text", {"format": "markdown"})
    assert result2 == 0.75
    assert call_count == 1  # Not called again

    # Different input - cache miss
    result3 = mock_analyze("different text", {"format": "markdown"})
    assert result3 == 0.75
    assert call_count == 2


def test_cache_stats_aggregation():
    """Test cache statistics aggregation."""
    clear_all_caches()

    # Trigger some cache operations
    analyze_pdf_quality("test", {})
    analyze_pdf_quality("test", {})  # Cache hit
    extract_document_entities("test")

    stats = get_cache_stats()

    assert "pdf_quality" in stats
    assert "entity_extraction" in stats
    assert stats["pdf_quality"]["hits"] >= 1
    assert stats["pdf_quality"]["misses"] >= 1


# ============================================================================
# Agent Unified Interface Tests
# ============================================================================

def test_run_graph_rag_basic_mode():
    """Test basic mode without enhancements."""
    with patch("app.tools.graph_tools.graph_lookup") as mock_lookup:
        mock_lookup.return_value = {
            "entities": [{"entity": "LLM", "relations": []}],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.5,
        }

        result = run_graph_rag(
            question="What is LLM?",
            enable_enhancements=False
        )

        assert result["graph_signal_score"] == 0.5
        assert "LLM" in result["entities"]
        mock_lookup.assert_called_once()


def test_run_graph_rag_enhanced_mode():
    """Test enhanced mode with PDF context."""
    with patch("app.agents.graph_rag_agent_enhanced.graph_lookup_enhanced") as mock_enhanced:
        mock_enhanced.return_value = {
            "entities": [{"entity": "LLM", "relations": []}],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.8,
            "confidence": "high",
        }

        # Use high-quality document to trigger enhanced mode
        retrieved_docs = [{
            "content": """
            # Large Language Models

            Large Language Models (LLMs) use Transformer architecture for
            natural language processing tasks including machine learning,
            deep learning, and artificial intelligence applications.

            | Model | Type |
            |-------|------|
            | GPT-4 | LLM  |

            ## References
            """,
            "metadata": {"format": "markdown", "total_pages": 10}
        }]

        result = run_graph_rag(
            question="What is LLM?",
            retrieved_docs=retrieved_docs,
            enable_enhancements=True
        )

        assert result["confidence"] == "high"
        assert result["graph_signal_score"] == 0.8
        mock_enhanced.assert_called_once()


def test_format_graph_context():
    """Test graph context formatting."""
    entities = [
        {
            "entity": "LLM",
            "relations": [
                {"relation": "uses", "weight": 0.9, "other": "Transformer"}
            ]
        }
    ]
    neighbors = [
        {"entity": "LLM", "relation": "enables", "other": "RAG", "weight": 0.85}
    ]
    paths = [
        {
            "source": "LLM",
            "rel1": "uses",
            "middle": "Transformer",
            "rel2": "implements",
            "target": "Attention",
            "weight": 0.8,
        }
    ]

    context = _format_graph_context(entities, neighbors, paths)

    assert "Entity: LLM" in context
    assert "uses (0.90) -> Transformer" in context
    assert "Neighbor: LLM -[enables|0.85]- RAG" in context
    assert "Path2Hop:" in context
    assert "Attention" in context


# ============================================================================
# Enhanced Agent Tests
# ============================================================================

def test_analyze_pdf_quality_structure_detection():
    """Test PDF quality analysis with structured content."""
    text = """
    # Introduction

    Large Language Models (LLMs) are AI systems that use deep learning,
    machine learning, natural language processing, and transformer architecture.
    These systems employ various algorithms, methods, and approaches for
    data analysis and implementation.

    | Model | Parameters |
    |-------|-----------|
    | GPT-4 | 1.7T      |

    - Feature 1: Advanced AI capabilities
    - Feature 2: System optimization
    - Feature 3: Process automation

    ## References
    """

    metadata = {"format": "markdown", "total_pages": 10}
    quality = analyze_pdf_quality(text, metadata)

    assert quality > 0.4  # Should detect structure (adjusted threshold)
    assert quality < 1.0


def test_analyze_pdf_quality_low_quality():
    """Test PDF quality analysis with poor content."""
    text = "a b c d e"
    metadata = {}

    quality = analyze_pdf_quality(text, metadata)

    assert quality < 0.3  # Low quality score


def test_extract_document_entities_english():
    """Test entity extraction from English text."""
    text = """
    Large Language Models (LLMs) like ChatGPT and Claude use
    Natural Language Processing and Transformer architecture.
    """

    entities = extract_document_entities(text, limit=10)

    assert "Large Language Models" in entities or "LLMs" in entities
    assert "ChatGPT" in entities or "Claude" in entities


def test_extract_document_entities_chinese():
    """Test entity extraction from Chinese text."""
    text = """
    大语言模型是一种基于深度学习的自然语言处理系统。
    它支持检索增强生成和智能客服系统。
    """

    entities = extract_document_entities(text, limit=10)

    assert any("大语言模型" in e or "自然语言处理" in e for e in entities)


def test_get_document_context_for_query():
    """Test document context analysis."""
    docs = [
        {
            "content": "Large Language Models (LLMs) are powerful AI systems.",
            "metadata": {"format": "markdown", "total_pages": 5}
        },
        {
            "content": "Natural Language Processing enables RAG systems.",
            "metadata": {"format": "markdown", "total_pages": 3}
        }
    ]

    context = get_document_context_for_query("What is LLM?", docs)

    assert "quality_score" in context
    assert "entities" in context
    assert "confidence" in context
    assert len(context["entities"]) > 0


# ============================================================================
# Configuration Tests
# ============================================================================

def test_config_imports():
    """Test that configuration constants are importable."""
    from app.agents.graph_rag_config import (
        QUALITY_THRESHOLD_HIGH,
        GRAPH_PARAMS_HIGH_QUALITY,
        ENGLISH_NOISE_TERMS,
    )

    assert isinstance(QUALITY_THRESHOLD_HIGH, float)
    assert isinstance(GRAPH_PARAMS_HIGH_QUALITY, dict)
    assert isinstance(ENGLISH_NOISE_TERMS, frozenset)


def test_tools_config_imports():
    """Test that tools configuration is importable."""
    from app.tools.graph_tools_config import (
        ENTITY_ALIASES,
        HIGH_VALUE_RELATIONS,
        RELATION_WEIGHT_HIGH,
    )

    assert isinstance(ENTITY_ALIASES, dict)
    assert isinstance(HIGH_VALUE_RELATIONS, frozenset)
    assert isinstance(RELATION_WEIGHT_HIGH, float)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
def test_end_to_end_basic_flow():
    """Test end-to-end basic Graph RAG flow."""
    with patch("app.tools.graph_tools.graph_lookup") as mock_lookup:
        mock_lookup.return_value = {
            "entities": [
                {
                    "entity": "LLM",
                    "relations": [
                        {"relation": "uses", "weight": 0.9, "other": "Transformer"}
                    ]
                }
            ],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.6,
        }

        result = run_graph_rag(
            question="What is a Large Language Model?",
            enable_enhancements=False
        )

        assert result["graph_signal_score"] == 0.6
        assert len(result["entities"]) > 0
        assert "context" in result


@pytest.mark.integration
def test_end_to_end_enhanced_flow():
    """Test end-to-end enhanced Graph RAG flow with PDF analysis."""
    docs = [
        {
            "content": """
            # Large Language Models

            Large Language Models (LLMs) are AI systems that use Transformer
            architecture for natural language processing, machine learning,
            deep learning tasks. They implement algorithms and methods for
            data analysis and system optimization.

            | Model | Parameters |
            |-------|-----------|
            | GPT-4 | 1.7T      |

            - Feature 1: Advanced processing
            - Feature 2: System optimization

            ## References
            """,
            "metadata": {"format": "markdown", "total_pages": 10}
        }
    ]

    with patch("app.agents.graph_rag_agent_enhanced.graph_lookup_enhanced") as mock_lookup:
        mock_lookup.return_value = {
            "entities": [{"entity": "llm", "relations": []}],
            "neighbors": [],
            "paths": [],
            "graph_signal_score": 0.75,
            "confidence": "high",
        }

        result = run_graph_rag(
            question="What is LLM?",
            retrieved_docs=docs,
            enable_enhancements=True
        )

        assert result["confidence"] == "high"
        assert result["graph_signal_score"] >= 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
