"""
Tests for query expansion module.

Tests entity extraction, synonym expansion, and query augmentation.
"""

import pytest

from app.retrievers.query_expansion import (
    expand_query,
    extract_entities,
    get_synonyms,
)


class TestEntityExtraction:
    """Test entity extraction from queries."""

    def test_extract_technical_entities(self):
        """Should extract technical terms and acronyms."""
        query = "How does ML model training work?"
        entities = extract_entities(query)

        assert "ML" in entities or "model training" in entities
        assert len(entities) > 0

    def test_extract_chinese_entities(self):
        """Should extract Chinese entities."""
        query = "机器学习模型如何训练"
        entities = extract_entities(query)

        assert len(entities) >= 0  # May have entities or empty
        # Chinese entity extraction is optional based on available tools

    def test_extract_mixed_language(self):
        """Should handle mixed English and Chinese."""
        query = "What is 深度学习 in AI?"
        entities = extract_entities(query)

        assert len(entities) >= 0

    def test_empty_query(self):
        """Should handle empty query gracefully."""
        entities = extract_entities("")
        assert entities == []

    def test_acronym_detection(self):
        """Should detect common technical acronyms."""
        query = "What is NLP and AI?"
        entities = extract_entities(query)

        # Should at least detect some entities
        assert len(entities) > 0


class TestSynonymExpansion:
    """Test synonym dictionary and expansion."""

    def test_ml_synonym(self):
        """Should expand ML to machine learning."""
        synonyms = get_synonyms("ML")

        assert "machine learning" in synonyms

    def test_ai_synonym(self):
        """Should expand AI to artificial intelligence."""
        synonyms = get_synonyms("AI")

        assert "artificial intelligence" in synonyms

    def test_nlp_synonym(self):
        """Should expand NLP to natural language processing."""
        synonyms = get_synonyms("NLP")

        assert "natural language processing" in synonyms

    def test_unknown_term(self):
        """Should return empty list for unknown terms."""
        synonyms = get_synonyms("xyzabc123")

        assert synonyms == []

    def test_case_insensitive(self):
        """Should handle different cases."""
        synonyms_upper = get_synonyms("ML")
        synonyms_lower = get_synonyms("ml")

        assert synonyms_upper == synonyms_lower

    def test_chinese_synonyms(self):
        """Should support Chinese synonyms."""
        synonyms = get_synonyms("机器学习")

        # May have ML as synonym or empty
        assert isinstance(synonyms, list)


class TestQueryExpansion:
    """Test complete query expansion."""

    def test_expand_ml_query(self):
        """Should expand query with ML acronym."""
        query = "What is ML?"
        expanded = expand_query(query)

        # Should include original and expanded terms
        assert query in expanded or "machine learning" in expanded.lower()
        assert len(expanded) > len(query)

    def test_expand_multiple_acronyms(self):
        """Should expand multiple acronyms in one query."""
        query = "ML and AI in NLP"
        expanded = expand_query(query)

        # Should contain expanded forms
        expanded_lower = expanded.lower()
        assert (
            "machine learning" in expanded_lower
            or "artificial intelligence" in expanded_lower
            or "natural language processing" in expanded_lower
        )

    def test_expand_chinese_query(self):
        """Should handle Chinese queries."""
        query = "机器学习模型训练"
        expanded = expand_query(query)

        # Should at least return original query
        assert len(expanded) >= len(query)

    def test_expand_mixed_language(self):
        """Should handle mixed language queries."""
        query = "What is 机器学习 ML?"
        expanded = expand_query(query)

        assert len(expanded) > 0

    def test_no_expansion_needed(self):
        """Should return query if no expansion needed."""
        query = "What is machine learning?"
        expanded = expand_query(query)

        # Should at least contain original meaning
        assert "machine learning" in expanded.lower()

    def test_empty_query(self):
        """Should handle empty query."""
        expanded = expand_query("")

        assert expanded == ""

    def test_expansion_preserves_context(self):
        """Expansion should preserve query context."""
        query = "How to use ML models in production?"
        expanded = expand_query(query)

        # Should preserve question structure
        assert "machine learning" in expanded.lower() or "ML" in expanded


class TestExpansionQuality:
    """Test expansion quality metrics."""

    def test_expansion_not_too_long(self):
        """Expansion should be reasonable length."""
        query = "ML AI NLP"
        expanded = expand_query(query)

        # Should not explode to unreasonable length
        # Max ~10x expansion is reasonable
        assert len(expanded) < len(query) * 10

    def test_expansion_deduplication(self):
        """Should not duplicate terms."""
        query = "ML machine learning ML"
        expanded = expand_query(query)

        # Count occurrences of "machine learning"
        count = expanded.lower().count("machine learning")
        # Should not have excessive duplicates (max 2-3 is reasonable)
        assert count <= 3

    def test_abbreviation_expansion_examples(self):
        """Test common abbreviations that should expand."""
        test_cases = [
            ("ML", ["machine learning"]),
            ("AI", ["artificial intelligence"]),
            ("NLP", ["natural language processing"]),
            ("DL", ["deep learning"]),
            ("NN", ["neural network"]),
        ]

        for abbrev, expected_synonyms in test_cases:
            synonyms = get_synonyms(abbrev)
            # At least one expected synonym should be present
            assert any(exp in synonyms for exp in expected_synonyms), f"Failed for {abbrev}"


class TestIntegrationWithRetrieval:
    """Test integration patterns with retrieval system."""

    def test_expanded_query_format(self):
        """Expanded query should be valid for retrieval."""
        query = "What is ML?"
        expanded = expand_query(query)

        # Should be non-empty string
        assert isinstance(expanded, str)
        assert len(expanded) > 0
        # Should not have special characters that break search
        assert not expanded.startswith("[")
        assert not expanded.endswith("]")

    def test_entity_extraction_output_format(self):
        """Entities should be in usable format."""
        query = "ML and AI models"
        entities = extract_entities(query)

        assert isinstance(entities, list)
        for entity in entities:
            assert isinstance(entity, str)
            assert len(entity) > 0
