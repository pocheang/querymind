"""
Tests for adaptive caching strategy.

Validates:
    - Tier-based TTL calculation
    - User-specific query detection
    - Chinese query pattern matching
    - Real-time query detection
"""

from app.retrievers.hybrid.adaptive_cache import (
    DEFAULT_CACHE_TTL_BALANCED_TIER,
    DEFAULT_CACHE_TTL_DEEP_TIER,
    DEFAULT_CACHE_TTL_FAST_TIER,
    DEFAULT_CACHE_TTL_USER_QUERY,
    _is_user_specific_query,
    get_adaptive_cache_ttl,
    should_skip_cache,
)


class TestTierBasedTTL:
    """Test tier-based cache TTL calculation."""

    def test_fast_tier_ttl(self):
        """Fast tier should have longest TTL."""
        ttl = get_adaptive_cache_ttl("What is AI?", tier="fast")
        assert ttl == DEFAULT_CACHE_TTL_FAST_TIER
        assert ttl == 300  # 5 minutes

    def test_balanced_tier_ttl(self):
        """Balanced tier should have medium TTL."""
        ttl = get_adaptive_cache_ttl("Explain machine learning", tier="balanced")
        assert ttl == DEFAULT_CACHE_TTL_BALANCED_TIER
        assert ttl == 120  # 2 minutes

    def test_deep_tier_ttl(self):
        """Deep tier should have shortest TTL."""
        ttl = get_adaptive_cache_ttl("Analyze market trends", tier="deep")
        assert ttl == DEFAULT_CACHE_TTL_DEEP_TIER
        assert ttl == 60  # 1 minute

    def test_default_tier(self):
        """No tier specified should default to balanced."""
        ttl = get_adaptive_cache_ttl("Random query")
        assert ttl == DEFAULT_CACHE_TTL_BALANCED_TIER


class TestUserSpecificQueries:
    """Test user-specific query detection."""

    def test_english_possessive_patterns(self):
        """Detect English possessive pronouns."""
        assert _is_user_specific_query("Show me my documents")
        assert _is_user_specific_query("Where are my files?")
        assert _is_user_specific_query("Our team's reports")
        assert _is_user_specific_query("I need help")

    def test_chinese_possessive_patterns(self):
        """Detect Chinese possessive patterns."""
        assert _is_user_specific_query("我的文档在哪里")
        assert _is_user_specific_query("给我最新的报告")
        assert _is_user_specific_query("帮我找到相关资料")
        assert _is_user_specific_query("我们的项目文件")

    def test_non_user_specific_queries(self):
        """Generic queries should not be detected as user-specific."""
        assert not _is_user_specific_query("What is Python?")
        assert not _is_user_specific_query("Explain quantum computing")
        assert not _is_user_specific_query("什么是人工智能")
        assert not _is_user_specific_query("机器学习算法介绍")

    def test_user_specific_ttl_override(self):
        """User-specific queries should use special TTL regardless of tier."""
        # Even with fast tier, user-specific query uses USER_QUERY TTL
        ttl = get_adaptive_cache_ttl("Show me my documents", tier="fast", user_id="user123")
        assert ttl == DEFAULT_CACHE_TTL_USER_QUERY
        assert ttl == 180  # 3 minutes


class TestRealtimeQueryDetection:
    """Test real-time query cache skipping."""

    def test_english_realtime_patterns(self):
        """Detect English real-time keywords."""
        assert should_skip_cache("What's the latest news?")
        assert should_skip_cache("Show me current stock prices")
        assert should_skip_cache("Get real-time data")
        assert should_skip_cache("What's happening now?")
        assert should_skip_cache("Today's weather")

    def test_chinese_realtime_patterns(self):
        """Detect Chinese real-time keywords."""
        assert should_skip_cache("最新的消息是什么")
        assert should_skip_cache("现在的天气怎么样")
        assert should_skip_cache("今天的新闻")
        assert should_skip_cache("当前的股票价格")
        assert should_skip_cache("实时数据")

    def test_force_refresh_flag(self):
        """Force refresh should skip cache."""
        assert should_skip_cache("Any query", force_refresh=True)

    def test_cacheable_queries(self):
        """Historical or static queries should be cacheable."""
        assert not should_skip_cache("What is AI?")
        assert not should_skip_cache("History of computing")
        assert not should_skip_cache("什么是人工智能")


class TestCustomSettings:
    """Test custom TTL settings override."""

    def test_custom_settings_override(self):
        """Custom settings should override defaults."""

        # Mock settings object
        class MockSettings:
            cache_ttl_fast_tier = 600  # 10 minutes
            cache_ttl_balanced_tier = 240  # 4 minutes
            cache_ttl_deep_tier = 90  # 1.5 minutes
            cache_ttl_user_query = 360  # 6 minutes

        settings = MockSettings()

        assert get_adaptive_cache_ttl("query", tier="fast", settings=settings) == 600
        assert get_adaptive_cache_ttl("query", tier="balanced", settings=settings) == 240
        assert get_adaptive_cache_ttl("query", tier="deep", settings=settings) == 90
        assert get_adaptive_cache_ttl("my files", user_id="u1", settings=settings) == 360


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_query(self):
        """Empty query should not cause errors."""
        ttl = get_adaptive_cache_ttl("")
        assert ttl == DEFAULT_CACHE_TTL_BALANCED_TIER

    def test_none_tier(self):
        """None tier should use balanced default."""
        ttl = get_adaptive_cache_ttl("query", tier=None)
        assert ttl == DEFAULT_CACHE_TTL_BALANCED_TIER

    def test_case_insensitive_tier(self):
        """Tier matching should be case-insensitive."""
        ttl1 = get_adaptive_cache_ttl("query", tier="FAST")
        ttl2 = get_adaptive_cache_ttl("query", tier="Fast")
        ttl3 = get_adaptive_cache_ttl("query", tier="fast")
        assert ttl1 == ttl2 == ttl3 == DEFAULT_CACHE_TTL_FAST_TIER

    def test_mixed_language_query(self):
        """Query with both English and Chinese."""
        query = "What is 机器学习 (machine learning)?"
        # Should not be detected as user-specific
        assert not _is_user_specific_query(query)

    def test_user_specific_mixed_language(self):
        """User-specific query with mixed language."""
        query = "Show me my 文档"
        assert _is_user_specific_query(query)
