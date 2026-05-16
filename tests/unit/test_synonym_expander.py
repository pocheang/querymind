"""Unit tests for synonym expander service."""

import pytest
from app.services.synonym_expander import SynonymExpander, get_expander


class TestSynonymExpander:
    """Test cases for SynonymExpander."""

    def test_get_synonyms(self):
        """Test getting synonyms for a word."""
        expander = SynonymExpander()
        synonyms = expander.get_synonyms("人工智能")

        assert isinstance(synonyms, set)
        assert len(synonyms) > 0
        # Should contain related terms
        assert any(syn in synonyms for syn in ["AI", "机器学习", "深度学习"])

    def test_get_synonyms_not_found(self):
        """Test getting synonyms for unknown word."""
        expander = SynonymExpander()
        synonyms = expander.get_synonyms("不存在的词语")

        assert synonyms == set()

    def test_add_synonym_group(self):
        """Test adding custom synonym group."""
        expander = SynonymExpander()
        expander.add_synonym_group("测试", {"test", "检验", "验证"})

        synonyms = expander.get_synonyms("测试")
        assert "test" in synonyms
        assert "检验" in synonyms
        assert "验证" in synonyms

    def test_expand_query(self):
        """Test query expansion with synonyms."""
        expander = SynonymExpander()
        tokens = ["人工智能", "应用"]
        expanded = expander.expand_query(tokens, max_expansions=2)

        # Should contain original tokens
        assert "人工智能" in expanded
        assert "应用" in expanded

        # Should contain some synonyms
        assert len(expanded) > len(tokens)

    def test_expand_query_no_synonyms(self):
        """Test query expansion when no synonyms found."""
        expander = SynonymExpander()
        tokens = ["未知词汇", "另一个未知词"]
        expanded = expander.expand_query(tokens, max_expansions=2)

        # Should return original tokens
        assert expanded == tokens

    def test_expand_query_string_append(self):
        """Test query string expansion with append strategy."""
        expander = SynonymExpander()
        query = "人工智能 应用"
        tokens = ["人工智能", "应用"]

        expanded = expander.expand_query_string(query, tokens, strategy="append")

        assert isinstance(expanded, str)
        assert "人工智能" in expanded
        assert "应用" in expanded
        # Should be longer than original
        assert len(expanded) >= len(query)

    def test_expand_query_string_replace(self):
        """Test query string expansion with replace strategy."""
        expander = SynonymExpander()
        query = "数据库 优化"
        tokens = ["数据库", "优化"]

        expanded = expander.expand_query_string(query, tokens, strategy="replace")

        assert isinstance(expanded, str)
        # Should contain OR clauses
        assert "OR" in expanded or "数据库" in expanded

    def test_expand_query_max_expansions(self):
        """Test that max_expansions is respected."""
        expander = SynonymExpander()
        tokens = ["人工智能"]

        expanded_1 = expander.expand_query(tokens, max_expansions=1)
        expanded_2 = expander.expand_query(tokens, max_expansions=2)

        # With more expansions allowed, should get more or equal tokens
        assert len(expanded_2) >= len(expanded_1)

    def test_default_synonyms_loaded(self):
        """Test that default synonyms are loaded."""
        expander = SynonymExpander()

        # Check some default synonym groups exist
        assert len(expander.synonyms) > 0
        assert "人工智能" in expander.synonyms
        assert "数据库" in expander.synonyms
        assert "员工" in expander.synonyms

    def test_get_expander_singleton(self):
        """Test that get_expander returns singleton instance."""
        expander1 = get_expander()
        expander2 = get_expander()

        assert expander1 is expander2
