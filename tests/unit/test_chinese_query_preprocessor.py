"""Unit tests for Chinese query preprocessor."""

from app.services.chinese_query_preprocessor import ChineseQueryPreprocessor, get_preprocessor


class TestChineseQueryPreprocessor:
    """Test cases for ChineseQueryPreprocessor."""

    def test_detect_language_chinese(self):
        """Test Chinese language detection."""
        preprocessor = ChineseQueryPreprocessor()
        result = preprocessor.detect_language("这是一个中文查询")

        assert result == "chinese"

    def test_detect_language_english(self):
        """Test English language detection."""
        preprocessor = ChineseQueryPreprocessor()
        result = preprocessor.detect_language("This is an English query")

        assert result == "english"

    def test_detect_language_mixed(self):
        """Test mixed language detection."""
        preprocessor = ChineseQueryPreprocessor()
        result = preprocessor.detect_language("使用Python开发应用")

        assert result == "mixed"

    def test_normalize_text(self):
        """Test text normalization."""
        preprocessor = ChineseQueryPreprocessor()
        text = "这是　　一个  测试"  # Contains full-width and multiple spaces
        normalized = preprocessor.normalize_text(text)

        assert "　" not in normalized  # Full-width space removed
        assert "  " not in normalized  # Multiple spaces normalized

    def test_remove_stopwords(self):
        """Test stopword removal."""
        preprocessor = ChineseQueryPreprocessor()
        tokens = ["我", "想", "了解", "人工智能", "的", "应用"]
        filtered = preprocessor.remove_stopwords(tokens)

        # Common stopwords should be removed
        assert "的" not in filtered
        # Content words should remain
        assert "人工智能" in filtered or "了解" in filtered

    def test_remove_stopwords_keeps_one_token(self):
        """Test that at least one token is kept even if all are stopwords."""
        preprocessor = ChineseQueryPreprocessor()
        tokens = ["的", "了", "在"]
        filtered = preprocessor.remove_stopwords(tokens)

        # Should keep at least one token
        assert len(filtered) >= 1

    def test_preprocess_chinese_query(self):
        """Test preprocessing a Chinese query."""
        preprocessor = ChineseQueryPreprocessor()
        query = "我想了解人工智能的应用"
        processed = preprocessor.preprocess(query, expand_synonyms=False)

        assert isinstance(processed, str)
        assert len(processed) > 0
        # Stopwords should be removed
        assert "的" not in processed

    def test_preprocess_with_synonym_expansion(self):
        """Test preprocessing with synonym expansion."""
        preprocessor = ChineseQueryPreprocessor()
        query = "人工智能应用"
        processed = preprocessor.preprocess(query, expand_synonyms=True)

        # With expansion, result should be longer
        processed_no_expansion = preprocessor.preprocess(query, expand_synonyms=False)
        assert len(processed) >= len(processed_no_expansion)

    def test_preprocess_with_metadata(self):
        """Test preprocessing with metadata return."""
        preprocessor = ChineseQueryPreprocessor()
        query = "数据库优化方法"
        result = preprocessor.preprocess(query, return_metadata=True)

        assert isinstance(result, dict)
        assert "processed_query" in result
        assert "original_query" in result
        assert "tokens" in result
        assert "language" in result
        assert result["language"] == "chinese"

    def test_preprocess_empty_query(self):
        """Test preprocessing empty query."""
        preprocessor = ChineseQueryPreprocessor()
        processed = preprocessor.preprocess("")

        assert processed == ""

    def test_preprocess_english_query(self):
        """Test preprocessing English query."""
        preprocessor = ChineseQueryPreprocessor()
        query = "machine learning applications"
        processed = preprocessor.preprocess(query, expand_synonyms=False)

        assert isinstance(processed, str)
        assert len(processed) > 0

    def test_extract_keywords(self):
        """Test keyword extraction from query."""
        preprocessor = ChineseQueryPreprocessor()
        query = "如何使用Python开发人工智能应用"
        keywords = preprocessor.extract_keywords(query, topK=3)

        assert len(keywords) <= 3
        assert len(keywords) > 0
        # Should extract meaningful terms
        assert any(kw in ["Python", "人工智能", "应用", "开发"] for kw in keywords)

    def test_add_stopword(self):
        """Test adding custom stopword."""
        preprocessor = ChineseQueryPreprocessor()
        preprocessor.add_stopword("测试词")

        tokens = ["这是", "测试词", "内容"]
        filtered = preprocessor.remove_stopwords(tokens)

        assert "测试词" not in filtered

    def test_remove_stopword(self):
        """Test removing word from stopwords."""
        preprocessor = ChineseQueryPreprocessor()
        preprocessor.remove_stopword("的")

        tokens = ["这是", "的", "内容"]
        filtered = preprocessor.remove_stopwords(tokens)

        # "的" should now be kept
        assert "的" in filtered

    def test_get_preprocessor_singleton(self):
        """Test that get_preprocessor returns singleton instance."""
        preprocessor1 = get_preprocessor()
        preprocessor2 = get_preprocessor()

        assert preprocessor1 is preprocessor2
