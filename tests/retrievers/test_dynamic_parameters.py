"""
Tests for dynamic parameter tuning based on query complexity.

Tests query classification, top-k adjustment, and RRF weight tuning.
"""

import pytest

from app.retrievers.parameter_tuning import (
    classify_query_complexity,
    get_dynamic_top_k,
    get_dynamic_rrf_weights,
    apply_dynamic_parameters,
)


class TestQueryComplexityClassification:
    """Test query complexity classification."""

    def test_simple_query_short_keyword(self):
        """Simple keyword queries should be classified as 'simple'."""
        query = "ML model"
        complexity = classify_query_complexity(query)

        assert complexity == "simple"

    def test_simple_query_basic_question(self):
        """Basic questions should be classified as 'simple'."""
        query = "What is machine learning?"
        complexity = classify_query_complexity(query)

        assert complexity == "simple"

    def test_medium_query_moderate_length(self):
        """Moderate length queries with some detail should be 'medium'."""
        query = "How does neural network training work with backpropagation?"
        complexity = classify_query_complexity(query)

        assert complexity == "medium"

    def test_medium_query_multiple_concepts(self):
        """Queries with multiple concepts should be 'medium'."""
        query = "How does supervised learning differ from unsupervised learning"
        complexity = classify_query_complexity(query)

        assert complexity == "medium"

    def test_complex_query_comparison(self):
        """Comparison queries should be classified as 'complex'."""
        query = "Compare the trade-offs between transformer architectures and recurrent neural networks for sequence modeling"
        complexity = classify_query_complexity(query)

        assert complexity == "complex"

    def test_complex_query_multi_part(self):
        """Multi-part questions should be 'complex'."""
        query = "What are the benefits and drawbacks of using attention mechanisms? How do they compare to traditional RNNs?"
        complexity = classify_query_complexity(query)

        assert complexity == "complex"

    def test_complex_query_chinese(self):
        """Complex Chinese queries should be classified correctly."""
        query = "对比深度学习和传统机器学习在图像识别中的优缺点，以及它们各自适用的场景"
        complexity = classify_query_complexity(query)

        assert complexity == "complex"

    def test_simple_query_chinese(self):
        """Simple Chinese queries should be 'simple'."""
        query = "什么是机器学习"
        complexity = classify_query_complexity(query)

        assert complexity == "simple"

    def test_empty_query(self):
        """Empty query should default to 'simple'."""
        complexity = classify_query_complexity("")

        assert complexity == "simple"

    def test_query_with_root_cause_keyword(self):
        """Queries with 'root cause' should be complex."""
        query = "What is the root cause of the model overfitting?"
        complexity = classify_query_complexity(query)

        assert complexity == "complex"

    def test_query_with_architecture_keyword(self):
        """Queries about architecture should be complex."""
        query = "Explain the architecture of transformers"
        complexity = classify_query_complexity(query)

        assert complexity == "complex"


class TestDynamicTopK:
    """Test dynamic top-k parameter adjustment."""

    def test_simple_query_top_k(self):
        """Simple queries should use top_k=15."""
        top_k = get_dynamic_top_k("simple")

        assert top_k == 15

    def test_medium_query_top_k(self):
        """Medium queries should use top_k=20."""
        top_k = get_dynamic_top_k("medium")

        assert top_k == 20

    def test_complex_query_top_k(self):
        """Complex queries should use top_k=30."""
        top_k = get_dynamic_top_k("complex")

        assert top_k == 30

    def test_invalid_complexity_defaults_to_simple(self):
        """Invalid complexity should default to simple (15)."""
        top_k = get_dynamic_top_k("unknown")

        assert top_k == 15

    def test_none_complexity_defaults_to_simple(self):
        """None complexity should default to simple (15)."""
        top_k = get_dynamic_top_k(None)

        assert top_k == 15


class TestDynamicRRFWeights:
    """Test dynamic RRF weight tuning by query type."""

    def test_simple_query_weights_favor_bm25(self):
        """Simple queries should favor BM25 for exact keyword matching."""
        vector_weight, bm25_weight = get_dynamic_rrf_weights("simple")

        # Simple queries: BM25 should have higher weight
        assert bm25_weight > vector_weight
        # Weights should sum to 1.0
        assert abs((vector_weight + bm25_weight) - 1.0) < 0.01

    def test_medium_query_weights_balanced(self):
        """Medium queries should have balanced weights."""
        vector_weight, bm25_weight = get_dynamic_rrf_weights("medium")

        # Should be relatively balanced
        assert 0.4 <= vector_weight <= 0.6
        assert 0.4 <= bm25_weight <= 0.6
        assert abs((vector_weight + bm25_weight) - 1.0) < 0.01

    def test_complex_query_weights_favor_vector(self):
        """Complex queries should favor vector search for semantic matching."""
        vector_weight, bm25_weight = get_dynamic_rrf_weights("complex")

        # Complex queries: vector should have higher weight
        assert vector_weight > bm25_weight
        assert abs((vector_weight + bm25_weight) - 1.0) < 0.01

    def test_weights_always_sum_to_one(self):
        """Weights should always sum to 1.0 for all complexity levels."""
        for complexity in ["simple", "medium", "complex"]:
            vector_weight, bm25_weight = get_dynamic_rrf_weights(complexity)
            total = vector_weight + bm25_weight

            assert abs(total - 1.0) < 0.01, f"Weights don't sum to 1.0 for {complexity}"

    def test_weights_are_positive(self):
        """All weights should be positive."""
        for complexity in ["simple", "medium", "complex"]:
            vector_weight, bm25_weight = get_dynamic_rrf_weights(complexity)

            assert vector_weight > 0
            assert bm25_weight > 0

    def test_invalid_complexity_defaults_to_balanced(self):
        """Invalid complexity should default to balanced weights."""
        vector_weight, bm25_weight = get_dynamic_rrf_weights("unknown")

        # Should default to balanced
        assert 0.4 <= vector_weight <= 0.6
        assert abs((vector_weight + bm25_weight) - 1.0) < 0.01


class TestApplyDynamicParameters:
    """Test complete dynamic parameter application."""

    def test_apply_for_simple_query(self):
        """Should return correct parameters for simple query."""
        query = "ML model"
        params = apply_dynamic_parameters(query)

        assert params["complexity"] == "simple"
        assert params["top_k"] == 15
        assert params["bm25_weight"] > params["vector_weight"]

    def test_apply_for_medium_query(self):
        """Should return correct parameters for medium query."""
        query = "How does neural network training work with backpropagation?"
        params = apply_dynamic_parameters(query)

        assert params["complexity"] == "medium"
        assert params["top_k"] == 20
        assert 0.4 <= params["vector_weight"] <= 0.6

    def test_apply_for_complex_query(self):
        """Should return correct parameters for complex query."""
        query = "Compare the trade-offs between transformer and RNN architectures"
        params = apply_dynamic_parameters(query)

        assert params["complexity"] == "complex"
        assert params["top_k"] == 30
        assert params["vector_weight"] > params["bm25_weight"]

    def test_params_contain_all_required_keys(self):
        """Result should contain all required keys."""
        query = "test query"
        params = apply_dynamic_parameters(query)

        assert "complexity" in params
        assert "top_k" in params
        assert "vector_weight" in params
        assert "bm25_weight" in params

    def test_params_are_serializable(self):
        """All parameter values should be JSON serializable."""
        import json

        query = "test query"
        params = apply_dynamic_parameters(query)

        # Should not raise exception
        json_str = json.dumps(params)
        assert len(json_str) > 0


class TestParameterTuningQuality:
    """Test that parameter tuning improves retrieval quality."""

    def test_complex_query_gets_more_candidates(self):
        """Complex queries should retrieve more candidates than simple ones."""
        simple_params = apply_dynamic_parameters("ML")
        complex_params = apply_dynamic_parameters(
            "Compare transformer architectures and RNN for sequence modeling"
        )

        assert complex_params["top_k"] > simple_params["top_k"]

    def test_keyword_query_favors_lexical_matching(self):
        """Keyword queries should favor BM25 for lexical matching."""
        params = apply_dynamic_parameters("API endpoint authentication")

        # Should favor BM25 for exact keyword matching
        assert params["bm25_weight"] >= params["vector_weight"]

    def test_semantic_query_favors_vector_search(self):
        """Semantic queries should favor vector search."""
        params = apply_dynamic_parameters(
            "What are the trade-offs between different neural network architectures?"
        )

        # Should favor vector for semantic understanding
        assert params["vector_weight"] >= params["bm25_weight"]

    def test_chinese_query_classification_works(self):
        """Chinese queries should be classified correctly."""
        simple_cn = apply_dynamic_parameters("机器学习")
        complex_cn = apply_dynamic_parameters("对比深度学习和传统机器学习的优缺点及适用场景")

        # Complex Chinese query should have higher top_k
        assert complex_cn["top_k"] > simple_cn["top_k"]


class TestBackwardCompatibility:
    """Test backward compatibility and edge cases."""

    def test_handles_none_query(self):
        """Should handle None query gracefully."""
        params = apply_dynamic_parameters(None)

        assert params["complexity"] == "simple"
        assert params["top_k"] == 15

    def test_handles_empty_string(self):
        """Should handle empty string gracefully."""
        params = apply_dynamic_parameters("")

        assert params["complexity"] == "simple"
        assert params["top_k"] == 15

    def test_handles_whitespace_only(self):
        """Should handle whitespace-only query."""
        params = apply_dynamic_parameters("   \n\t  ")

        assert params["complexity"] == "simple"
        assert params["top_k"] == 15

    def test_handles_very_long_query(self):
        """Should handle very long queries."""
        long_query = "What is machine learning? " * 50
        params = apply_dynamic_parameters(long_query)

        # Should classify as complex due to length
        assert params["complexity"] == "complex"
        assert params["top_k"] == 30

    def test_special_characters_dont_break_classification(self):
        """Special characters should not break classification."""
        query = "What is ML? How does it work? !@#$%^&*()"
        params = apply_dynamic_parameters(query)

        # Should still classify correctly
        assert params["complexity"] in ["simple", "medium", "complex"]
        assert params["top_k"] in [15, 20, 30]
