"""Pytest tests for performance benchmarking."""

import pytest
import tempfile
import os
from pathlib import Path
from io import BytesIO
from PIL import Image
from tests.performance.benchmark_pdf_processing import (
    PDFBenchmark,
    run_cache_benchmark,
    run_chart_extraction_benchmark
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory in the project."""
    temp_path = Path("tests/.tmp/performance_test")
    temp_path.mkdir(parents=True, exist_ok=True)
    yield temp_path
    # Cleanup
    import shutil
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_pdf(temp_dir):
    """Create a minimal valid PDF for testing."""
    pdf_path = temp_dir / "test_sample.pdf"
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
190
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def benchmark_instance(temp_dir):
    """Create a PDFBenchmark instance with temp results file."""
    results_file = temp_dir / "test_results.json"
    return PDFBenchmark(results_file=results_file)


@pytest.fixture
def test_image_bytes():
    """Create test image bytes."""
    img = Image.new('RGB', (1000, 800), color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def test_benchmark_loader_success(benchmark_instance, sample_pdf):
    """Test benchmarking a successful PDF loader."""
    def mock_loader(pdf_path):
        return ["doc1", "doc2", "doc3"]

    result = benchmark_instance.benchmark_loader(
        sample_pdf,
        mock_loader,
        "test_mode"
    )

    assert result["mode"] == "test_mode"
    assert result["file_name"] == "test_sample.pdf"
    assert result["success"] is True
    assert result["error"] is None
    assert result["num_docs"] == 3
    assert result["time_seconds"] >= 0
    assert "memory_mb" in result
    assert "file_size_mb" in result


def test_benchmark_loader_failure(benchmark_instance, sample_pdf):
    """Test benchmarking a failing PDF loader."""
    def failing_loader(pdf_path):
        raise ValueError("Test error")

    result = benchmark_instance.benchmark_loader(
        sample_pdf,
        failing_loader,
        "failing_mode"
    )

    assert result["mode"] == "failing_mode"
    assert result["success"] is False
    assert result["error"] == "Test error"
    assert result["num_docs"] == 0
    assert result["time_seconds"] >= 0


def test_benchmark_cache_operations(benchmark_instance, sample_pdf):
    """Test cache operations benchmarking."""
    from app.ingestion.utils.performance import PDFProcessingCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = PDFProcessingCache(cache_dir=Path(tmpdir))

        result = benchmark_instance.benchmark_cache_operations(
            cache,
            sample_pdf,
            num_iterations=10
        )

        assert result["operation"] == "cache_operations"
        assert result["iterations"] == 10
        assert result["set_time_seconds"] >= 0
        assert result["get_time_seconds"] >= 0
        assert result["avg_set_ms"] >= 0
        assert result["avg_get_ms"] >= 0


def test_benchmark_chart_extraction(benchmark_instance, test_image_bytes):
    """Test chart extraction benchmarking."""
    result = benchmark_instance.benchmark_chart_extraction(
        test_image_bytes,
        num_iterations=3
    )

    assert result["operation"] == "chart_extraction"
    assert result["iterations"] == 3
    assert result["total_time_seconds"] >= 0
    assert result["avg_time_ms"] >= 0
    assert "memory_mb" in result


def test_save_results(benchmark_instance, temp_dir):
    """Test saving benchmark results to JSON."""
    results = [
        {
            "mode": "test",
            "file_name": "test.pdf",
            "time_seconds": 1.5,
            "memory_mb": 10.0,
            "success": True
        }
    ]

    benchmark_instance.save_results(results)

    assert benchmark_instance.results_file.exists()

    import json
    with open(benchmark_instance.results_file, 'r') as f:
        data = json.load(f)

    assert "timestamp" in data
    assert "benchmarks" in data
    assert len(data["benchmarks"]) == 1
    assert data["benchmarks"][0]["mode"] == "test"


def test_run_cache_benchmark(sample_pdf):
    """Test running cache benchmark."""
    result = run_cache_benchmark(sample_pdf, num_iterations=5)

    assert result["operation"] == "cache_operations"
    assert result["iterations"] == 5
    assert result["set_time_seconds"] >= 0
    assert result["get_time_seconds"] >= 0


def test_run_chart_extraction_benchmark():
    """Test running chart extraction benchmark."""
    result = run_chart_extraction_benchmark(num_iterations=2)

    assert result["operation"] == "chart_extraction"
    assert result["iterations"] == 2
    assert result["total_time_seconds"] >= 0
    assert result["avg_time_ms"] >= 0


def test_benchmark_memory_tracking(benchmark_instance, sample_pdf):
    """Test that memory tracking works."""
    def memory_intensive_loader(pdf_path):
        # Allocate some memory
        data = [0] * 1000000
        return [f"doc_{i}" for i in range(10)]

    result = benchmark_instance.benchmark_loader(
        sample_pdf,
        memory_intensive_loader,
        "memory_test"
    )

    assert result["success"] is True
    assert "memory_mb" in result
    # Memory should be tracked (may be positive or negative depending on GC)
    assert isinstance(result["memory_mb"], (int, float))


def test_benchmark_timing_accuracy(benchmark_instance, sample_pdf):
    """Test that timing measurements are accurate."""
    import time

    def slow_loader(pdf_path):
        time.sleep(0.1)  # Sleep for 100ms
        return ["doc"]

    result = benchmark_instance.benchmark_loader(
        sample_pdf,
        slow_loader,
        "slow_mode"
    )

    # Should measure at least 100ms (0.1s)
    assert result["time_seconds"] >= 0.1
    assert result["success"] is True


def test_benchmark_results_format(benchmark_instance, sample_pdf):
    """Test that benchmark results have correct format."""
    def simple_loader(pdf_path):
        return ["doc1", "doc2"]

    result = benchmark_instance.benchmark_loader(
        sample_pdf,
        simple_loader,
        "format_test"
    )

    # Check all required fields
    required_fields = [
        "mode", "file_name", "file_size_mb", "time_seconds",
        "memory_mb", "num_docs", "success", "error"
    ]

    for field in required_fields:
        assert field in result, f"Missing field: {field}"

    # Check types
    assert isinstance(result["mode"], str)
    assert isinstance(result["file_name"], str)
    assert isinstance(result["file_size_mb"], (int, float))
    assert isinstance(result["time_seconds"], (int, float))
    assert isinstance(result["memory_mb"], (int, float))
    assert isinstance(result["num_docs"], int)
    assert isinstance(result["success"], bool)
    assert result["error"] is None or isinstance(result["error"], str)
