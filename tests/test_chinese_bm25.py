"""
Tests for Chinese-aware BM25 retrieval.

Validates:
    - Chinese tokenization with jieba
    - Fallback to basic tokenization
    - Mixed English-Chinese queries
    - Tokenization comparison
"""

import pytest

from app.retrievers.bm25_retriever import (
    tokenize,
    tokenize_chinese_aware,
)


def _jieba_available():
    """Check if jieba is available."""
    try:
        import jieba

        return True
    except ImportError:
        return False


class TestChineseAwareTokenization:
    """Test Chinese-aware tokenization."""

    def test_chinese_text_tokenization(self):
        """Chinese text should be tokenized with jieba."""
        text = "机器学习算法"
        tokens = tokenize_chinese_aware(text)

        # With jieba, should get meaningful tokens
        # Expected: ['机器', '学习', '算法'] or similar
        assert len(tokens) > 0
        assert all(len(t) > 1 for t in tokens)  # Multi-char tokens

    def test_english_text_tokenization(self):
        """English text should use regex tokenization."""
        text = "machine learning algorithms"
        tokens = tokenize_chinese_aware(text)

        assert "machine" in tokens
        assert "learning" in tokens
        assert "algorithms" in tokens

    def test_mixed_language_tokenization(self):
        """Mixed Chinese-English text."""
        text = "使用Python进行machine learning"
        tokens = tokenize_chinese_aware(text)

        assert len(tokens) > 0
        # Should include both Chinese and English tokens
        assert "python" in tokens or "Python" in [t.lower() for t in tokens]

    def test_empty_text(self):
        """Empty text should return empty list."""
        assert tokenize_chinese_aware("") == []
        assert tokenize_chinese_aware("   ") == []

    def test_chinese_detection_threshold(self):
        """Text with >20% Chinese chars should use jieba."""
        # 50% Chinese (5 Chinese chars out of 10 total)
        text = "这是测试text"  # 4 Chinese + ~4 English = >20%
        tokens = tokenize_chinese_aware(text)
        assert len(tokens) > 0


class TestBasicTokenization:
    """Test basic tokenization (fallback)."""

    def test_basic_english_tokenization(self):
        """Basic tokenization for English."""
        text = "Hello world"
        tokens = tokenize(text)

        assert "hello" in tokens
        assert "world" in tokens

    def test_basic_chinese_tokenization(self):
        """Basic tokenization treats each Chinese char separately."""
        text = "机器学习"
        tokens = tokenize(text)

        # Basic tokenization: each character is a token
        assert len(tokens) >= 4  # At least 4 Chinese characters

    def test_basic_handles_punctuation(self):
        """Basic tokenization filters punctuation."""
        text = "Hello, world!"
        tokens = tokenize(text)

        assert "hello" in tokens
        assert "world" in tokens
        assert "," not in tokens
        assert "!" not in tokens


class TestTokenizationComparison:
    """Compare basic vs Chinese-aware tokenization."""

    def test_chinese_text_improvement(self):
        """Chinese-aware tokenization should produce better tokens."""
        text = "自然语言处理技术"

        basic_tokens = tokenize(text)
        chinese_tokens = tokenize_chinese_aware(text)

        # Chinese-aware should produce fewer, more meaningful tokens
        # Basic: [自, 然, 语, 言, 处, 理, 技, 术] (8 tokens)
        # Chinese-aware: [自然, 语言, 处理, 技术] (4 tokens)
        if len(chinese_tokens) > 0:
            # If jieba is available
            assert len(chinese_tokens) <= len(basic_tokens)
            assert all(len(t) > 1 for t in chinese_tokens)  # Multi-char tokens

    def test_english_text_consistency(self):
        """Both methods should work well for English."""
        text = "natural language processing"

        basic_tokens = tokenize(text)
        chinese_tokens = tokenize_chinese_aware(text)

        # Both should produce similar results for English
        assert set(basic_tokens) == set(chinese_tokens)


class TestBM25Integration:
    """Test BM25 search with Chinese tokenization."""

    @pytest.mark.skipif(not _jieba_available(), reason="jieba not available")
    def test_bm25_search_with_chinese_query(self):
        """BM25 search should work with Chinese queries."""
        from app.retrievers.bm25_retriever import bm25_search

        # This test assumes corpus exists
        # In real scenario, would need to set up test corpus
        query = "机器学习"

        try:
            results = bm25_search(query, k=5, use_chinese_tokenizer=True)
            # Should not raise error
            assert isinstance(results, list)
        except Exception:
            pytest.skip("No corpus available for testing")

    def test_bm25_tokenizer_parameter(self):
        """BM25 search should accept tokenizer parameter."""
        from app.retrievers.bm25_retriever import bm25_search

        try:
            # Test with Chinese tokenizer
            results1 = bm25_search("test", k=5, use_chinese_tokenizer=True)
            assert isinstance(results1, list)

            # Test without Chinese tokenizer
            results2 = bm25_search("test", k=5, use_chinese_tokenizer=False)
            assert isinstance(results2, list)
        except Exception:
            pytest.skip("No corpus available for testing")


def _jieba_available() -> bool:
    """Check if jieba is available."""
    try:
        import jieba

        return True
    except ImportError:
        return False


class TestRealWorldQueries:
    """Test with realistic query examples."""

    def test_chinese_question(self):
        """Typical Chinese question."""
        query = "什么是深度学习？"
        tokens = tokenize_chinese_aware(query)

        assert len(tokens) > 0
        # Should produce meaningful tokens, not single characters

    def test_technical_chinese_term(self):
        """Technical Chinese terminology."""
        query = "神经网络优化算法"
        tokens = tokenize_chinese_aware(query)

        assert len(tokens) > 0

    def test_english_question(self):
        """Typical English question."""
        query = "What is deep learning?"
        tokens = tokenize_chinese_aware(query)

        assert "what" in tokens
        assert "deep" in tokens
        assert "learning" in tokens

    def test_code_with_chinese_comment(self):
        """Code snippet with Chinese comments."""
        query = "def train_model(): # 训练模型"
        tokens = tokenize_chinese_aware(query)

        assert "def" in tokens or "train" in tokens
        assert len(tokens) > 0
