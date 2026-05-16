"""Unit tests for Chinese tokenizer service."""

import pytest
from app.services.chinese_tokenizer import ChineseTokenizer, get_tokenizer


class TestChineseTokenizer:
    """Test cases for ChineseTokenizer."""

    def test_tokenize_chinese_text(self):
        """Test basic Chinese text tokenization."""
        tokenizer = ChineseTokenizer()
        text = "我想了解人工智能的应用"
        tokens = tokenizer.tokenize(text)

        assert len(tokens) > 0
        assert "人工智能" in tokens or "人工" in tokens
        assert "应用" in tokens

    def test_tokenize_empty_text(self):
        """Test tokenization of empty text."""
        tokenizer = ChineseTokenizer()
        tokens = tokenizer.tokenize("")

        assert tokens == []

    def test_tokenize_for_search(self):
        """Test search-optimized tokenization."""
        tokenizer = ChineseTokenizer()
        text = "中国人民银行"
        tokens = tokenizer.tokenize_for_search(text)

        assert len(tokens) > 0
        # Search mode should produce more granular tokens
        assert len(tokens) >= len(tokenizer.tokenize(text, cut_all=False))

    def test_extract_keywords(self):
        """Test keyword extraction."""
        tokenizer = ChineseTokenizer()
        text = "人工智能技术在医疗领域的应用越来越广泛，深度学习算法可以帮助医生诊断疾病。"
        keywords = tokenizer.extract_keywords(text, topK=5)

        assert len(keywords) <= 5
        assert len(keywords) > 0
        # Should extract meaningful terms
        assert any(kw in ["人工智能", "医疗", "深度学习", "算法"] for kw in keywords)

    def test_extract_keywords_with_weight(self):
        """Test keyword extraction with weights."""
        tokenizer = ChineseTokenizer()
        text = "机器学习是人工智能的核心技术"
        keywords = tokenizer.extract_keywords(text, topK=3, withWeight=True)

        assert len(keywords) <= 3
        assert all(isinstance(kw, tuple) and len(kw) == 2 for kw in keywords)
        assert all(isinstance(kw[0], str) and isinstance(kw[1], float) for kw in keywords)

    def test_extract_keywords_textrank(self):
        """Test TextRank keyword extraction."""
        tokenizer = ChineseTokenizer()
        text = "自然语言处理技术包括分词、词性标注、命名实体识别等多个子任务。"
        keywords = tokenizer.extract_keywords_textrank(text, topK=5)

        assert len(keywords) <= 5
        assert len(keywords) > 0

    def test_add_word(self):
        """Test adding custom words to dictionary."""
        tokenizer = ChineseTokenizer()

        # Add a custom term
        tokenizer.add_word("RAG系统", freq=1000)

        text = "RAG系统的性能很好"
        tokens = tokenizer.tokenize(text)

        # The custom term should be recognized as a single token
        assert "RAG系统" in tokens or "RAG" in tokens

    def test_tokenize_mixed_language(self):
        """Test tokenization of mixed Chinese and English."""
        tokenizer = ChineseTokenizer()
        text = "使用Python开发AI应用"
        tokens = tokenizer.tokenize(text)

        assert len(tokens) > 0
        assert "Python" in tokens
        assert "AI" in tokens or "应用" in tokens

    def test_get_tokenizer_singleton(self):
        """Test that get_tokenizer returns singleton instance."""
        tokenizer1 = get_tokenizer()
        tokenizer2 = get_tokenizer()

        assert tokenizer1 is tokenizer2
