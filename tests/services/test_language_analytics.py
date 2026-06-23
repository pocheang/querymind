"""Tests for language analytics service."""

import threading
import time
from datetime import datetime

import pytest

from app.services.language_analytics import LanguageAnalytics


@pytest.fixture
def analytics():
    """Create a fresh analytics instance for each test."""
    # Clear singleton instance
    LanguageAnalytics._instance = None
    instance = LanguageAnalytics.get_instance()
    instance.clear_statistics()
    return instance


class TestLanguageAnalyticsSingleton:
    """Test singleton pattern implementation."""

    def test_singleton_instance(self):
        """Test that get_instance returns the same instance."""
        LanguageAnalytics._instance = None
        instance1 = LanguageAnalytics.get_instance()
        instance2 = LanguageAnalytics.get_instance()
        assert instance1 is instance2

    def test_singleton_thread_safe(self):
        """Test that singleton is thread-safe."""
        LanguageAnalytics._instance = None
        instances = []

        def get_instance():
            instances.append(LanguageAnalytics.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same object
        assert all(inst is instances[0] for inst in instances)


class TestLanguageAnalyticsLogging:
    """Test logging functionality."""

    def test_log_detection_basic(self, analytics):
        """Test basic language detection logging."""
        analytics.log_detection(
            query="What is security?",
            detected_language="en",
            force_language="",
            session_id="session-1",
        )

        stats = analytics.get_statistics()
        assert stats["total_queries"] == 1
        assert stats["language_distribution"]["en"] == 1
        assert stats["forced_vs_auto"]["auto_detected"] == 1
        assert stats["forced_vs_auto"]["forced"] == 0

    def test_log_detection_forced_language(self, analytics):
        """Test logging with forced language."""
        analytics.log_detection(
            query="What is security?",
            detected_language="zh",
            force_language="zh",
            session_id="session-1",
        )

        stats = analytics.get_statistics()
        assert stats["total_queries"] == 1
        assert stats["forced_vs_auto"]["auto_detected"] == 0
        assert stats["forced_vs_auto"]["forced"] == 1

    def test_log_detection_multiple_queries(self, analytics):
        """Test logging multiple queries."""
        analytics.log_detection("Query 1", "en", "", "session-1")
        analytics.log_detection("Query 2", "zh", "", "session-1")
        analytics.log_detection("Query 3", "en", "", "session-2")
        analytics.log_detection("Query 4", "zh", "zh", "session-2")

        stats = analytics.get_statistics()
        assert stats["total_queries"] == 4
        assert stats["language_distribution"]["en"] == 2
        assert stats["language_distribution"]["zh"] == 2
        assert stats["forced_vs_auto"]["auto_detected"] == 3
        assert stats["forced_vs_auto"]["forced"] == 1
        assert stats["session_count"] == 2

    def test_log_detection_query_truncation(self, analytics):
        """Test that long queries are truncated."""
        long_query = "x" * 200
        analytics.log_detection(long_query, "en", "", "session-1")

        stats = analytics.get_statistics()
        event = stats["recent_events"][0]
        assert len(event["query"]) == 100

    def test_log_detection_thread_safe(self, analytics):
        """Test that logging is thread-safe."""

        def log_events():
            for i in range(10):
                analytics.log_detection(
                    query=f"Query {i}",
                    detected_language="en" if i % 2 == 0 else "zh",
                    force_language="",
                    session_id=f"session-{i % 3}",
                )

        threads = [threading.Thread(target=log_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = analytics.get_statistics()
        assert stats["total_queries"] == 50

    def test_log_detection_memory_limit(self, analytics):
        """Test that events are limited to prevent unbounded growth."""
        # Log more than 10,000 events
        for i in range(10500):
            analytics.log_detection(f"Query {i}", "en", "", f"session-{i}")

        stats = analytics.get_statistics()
        # Should keep only last 10,000
        assert stats["total_queries"] == 10000


class TestLanguageAnalyticsStatistics:
    """Test statistics retrieval."""

    def test_get_statistics_empty(self, analytics):
        """Test statistics when no events logged."""
        stats = analytics.get_statistics()
        assert stats["total_queries"] == 0
        assert stats["language_distribution"] == {}
        assert stats["forced_vs_auto"]["auto_detected"] == 0
        assert stats["forced_vs_auto"]["forced"] == 0
        assert stats["session_count"] == 0
        assert stats["recent_events"] == []

    def test_get_statistics_language_distribution(self, analytics):
        """Test language distribution calculation."""
        analytics.log_detection("Q1", "en", "", "s1")
        analytics.log_detection("Q2", "en", "", "s1")
        analytics.log_detection("Q3", "zh", "", "s1")
        analytics.log_detection("Q4", "zh", "", "s1")
        analytics.log_detection("Q5", "zh", "", "s1")

        stats = analytics.get_statistics()
        assert stats["language_distribution"]["en"] == 2
        assert stats["language_distribution"]["zh"] == 3

    def test_get_statistics_recent_events(self, analytics):
        """Test recent events are returned in reverse order."""
        for i in range(150):
            analytics.log_detection(f"Query {i}", "en", "", "session-1")

        stats = analytics.get_statistics()
        # Should return last 100 events, most recent first
        assert len(stats["recent_events"]) == 100
        assert stats["recent_events"][0]["query"] == "Query 149"
        assert stats["recent_events"][-1]["query"] == "Query 50"

    def test_get_statistics_session_count(self, analytics):
        """Test unique session counting."""
        analytics.log_detection("Q1", "en", "", "session-1")
        analytics.log_detection("Q2", "en", "", "session-1")
        analytics.log_detection("Q3", "en", "", "session-2")
        analytics.log_detection("Q4", "en", "", "session-3")
        analytics.log_detection("Q5", "en", "", "")  # Empty session

        stats = analytics.get_statistics()
        # Should count unique non-empty sessions
        assert stats["session_count"] == 3


class TestLanguageAnalyticsSessionStatistics:
    """Test session-specific statistics."""

    def test_get_session_statistics_empty(self, analytics):
        """Test session statistics when session has no events."""
        stats = analytics.get_session_statistics("session-1")
        assert stats["session_id"] == "session-1"
        assert stats["total_queries"] == 0
        assert stats["language_distribution"] == {}
        assert stats["events"] == []

    def test_get_session_statistics_single_session(self, analytics):
        """Test statistics for a single session."""
        analytics.log_detection("Q1", "en", "", "session-1")
        analytics.log_detection("Q2", "zh", "", "session-1")
        analytics.log_detection("Q3", "en", "en", "session-1")
        analytics.log_detection("Q4", "zh", "", "session-2")  # Different session

        stats = analytics.get_session_statistics("session-1")
        assert stats["session_id"] == "session-1"
        assert stats["total_queries"] == 3
        assert stats["language_distribution"]["en"] == 2
        assert stats["language_distribution"]["zh"] == 1
        assert stats["forced_vs_auto"]["auto_detected"] == 2
        assert stats["forced_vs_auto"]["forced"] == 1
        assert len(stats["events"]) == 3

    def test_get_session_statistics_events_order(self, analytics):
        """Test that session events are returned in reverse order."""
        analytics.log_detection("Q1", "en", "", "session-1")
        time.sleep(0.01)  # Ensure different timestamps
        analytics.log_detection("Q2", "zh", "", "session-1")
        time.sleep(0.01)
        analytics.log_detection("Q3", "en", "", "session-1")

        stats = analytics.get_session_statistics("session-1")
        # Most recent first
        assert stats["events"][0]["query"] == "Q3"
        assert stats["events"][1]["query"] == "Q2"
        assert stats["events"][2]["query"] == "Q1"


class TestLanguageAnalyticsClear:
    """Test clearing statistics."""

    def test_clear_statistics(self, analytics):
        """Test that clear removes all events."""
        analytics.log_detection("Q1", "en", "", "session-1")
        analytics.log_detection("Q2", "zh", "", "session-2")

        stats_before = analytics.get_statistics()
        assert stats_before["total_queries"] == 2

        analytics.clear_statistics()

        stats_after = analytics.get_statistics()
        assert stats_after["total_queries"] == 0
        assert stats_after["language_distribution"] == {}
        assert stats_after["recent_events"] == []


class TestLanguageAnalyticsEventStructure:
    """Test event data structure."""

    def test_event_structure(self, analytics):
        """Test that logged events have correct structure."""
        analytics.log_detection(
            query="Test query",
            detected_language="en",
            force_language="",
            session_id="session-1",
        )

        stats = analytics.get_statistics()
        event = stats["recent_events"][0]

        assert "timestamp" in event
        assert "query" in event
        assert "detected_language" in event
        assert "force_language" in event
        assert "was_forced" in event
        assert "session_id" in event

        assert event["query"] == "Test query"
        assert event["detected_language"] == "en"
        assert event["force_language"] == ""
        assert event["was_forced"] is False
        assert event["session_id"] == "session-1"

    def test_event_timestamp_format(self, analytics):
        """Test that timestamps are in ISO format."""
        analytics.log_detection("Q1", "en", "", "session-1")

        stats = analytics.get_statistics()
        event = stats["recent_events"][0]

        # Should be parseable as ISO format
        timestamp = datetime.fromisoformat(event["timestamp"])
        assert isinstance(timestamp, datetime)
