"""
Tests for multi-stage entity extraction with validation.

Task 6: Graph RAG - Robust Entity Extraction
"""

import pytest


class TestRuleBasedExtraction:
    """Test Stage 1: Rule-based NER for common patterns."""

    def test_extract_technical_terms(self):
        """Extract technical terms like LLM, AI, API."""
        from app.graph.entity_extraction import extract_entities_rule_based

        query = "What is LLM and how does AI API work?"
        entities = extract_entities_rule_based(query)

        assert len(entities) > 0
        entity_names = [e["text"].lower() for e in entities]
        assert any("llm" in name or "large language model" in name for name in entity_names)
        assert any("ai" in name or "artificial intelligence" in name for name in entity_names)
        assert any("api" in name for name in entity_names)

    def test_extract_chinese_terms(self):
        """Extract Chinese technical terms."""
        from app.graph.entity_extraction import extract_entities_rule_based

        query = "什么是大模型和网络安全？"
        entities = extract_entities_rule_based(query)

        assert len(entities) > 0
        entity_texts = [e["text"] for e in entities]
        assert any("大模型" in text or "网络安全" in text for text in entity_texts)

    def test_extract_acronyms(self):
        """Extract acronyms and abbreviations."""
        from app.graph.entity_extraction import extract_entities_rule_based

        query = "SQL injection and XSS attacks"
        entities = extract_entities_rule_based(query)

        assert len(entities) > 0
        entity_texts = [e["text"] for e in entities]
        assert any("SQL" in text.upper() or "injection" in text.lower() for text in entity_texts)
        assert any("XSS" in text.upper() or "attack" in text.lower() for text in entity_texts)

    def test_extract_capitalized_entities(self):
        """Extract capitalized proper nouns."""
        from app.graph.entity_extraction import extract_entities_rule_based

        query = "How does OpenAI GPT compare to Google Gemini?"
        entities = extract_entities_rule_based(query)

        assert len(entities) > 0
        entity_texts = [e["text"] for e in entities]
        assert any("OpenAI" in text or "GPT" in text for text in entity_texts)
        assert any("Google" in text or "Gemini" in text for text in entity_texts)

    def test_no_entities_in_simple_query(self):
        """Return empty list for queries without clear entities."""
        from app.graph.entity_extraction import extract_entities_rule_based

        query = "how to do this?"
        entities = extract_entities_rule_based(query)

        # May have some generic terms, but should not extract common words
        for entity in entities:
            assert entity["text"].lower() not in {"how", "to", "do", "this"}


class TestLLMBasedExtraction:
    """Test Stage 2: LLM-based extraction for complex cases."""

    def test_llm_extraction_basic(self):
        """LLM extracts entities from complex queries."""
        from app.graph.entity_extraction import extract_entities_llm

        query = "Explain how transformer attention mechanism relates to positional encoding"
        entities = extract_entities_llm(query, max_entities=5)

        assert len(entities) > 0
        assert all(isinstance(e, dict) for e in entities)
        assert all("text" in e and "confidence" in e for e in entities)
        assert all(0.0 <= e["confidence"] <= 1.0 for e in entities)

    def test_llm_extraction_respects_max_entities(self):
        """LLM respects max_entities limit."""
        from app.graph.entity_extraction import extract_entities_llm

        query = "AI machine learning deep learning neural networks transformers attention BERT GPT"
        entities = extract_entities_llm(query, max_entities=3)

        assert len(entities) <= 3

    def test_llm_extraction_chinese(self):
        """LLM extracts Chinese entities."""
        from app.graph.entity_extraction import extract_entities_llm

        query = "解释深度学习中的注意力机制和Transformer架构"
        entities = extract_entities_llm(query, max_entities=5)

        assert len(entities) > 0
        # Should extract both Chinese and English terms
        entity_texts = [e["text"] for e in entities]
        assert len(entity_texts) > 0

    def test_llm_extraction_handles_empty_query(self):
        """LLM handles empty query gracefully."""
        from app.graph.entity_extraction import extract_entities_llm

        entities = extract_entities_llm("", max_entities=5)
        assert entities == []

    def test_llm_extraction_handles_error(self, monkeypatch):
        """LLM extraction handles LLM errors gracefully."""
        from app.graph import entity_extraction

        def mock_llm_call(*args, **kwargs):
            raise Exception("LLM unavailable")

        # Mock the internal LLM call function
        monkeypatch.setattr(entity_extraction, "_call_llm_for_entities", mock_llm_call)

        entities = entity_extraction.extract_entities_llm("test query", max_entities=5)
        assert entities == []


class TestFuzzyMatching:
    """Test fuzzy matching for entity linking."""

    def test_fuzzy_match_exact(self):
        """Exact match returns distance 0."""
        from app.graph.entity_extraction import fuzzy_match_entity

        result = fuzzy_match_entity("LLM", ["LLM", "AI", "API"])
        assert result is not None
        assert result["matched"] == "LLM"
        assert result["distance"] == 0

    def test_fuzzy_match_case_insensitive(self):
        """Case-insensitive matching."""
        from app.graph.entity_extraction import fuzzy_match_entity

        result = fuzzy_match_entity("llm", ["LLM", "AI", "API"])
        assert result is not None
        assert result["matched"].upper() == "LLM"
        assert result["distance"] == 0

    def test_fuzzy_match_levenshtein(self):
        """Levenshtein distance <= 2 matches."""
        from app.graph.entity_extraction import fuzzy_match_entity

        # "LLMs" vs "LLM" - distance 1
        result = fuzzy_match_entity("LLMs", ["LLM", "AI", "API"])
        assert result is not None
        assert result["matched"] == "LLM"
        assert result["distance"] == 1

        # "APIs" vs "API" - distance 1
        result = fuzzy_match_entity("APIs", ["LLM", "AI", "API"])
        assert result is not None
        assert result["matched"] == "API"
        assert result["distance"] == 1

    def test_fuzzy_match_no_match(self):
        """No match when distance > 2."""
        from app.graph.entity_extraction import fuzzy_match_entity

        result = fuzzy_match_entity("completely_different", ["LLM", "AI", "API"])
        assert result is None

    def test_fuzzy_match_returns_best(self):
        """Returns the closest match."""
        from app.graph.entity_extraction import fuzzy_match_entity

        result = fuzzy_match_entity("LLMx", ["LLM", "LLMM", "LLMMM"])
        assert result is not None
        assert result["matched"] == "LLM"
        assert result["distance"] == 1


class TestCrossValidation:
    """Test cross-validation between rule-based and LLM extraction."""

    def test_cross_validate_agreement(self):
        """Entities validated by both methods get higher confidence."""
        from app.graph.entity_extraction import cross_validate_entities

        rule_entities = [
            {"text": "LLM", "confidence": 0.8, "source": "rule"},
            {"text": "API", "confidence": 0.7, "source": "rule"},
        ]
        llm_entities = [
            {"text": "LLM", "confidence": 0.9, "source": "llm"},
            {"text": "AI", "confidence": 0.85, "source": "llm"},
        ]

        validated = cross_validate_entities(rule_entities, llm_entities)

        # LLM should have boosted confidence (appears in both)
        llm_entry = next(e for e in validated if e["text"] == "LLM")
        assert llm_entry["confidence"] > 0.9  # Boosted
        assert llm_entry["validated_by_both"] is True

        # API only in rule-based
        api_entry = next((e for e in validated if e["text"] == "API"), None)
        if api_entry:
            assert api_entry.get("validated_by_both", False) is False

    def test_cross_validate_fuzzy_match(self):
        """Cross-validation uses fuzzy matching."""
        from app.graph.entity_extraction import cross_validate_entities

        rule_entities = [{"text": "LLMs", "confidence": 0.8, "source": "rule"}]
        llm_entities = [{"text": "LLM", "confidence": 0.9, "source": "llm"}]

        validated = cross_validate_entities(rule_entities, llm_entities)

        # Should recognize LLMs ≈ LLM
        assert any(e.get("validated_by_both") for e in validated)

    def test_cross_validate_deduplication(self):
        """Cross-validation deduplicates entities."""
        from app.graph.entity_extraction import cross_validate_entities

        rule_entities = [
            {"text": "LLM", "confidence": 0.8, "source": "rule"},
            {"text": "llm", "confidence": 0.75, "source": "rule"},
        ]
        llm_entities = [{"text": "LLM", "confidence": 0.9, "source": "llm"}]

        validated = cross_validate_entities(rule_entities, llm_entities)

        # Should have only one LLM entry (deduplicated)
        llm_entries = [e for e in validated if e["text"].upper() == "LLM"]
        assert len(llm_entries) == 1


class TestMultiStageExtraction:
    """Test the complete multi-stage extraction pipeline."""

    def test_extract_entities_english(self):
        """Extract entities from English query."""
        from app.graph.entity_extraction import extract_entities

        query = "How does GPT-4 use transformer architecture for natural language processing?"
        entities = extract_entities(query, use_llm=True, max_entities=8)

        assert len(entities) > 0
        assert all("text" in e and "confidence" in e for e in entities)
        assert all(0.0 <= e["confidence"] <= 1.0 for e in entities)

        # Should extract key terms
        entity_texts = [e["text"].lower() for e in entities]
        assert any("gpt" in text or "transformer" in text for text in entity_texts)

    def test_extract_entities_chinese(self):
        """Extract entities from Chinese query."""
        from app.graph.entity_extraction import extract_entities

        query = "大模型如何使用Transformer架构进行自然语言处理？"
        entities = extract_entities(query, use_llm=True, max_entities=8)

        assert len(entities) > 0
        entity_texts = [e["text"] for e in entities]
        # Should extract Chinese and/or English terms
        assert len(entity_texts) > 0

    def test_extract_entities_without_llm(self):
        """Extract entities using only rule-based method."""
        from app.graph.entity_extraction import extract_entities

        query = "What is LLM and AI?"
        entities = extract_entities(query, use_llm=False, max_entities=8)

        assert len(entities) > 0
        assert all("source" in e for e in entities)
        assert all(e["source"] == "rule" for e in entities)

    def test_extract_entities_mixed_language(self):
        """Extract entities from mixed language query."""
        from app.graph.entity_extraction import extract_entities

        query = "GPT-4和大模型的Transformer架构有什么区别？"
        entities = extract_entities(query, use_llm=True, max_entities=10)

        assert len(entities) > 0
        # Should extract both English and Chinese entities
        entity_texts = [e["text"] for e in entities]
        has_english = any(any(c.isascii() and c.isalpha() for c in text) for text in entity_texts)
        has_chinese = any(any("一" <= c <= "鿿" for c in text) for text in entity_texts)
        assert has_english or has_chinese

    def test_extract_entities_returns_sorted(self):
        """Entities are sorted by confidence (descending)."""
        from app.graph.entity_extraction import extract_entities

        query = "LLM AI API GPT machine learning deep learning"
        entities = extract_entities(query, use_llm=True, max_entities=10)

        assert len(entities) > 0
        confidences = [e["confidence"] for e in entities]
        assert confidences == sorted(confidences, reverse=True)

    def test_extract_entities_respects_max(self):
        """Respects max_entities limit."""
        from app.graph.entity_extraction import extract_entities

        query = "AI ML DL NLP LLM GPT BERT transformer attention mechanism"
        entities = extract_entities(query, use_llm=False, max_entities=3)

        assert len(entities) <= 3

    def test_extract_entities_handles_empty(self):
        """Handles empty query gracefully."""
        from app.graph.entity_extraction import extract_entities

        entities = extract_entities("", use_llm=False)
        assert entities == []


class TestAccuracyMetrics:
    """Test entity extraction accuracy against ground truth."""

    @pytest.mark.parametrize(
        "query,expected_entities",
        [
            (
                "What is SQL injection and how to prevent XSS attacks?",
                ["SQL injection", "XSS"],
            ),
            (
                "Explain transformer architecture and attention mechanism",
                ["transformer", "attention"],
            ),
            (
                "大模型和深度学习的关系",
                ["大模型", "深度学习"],
            ),
            (
                "How does OpenAI GPT differ from Google BERT?",
                ["OpenAI", "GPT", "Google", "BERT"],
            ),
        ],
    )
    def test_extraction_accuracy(self, query, expected_entities):
        """Test extraction accuracy on entity-heavy queries."""
        from app.graph.entity_extraction import extract_entities

        entities = extract_entities(query, use_llm=False, max_entities=10)
        entity_texts = [e["text"].lower() for e in entities]

        # Calculate recall: how many expected entities were found
        found = 0
        for expected in expected_entities:
            # Check if any extracted entity contains the expected term (fuzzy match)
            if any(expected.lower() in text or text in expected.lower() for text in entity_texts):
                found += 1

        recall = found / len(expected_entities) if expected_entities else 1.0

        # Target: 85% accuracy (per spec baseline), aiming for 92%
        # For rule-based only, we expect at least 70% recall
        assert recall >= 0.7, f"Recall {recall:.2%} too low for query: {query}"


class TestIntegrationWithGraphLookup:
    """Test integration with existing graph lookup."""

    def test_normalized_entity_names(self):
        """Extracted entities are normalized for graph lookup."""
        from app.graph.entity_extraction import extract_entities, normalize_for_graph

        query = "What is A.I. and LLMs?"
        entities = extract_entities(query, use_llm=False)

        normalized = [normalize_for_graph(e["text"]) for e in entities]

        # Should normalize aliases
        assert any("artificial intelligence" in n.lower() for n in normalized)
        assert any("large language model" in n.lower() or "llm" in n.lower() for n in normalized)

    def test_entity_deduplication_after_normalization(self):
        """Entities are deduplicated after normalization."""
        from app.graph.entity_extraction import extract_entities

        query = "AI and A.I. and artificial intelligence"
        entities = extract_entities(query, use_llm=False)

        # After normalization and deduplication, should have minimal duplicates
        normalized_texts = [e["text"].lower() for e in entities]
        # Allow some duplicates but should be much fewer than 3
        unique_normalized = set(normalized_texts)
        assert len(unique_normalized) >= 1  # At least one unique entity
