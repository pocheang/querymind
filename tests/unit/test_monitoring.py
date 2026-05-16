import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import shutil

from app.ingestion.utils.monitoring import PDFProcessingMetrics


@pytest.fixture
def temp_metrics_dir():
    """Create a temporary directory for metrics files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def metrics_file(temp_metrics_dir):
    """Create a metrics file path in temp directory."""
    return temp_metrics_dir / "metrics" / "pdf_processing.jsonl"


@pytest.fixture
def monitoring(metrics_file):
    """Create a PDFProcessingMetrics instance with temp file."""
    return PDFProcessingMetrics(metrics_file=metrics_file)


@pytest.fixture
def temp_pdf_file(temp_metrics_dir):
    """Create a temporary PDF file for testing."""
    pdf_path = temp_metrics_dir / "test.pdf"
    pdf_path.write_bytes(b"fake pdf content" * 1000)  # ~15 KB
    return pdf_path


class TestMetricsInitialization:
    """Test PDFProcessingMetrics initialization."""

    def test_metrics_initialization(self, metrics_file):
        """Verify metrics file path and directory creation."""
        monitoring = PDFProcessingMetrics(metrics_file=metrics_file)

        assert monitoring.metrics_file == metrics_file
        assert metrics_file.parent.exists()
        assert metrics_file.parent.is_dir()

    def test_default_metrics_file_path(self):
        """Verify default metrics file path."""
        monitoring = PDFProcessingMetrics()

        assert monitoring.metrics_file == Path("./data/metrics/pdf_processing.jsonl")


class TestRecordProcessing:
    """Test record_processing method."""

    def test_record_processing_success(self, monitoring, temp_pdf_file):
        """Record successful processing."""
        monitoring.record_processing(
            file_path=temp_pdf_file,
            mode="streaming",
            duration=2.5,
            memory_mb=128.5,
            cache_hit=True,
            api_calls=3,
            num_pages=10,
            error=None
        )

        assert monitoring.metrics_file.exists()

        with open(monitoring.metrics_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            metric = json.loads(line)

        assert metric["file_name"] == "test.pdf"
        assert metric["mode"] == "streaming"
        assert metric["duration_seconds"] == 2.5
        assert metric["memory_mb"] == 128.5
        assert metric["cache_hit"] is True
        assert metric["api_calls"] == 3
        assert metric["num_pages"] == 10
        assert metric["error"] is None

    def test_record_processing_with_error(self, monitoring, temp_pdf_file):
        """Record processing with error."""
        monitoring.record_processing(
            file_path=temp_pdf_file,
            mode="batch",
            duration=1.0,
            memory_mb=64.0,
            cache_hit=False,
            api_calls=0,
            num_pages=0,
            error="PDF parsing failed"
        )

        with open(monitoring.metrics_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            metric = json.loads(line)

        assert metric["error"] == "PDF parsing failed"
        assert metric["cache_hit"] is False

    def test_record_processing_creates_jsonl(self, monitoring, temp_pdf_file):
        """Verify JSONL format (one JSON per line, not array)."""
        monitoring.record_processing(
            file_path=temp_pdf_file,
            mode="streaming",
            duration=1.0,
            memory_mb=100.0,
            cache_hit=True,
            api_calls=1,
            num_pages=5
        )

        content = monitoring.metrics_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')

        assert len(lines) == 1
        metric = json.loads(lines[0])
        assert isinstance(metric, dict)

    def test_record_processing_appends(self, monitoring, temp_pdf_file):
        """Multiple records append correctly."""
        for i in range(3):
            monitoring.record_processing(
                file_path=temp_pdf_file,
                mode="streaming",
                duration=float(i + 1),
                memory_mb=100.0 + i,
                cache_hit=i % 2 == 0,
                api_calls=i,
                num_pages=5 + i
            )

        with open(monitoring.metrics_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 3

        metrics = [json.loads(line) for line in lines]
        assert metrics[0]["duration_seconds"] == 1.0
        assert metrics[1]["duration_seconds"] == 2.0
        assert metrics[2]["duration_seconds"] == 3.0

    def test_record_processing_file_size_calculation(self, monitoring, temp_pdf_file):
        """Verify file size in MB calculation."""
        file_size_bytes = temp_pdf_file.stat().st_size
        expected_size_mb = file_size_bytes / 1024 / 1024

        monitoring.record_processing(
            file_path=temp_pdf_file,
            mode="streaming",
            duration=1.0,
            memory_mb=100.0,
            cache_hit=True,
            api_calls=1,
            num_pages=5
        )

        with open(monitoring.metrics_file, 'r', encoding='utf-8') as f:
            metric = json.loads(f.readline())

        assert abs(metric["file_size_mb"] - expected_size_mb) < 0.0001

    def test_record_processing_timestamp_format(self, monitoring, temp_pdf_file):
        """Verify timestamp is in ISO format."""
        before = datetime.now()

        monitoring.record_processing(
            file_path=temp_pdf_file,
            mode="streaming",
            duration=1.0,
            memory_mb=100.0,
            cache_hit=True,
            api_calls=1,
            num_pages=5
        )

        after = datetime.now()

        with open(monitoring.metrics_file, 'r', encoding='utf-8') as f:
            metric = json.loads(f.readline())

        timestamp = datetime.fromisoformat(metric["timestamp"])
        assert before <= timestamp <= after


class TestGetSummary:
    """Test get_summary method."""

    def test_get_summary_empty_file(self, monitoring):
        """Handle missing metrics file."""
        result = monitoring.get_summary(days=7)

        assert result == {}

    def test_get_summary_no_recent_metrics(self, monitoring, temp_pdf_file):
        """Handle old metrics outside time window."""
        # Record a metric with old timestamp
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()

        metric = {
            "timestamp": old_timestamp,
            "file_name": "test.pdf",
            "file_size_mb": 0.015,
            "mode": "streaming",
            "duration_seconds": 1.0,
            "memory_mb": 100.0,
            "cache_hit": True,
            "api_calls": 1,
            "num_pages": 5,
            "error": None
        }

        with open(monitoring.metrics_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(metric, ensure_ascii=False) + '\n')

        result = monitoring.get_summary(days=7)

        assert result == {}

    def test_get_summary_calculations(self, monitoring, temp_pdf_file):
        """Verify all statistics are correct."""
        # Record multiple metrics
        metrics_data = [
            {"duration": 1.0, "memory": 100.0, "cache_hit": True, "api_calls": 2, "error": None},
            {"duration": 2.0, "memory": 150.0, "cache_hit": True, "api_calls": 3, "error": None},
            {"duration": 3.0, "memory": 200.0, "cache_hit": False, "api_calls": 1, "error": None},
        ]

        for data in metrics_data:
            monitoring.record_processing(
                file_path=temp_pdf_file,
                mode="streaming",
                duration=data["duration"],
                memory_mb=data["memory"],
                cache_hit=data["cache_hit"],
                api_calls=data["api_calls"],
                num_pages=5,
                error=data["error"]
            )

        result = monitoring.get_summary(days=7)

        assert result["period_days"] == 7
        assert result["total_processed"] == 3
        assert result["avg_time_seconds"] == 2.0  # (1 + 2 + 3) / 3
        assert result["total_api_calls"] == 6  # 2 + 3 + 1
        assert result["estimated_cost_usd"] == 0.06  # 6 * 0.01
        assert result["cache_hit_rate"] == pytest.approx(2/3)  # 2 hits out of 3

    def test_get_summary_cache_hit_rate(self, monitoring, temp_pdf_file):
        """Verify cache hit rate calculation."""
        for i in range(4):
            monitoring.record_processing(
                file_path=temp_pdf_file,
                mode="streaming",
                duration=1.0,
                memory_mb=100.0,
                cache_hit=i < 3,  # 3 hits, 1 miss
                api_calls=1,
                num_pages=5
            )

        result = monitoring.get_summary(days=7)

        assert result["cache_hit_rate"] == 0.75  # 3/4

    def test_get_summary_error_rate(self, monitoring, temp_pdf_file):
        """Verify error rate calculation."""
        for i in range(5):
            monitoring.record_processing(
                file_path=temp_pdf_file,
                mode="streaming",
                duration=1.0,
                memory_mb=100.0,
                cache_hit=True,
                api_calls=1,
                num_pages=5,
                error="Error occurred" if i >= 3 else None  # 2 errors, 3 successes
            )

        result = monitoring.get_summary(days=7)

        assert result["error_rate"] == 0.4  # 2/5

    def test_get_summary_time_filtering(self, monitoring, temp_pdf_file):
        """Only include metrics within time window."""
        now = datetime.now()

        # Record old metric (10 days ago)
        old_metric = {
            "timestamp": (now - timedelta(days=10)).isoformat(),
            "file_name": "old.pdf",
            "file_size_mb": 0.015,
            "mode": "streaming",
            "duration_seconds": 1.0,
            "memory_mb": 100.0,
            "cache_hit": True,
            "api_calls": 1,
            "num_pages": 5,
            "error": None
        }

        # Record recent metrics (2 days ago and now)
        recent_metrics = [
            {
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "file_name": "recent1.pdf",
                "file_size_mb": 0.015,
                "mode": "streaming",
                "duration_seconds": 2.0,
                "memory_mb": 100.0,
                "cache_hit": True,
                "api_calls": 2,
                "num_pages": 5,
                "error": None
            },
            {
                "timestamp": now.isoformat(),
                "file_name": "recent2.pdf",
                "file_size_mb": 0.015,
                "mode": "streaming",
                "duration_seconds": 3.0,
                "memory_mb": 100.0,
                "cache_hit": False,
                "api_calls": 1,
                "num_pages": 5,
                "error": None
            }
        ]

        with open(monitoring.metrics_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(old_metric, ensure_ascii=False) + '\n')
            for metric in recent_metrics:
                f.write(json.dumps(metric, ensure_ascii=False) + '\n')

        result = monitoring.get_summary(days=7)

        assert result["total_processed"] == 2
        assert result["avg_time_seconds"] == 2.5  # (2 + 3) / 2
        assert result["total_api_calls"] == 3  # 2 + 1

    def test_get_summary_zero_metrics(self, monitoring, temp_pdf_file):
        """Handle case with zero metrics in time window."""
        result = monitoring.get_summary(days=7)

        assert result == {}

    def test_get_summary_single_metric(self, monitoring, temp_pdf_file):
        """Handle single metric correctly."""
        monitoring.record_processing(
            file_path=temp_pdf_file,
            mode="streaming",
            duration=5.0,
            memory_mb=256.0,
            cache_hit=True,
            api_calls=10,
            num_pages=20,
            error=None
        )

        result = monitoring.get_summary(days=7)

        assert result["total_processed"] == 1
        assert result["avg_time_seconds"] == 5.0
        assert result["cache_hit_rate"] == 1.0
        assert result["error_rate"] == 0.0
        assert result["total_api_calls"] == 10
        assert result["estimated_cost_usd"] == 0.10

    def test_get_summary_all_errors(self, monitoring, temp_pdf_file):
        """Handle case where all metrics have errors."""
        for i in range(3):
            monitoring.record_processing(
                file_path=temp_pdf_file,
                mode="streaming",
                duration=1.0,
                memory_mb=100.0,
                cache_hit=False,
                api_calls=0,
                num_pages=0,
                error=f"Error {i}"
            )

        result = monitoring.get_summary(days=7)

        assert result["error_rate"] == 1.0
        assert result["total_processed"] == 3
