import json
import csv
import io
import threading
import time
from datetime import datetime, timezone
from typing import Any

import pytest

from app.services.retrieval_logger import (
    RetrievalLog,
    AnalyticsOverview,
    AgentStats,
    DocumentStats,
    RetrievalLogger,
)


def utcnow():
    """Helper to get current UTC time."""
    return datetime.now(timezone.utc)


class TestRetrievalLogModel:
    """Test RetrievalLog data model."""

    def test_retrieval_log_creation(self):
        """Test that RetrievalLog can be instantiated with all required fields."""
        log = RetrievalLog(
            log_id="test-123",
            timestamp=utcnow(),
            question="What is cybersecurity?",
            agent_class="cybersecurity",
            route="vector",
            filtered_docs_count=50,
            retrieved_count=10,
            effective_hit_count=8,
            top_scores=[0.95, 0.87, 0.76],
            retrieval_time_ms=45.2,
            total_time_ms=120.5,
            retrieved_sources=["doc1.md", "doc2.md"],
            has_result=True,
            error=None,
        )

        assert log.log_id == "test-123"
        assert log.question == "What is cybersecurity?"
        assert log.agent_class == "cybersecurity"
        assert log.route == "vector"
        assert log.filtered_docs_count == 50
        assert log.retrieved_count == 10
        assert log.effective_hit_count == 8
        assert len(log.top_scores) == 3
        assert log.retrieval_time_ms == 45.2
        assert log.total_time_ms == 120.5
        assert len(log.retrieved_sources) == 2
        assert log.has_result is True
        assert log.error is None

    def test_retrieval_log_with_error(self):
        """Test RetrievalLog with error field populated."""
        log = RetrievalLog(
            log_id="test-456",
            timestamp=utcnow(),
            question="Test question",
            agent_class="general",
            route="graph",
            filtered_docs_count=0,
            retrieved_count=0,
            effective_hit_count=0,
            top_scores=[],
            retrieval_time_ms=10.0,
            total_time_ms=15.0,
            retrieved_sources=[],
            has_result=False,
            error="Connection timeout",
        )

        assert log.has_result is False
        assert log.error == "Connection timeout"


class TestRetrievalLoggerSingleton:
    """Test RetrievalLogger singleton pattern."""

    def test_retrieval_logger_singleton(self):
        """Test that RetrievalLogger follows singleton pattern."""
        logger1 = RetrievalLogger.get_instance()
        logger2 = RetrievalLogger.get_instance()

        assert logger1 is logger2

    def test_singleton_thread_safety(self):
        """Test that singleton is thread-safe."""
        instances = []

        def get_instance():
            instances.append(RetrievalLogger.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same object
        assert all(inst is instances[0] for inst in instances)


class TestRetrievalLoggerLogging:
    """Test logging functionality."""

    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset logger state before each test."""
        logger = RetrievalLogger.get_instance()
        logger._logs.clear()
        yield

    def test_log_retrieval(self):
        """Test logging a retrieval event."""
        logger = RetrievalLogger.get_instance()

        log = RetrievalLog(
            log_id="log-1",
            timestamp=utcnow(),
            question="Test question",
            agent_class="cybersecurity",
            route="vector",
            filtered_docs_count=100,
            retrieved_count=10,
            effective_hit_count=8,
            top_scores=[0.9, 0.8, 0.7],
            retrieval_time_ms=50.0,
            total_time_ms=150.0,
            retrieved_sources=["doc1.md"],
            has_result=True,
        )

        logger.log_retrieval(log)

        # Verify log was stored
        assert len(logger._logs) == 1
        assert logger._logs[0].log_id == "log-1"

    def test_log_retrieval_thread_safety(self):
        """Test that logging is thread-safe."""
        logger = RetrievalLogger.get_instance()

        def log_entry(i: int):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question=f"Question {i}",
                agent_class="general",
                route="vector",
                filtered_docs_count=10,
                retrieved_count=5,
                effective_hit_count=3,
                top_scores=[0.8],
                retrieval_time_ms=10.0,
                total_time_ms=20.0,
                retrieved_sources=[],
                has_result=True,
            )
            logger.log_retrieval(log)

        threads = [threading.Thread(target=log_entry, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All logs should be recorded
        assert len(logger._logs) == 50

    def test_log_deque_max_size(self):
        """Test that deque respects maxlen=1000."""
        logger = RetrievalLogger.get_instance()

        # Add 1100 logs
        for i in range(1100):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question=f"Question {i}",
                agent_class="general",
                route="vector",
                filtered_docs_count=10,
                retrieved_count=5,
                effective_hit_count=3,
                top_scores=[0.8],
                retrieval_time_ms=10.0,
                total_time_ms=20.0,
                retrieved_sources=[],
                has_result=True,
            )
            logger.log_retrieval(log)

        # Should only keep last 1000
        assert len(logger._logs) == 1000
        # First log should be log-100 (0-99 were dropped)
        assert logger._logs[0].log_id == "log-100"


class TestAnalyticsOverview:
    """Test analytics overview functionality."""

    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset logger state before each test."""
        logger = RetrievalLogger.get_instance()
        logger._logs.clear()
        yield

    def test_get_overview_empty(self):
        """Test get_overview with no data."""
        logger = RetrievalLogger.get_instance()
        overview = logger.get_overview()

        assert overview.total_queries == 0
        assert overview.success_rate == 0.0
        assert overview.avg_retrieval_time_ms == 0.0
        assert overview.avg_total_time_ms == 0.0
        assert overview.avg_retrieved_count == 0.0
        assert overview.avg_effective_hit_count == 0.0
        assert overview.agent_distribution == {}
        assert overview.route_distribution == {}
        assert overview.time_range_start is None
        assert overview.time_range_end is None

    def test_get_overview_with_data(self):
        """Test get_overview with sample data."""
        logger = RetrievalLogger.get_instance()

        # Add 10 logs: 8 successful, 2 failed
        for i in range(8):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question=f"Question {i}",
                agent_class="cybersecurity" if i < 5 else "artificial_intelligence",
                route="vector" if i < 6 else "graph",
                filtered_docs_count=100,
                retrieved_count=10,
                effective_hit_count=8,
                top_scores=[0.9, 0.8, 0.7],
                retrieval_time_ms=50.0,
                total_time_ms=150.0,
                retrieved_sources=["doc1.md"],
                has_result=True,
            )
            logger.log_retrieval(log)

        for i in range(8, 10):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question=f"Question {i}",
                agent_class="general",
                route="web",
                filtered_docs_count=0,
                retrieved_count=0,
                effective_hit_count=0,
                top_scores=[],
                retrieval_time_ms=10.0,
                total_time_ms=20.0,
                retrieved_sources=[],
                has_result=False,
                error="No results",
            )
            logger.log_retrieval(log)

        overview = logger.get_overview()

        assert overview.total_queries == 10
        assert overview.success_rate == 80.0  # 8/10 * 100
        assert overview.avg_retrieval_time_ms == 42.0  # (50*8 + 10*2) / 10
        assert overview.avg_total_time_ms == 124.0  # (150*8 + 20*2) / 10
        assert overview.avg_retrieved_count == 8.0  # (10*8 + 0*2) / 10
        assert overview.avg_effective_hit_count == 6.4  # (8*8 + 0*2) / 10

        assert overview.agent_distribution == {
            "cybersecurity": 5,
            "artificial_intelligence": 3,
            "general": 2,
        }
        assert overview.route_distribution == {
            "vector": 6,
            "graph": 2,
            "web": 2,
        }

        assert overview.time_range_start is not None
        assert overview.time_range_end is not None


class TestAgentStats:
    """Test agent statistics functionality."""

    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset logger state before each test."""
        logger = RetrievalLogger.get_instance()
        logger._logs.clear()
        yield

    def test_get_agent_stats_empty(self):
        """Test get_agent_stats with no data."""
        logger = RetrievalLogger.get_instance()
        stats = logger.get_agent_stats()

        assert stats == []

    def test_get_agent_stats(self):
        """Test get_agent_stats with sample data."""
        logger = RetrievalLogger.get_instance()

        # Add logs for different agents
        # Cybersecurity: 5 queries, 4 successful
        for i in range(5):
            log = RetrievalLog(
                log_id=f"cyber-{i}",
                timestamp=utcnow(),
                question=f"Cyber question {i}",
                agent_class="cybersecurity",
                route="vector",
                filtered_docs_count=100,
                retrieved_count=10,
                effective_hit_count=8,
                top_scores=[0.95, 0.85, 0.75],
                retrieval_time_ms=50.0,
                total_time_ms=150.0,
                retrieved_sources=["doc1.md"],
                has_result=(i < 4),  # First 4 successful
            )
            logger.log_retrieval(log)

        # AI: 3 queries, all successful
        for i in range(3):
            log = RetrievalLog(
                log_id=f"ai-{i}",
                timestamp=utcnow(),
                question=f"AI question {i}",
                agent_class="artificial_intelligence",
                route="graph",
                filtered_docs_count=80,
                retrieved_count=8,
                effective_hit_count=6,
                top_scores=[0.88, 0.78],
                retrieval_time_ms=40.0,
                total_time_ms=120.0,
                retrieved_sources=["doc2.md"],
                has_result=True,
            )
            logger.log_retrieval(log)

        stats = logger.get_agent_stats()

        # Should be sorted by query_count descending
        assert len(stats) == 2
        assert stats[0].agent_class == "cybersecurity"
        assert stats[0].query_count == 5
        assert stats[0].success_rate == 80.0  # 4/5 * 100
        assert stats[0].avg_retrieval_time_ms == 50.0
        assert stats[0].avg_total_time_ms == 150.0
        assert stats[0].avg_retrieved_count == 10.0
        assert stats[0].avg_effective_hit_count == 8.0
        assert stats[0].avg_top_score == 0.95

        assert stats[1].agent_class == "artificial_intelligence"
        assert stats[1].query_count == 3
        assert stats[1].success_rate == 100.0
        assert stats[1].avg_top_score == 0.88


class TestDocumentStats:
    """Test document statistics functionality."""

    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset logger state before each test."""
        logger = RetrievalLogger.get_instance()
        logger._logs.clear()
        yield

    def test_get_document_stats_empty(self):
        """Test get_document_stats with no data."""
        logger = RetrievalLogger.get_instance()
        stats = logger.get_document_stats()

        assert stats == []

    def test_get_document_stats(self):
        """Test get_document_stats with sample data."""
        logger = RetrievalLogger.get_instance()

        # Add logs with different documents
        logs_data = [
            # doc1.md: 3 times, by cybersecurity (2) and AI (1)
            ("log-1", "cybersecurity", ["doc1.md", "doc2.md"], [0.95, 0.85]),
            ("log-2", "cybersecurity", ["doc1.md"], [0.90]),
            ("log-3", "artificial_intelligence", ["doc1.md", "doc3.md"], [0.88, 0.78]),
            # doc2.md: 2 times, by cybersecurity (1) and general (1)
            ("log-4", "general", ["doc2.md"], [0.80]),
            # doc3.md: 1 time
        ]

        for log_id, agent, sources, scores in logs_data:
            log = RetrievalLog(
                log_id=log_id,
                timestamp=utcnow(),
                question="Test",
                agent_class=agent,
                route="vector",
                filtered_docs_count=100,
                retrieved_count=len(sources),
                effective_hit_count=len(sources),
                top_scores=scores,
                retrieval_time_ms=50.0,
                total_time_ms=150.0,
                retrieved_sources=sources,
                has_result=True,
            )
            logger.log_retrieval(log)

        stats = logger.get_document_stats(limit=10)

        # Should be sorted by retrieval_count descending
        assert len(stats) == 3

        # doc1.md should be first (3 retrievals)
        assert stats[0].source == "doc1.md"
        assert stats[0].retrieval_count == 3
        assert stats[0].avg_score == pytest.approx((0.95 + 0.90 + 0.88) / 3)
        assert stats[0].agent_usage == {
            "cybersecurity": 2,
            "artificial_intelligence": 1,
        }

        # doc2.md should be second (2 retrievals)
        assert stats[1].source == "doc2.md"
        assert stats[1].retrieval_count == 2
        assert stats[1].avg_score == pytest.approx((0.85 + 0.80) / 2)
        assert stats[1].agent_usage == {
            "cybersecurity": 1,
            "general": 1,
        }

        # doc3.md should be third (1 retrieval)
        assert stats[2].source == "doc3.md"
        assert stats[2].retrieval_count == 1
        assert stats[2].avg_score == 0.78

    def test_get_document_stats_limit(self):
        """Test get_document_stats respects limit parameter."""
        logger = RetrievalLogger.get_instance()

        # Add 25 different documents
        for i in range(25):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question="Test",
                agent_class="general",
                route="vector",
                filtered_docs_count=100,
                retrieved_count=1,
                effective_hit_count=1,
                top_scores=[0.8],
                retrieval_time_ms=50.0,
                total_time_ms=150.0,
                retrieved_sources=[f"doc{i}.md"],
                has_result=True,
            )
            logger.log_retrieval(log)

        stats = logger.get_document_stats(limit=20)
        assert len(stats) == 20


class TestExportFunctionality:
    """Test export functionality."""

    @pytest.fixture(autouse=True)
    def reset_logger(self):
        """Reset logger state before each test."""
        logger = RetrievalLogger.get_instance()
        logger._logs.clear()
        yield

    def test_export_logs_json_empty(self):
        """Test JSON export with no data."""
        logger = RetrievalLogger.get_instance()
        result = logger.export_logs(format="json")

        data = json.loads(result)
        assert data == []

    def test_export_logs_json(self):
        """Test JSON export with data."""
        logger = RetrievalLogger.get_instance()

        # Add sample logs
        for i in range(3):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question=f"Question {i}",
                agent_class="cybersecurity",
                route="vector",
                filtered_docs_count=100,
                retrieved_count=10,
                effective_hit_count=8,
                top_scores=[0.9, 0.8],
                retrieval_time_ms=50.0,
                total_time_ms=150.0,
                retrieved_sources=["doc1.md"],
                has_result=True,
            )
            logger.log_retrieval(log)

        result = logger.export_logs(format="json")
        data = json.loads(result)

        assert len(data) == 3
        assert data[0]["log_id"] == "log-0"
        assert data[0]["question"] == "Question 0"
        assert data[0]["agent_class"] == "cybersecurity"

    def test_export_logs_csv_empty(self):
        """Test CSV export with no data."""
        logger = RetrievalLogger.get_instance()
        result = logger.export_logs(format="csv")

        # Should have header row only
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "log_id" in lines[0]

    def test_export_logs_csv(self):
        """Test CSV export with data."""
        logger = RetrievalLogger.get_instance()

        # Add sample logs
        for i in range(3):
            log = RetrievalLog(
                log_id=f"log-{i}",
                timestamp=utcnow(),
                question=f"Question {i}",
                agent_class="cybersecurity",
                route="vector",
                filtered_docs_count=100,
                retrieved_count=10,
                effective_hit_count=8,
                top_scores=[0.9, 0.8],
                retrieval_time_ms=50.0,
                total_time_ms=150.0,
                retrieved_sources=["doc1.md", "doc2.md"],
                has_result=True,
            )
            logger.log_retrieval(log)

        result = logger.export_logs(format="csv")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["log_id"] == "log-0"
        assert rows[0]["question"] == "Question 0"
        assert rows[0]["agent_class"] == "cybersecurity"
        assert rows[0]["route"] == "vector"
        assert rows[0]["has_result"] == "True"

    def test_export_logs_csv_with_commas(self):
        """Test CSV export properly escapes fields with commas."""
        logger = RetrievalLogger.get_instance()

        log = RetrievalLog(
            log_id="log-1",
            timestamp=utcnow(),
            question="What is AI, ML, and DL?",
            agent_class="artificial_intelligence",
            route="vector",
            filtered_docs_count=100,
            retrieved_count=10,
            effective_hit_count=8,
            top_scores=[0.9, 0.8],
            retrieval_time_ms=50.0,
            total_time_ms=150.0,
            retrieved_sources=["doc1.md", "doc2.md"],
            has_result=True,
        )
        logger.log_retrieval(log)

        result = logger.export_logs(format="csv")

        # Parse CSV - should handle commas correctly
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["question"] == "What is AI, ML, and DL?"

    def test_export_logs_invalid_format(self):
        """Test export with invalid format raises error."""
        logger = RetrievalLogger.get_instance()

        with pytest.raises(ValueError, match="Unsupported format"):
            logger.export_logs(format="xml")
