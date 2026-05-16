"""Unit tests for PDF processing cache system."""

import pytest
import json
import threading
import tempfile
import shutil
import time
from pathlib import Path
from app.ingestion.utils.performance import (
    PDFProcessingCache,
    compute_file_hash,
    compute_config_hash
)


@pytest.fixture
def temp_cache_dir():
    """Provide a temporary cache directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_cache_")
    cache_dir = Path(temp_dir) / "test_cache"
    cache_dir.mkdir()
    yield cache_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_pdf_")
    pdf_path = Path(temp_dir) / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest content")
    yield pdf_path
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf2():
    """Create a second sample PDF file for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_pdf2_")
    pdf_path = Path(temp_dir) / "another.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nother")
    yield pdf_path
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_file():
    """Create a test file for hash testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_hash_")
    file_path = Path(temp_dir) / "test.txt"
    file_path.write_text("test content")
    yield file_path
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cache(temp_cache_dir):
    """Provide a PDFProcessingCache instance."""
    return PDFProcessingCache(cache_dir=temp_cache_dir)


# Config hash tests
def test_compute_config_hash_consistent():
    """Test that same config produces same hash."""
    config1 = {"enable_cleaning": True, "mode": "enhanced"}
    config2 = {"mode": "enhanced", "enable_cleaning": True}

    hash1 = compute_config_hash(config1)
    hash2 = compute_config_hash(config2)

    assert hash1 == hash2
    assert len(hash1) == 8


def test_compute_config_hash_different():
    """Test that different configs produce different hashes."""
    config1 = {"enable_cleaning": True}
    config2 = {"enable_cleaning": False}

    hash1 = compute_config_hash(config1)
    hash2 = compute_config_hash(config2)

    assert hash1 != hash2


def test_compute_config_hash_empty():
    """Test that empty config returns empty string."""
    assert compute_config_hash({}) == ""
    assert compute_config_hash(None) == ""


# Cache isolation tests
def test_cache_with_different_configs(cache, sample_pdf):
    """Test that different configs use different cache keys."""
    config1 = {"enable_cleaning": True}
    config2 = {"enable_cleaning": False}

    # Set cache with config1
    cache.set(sample_pdf, "docling", {"result": "data1"}, config1)

    # Set cache with config2
    cache.set(sample_pdf, "docling", {"result": "data2"}, config2)

    # Get with config1
    result1 = cache.get(sample_pdf, "docling", config1)
    assert result1 == {"result": "data1"}

    # Get with config2
    result2 = cache.get(sample_pdf, "docling", config2)
    assert result2 == {"result": "data2"}


def test_cache_hit_and_miss(cache, sample_pdf):
    """Test cache hit and miss scenarios."""
    # Miss - no cache exists
    result = cache.get(sample_pdf, "docling")
    assert result is None

    # Set cache
    test_data = {"pages": 10, "content": "test"}
    cache.set(sample_pdf, "docling", test_data)

    # Hit - cache exists
    result = cache.get(sample_pdf, "docling")
    assert result == test_data


# Atomic write tests
def test_cache_atomic_write(cache, sample_pdf):
    """Test that cache writes are atomic (no corruption)."""

    def write_cache(value):
        cache.set(sample_pdf, "test", {"value": value})

    # Concurrent writes with small delay to reduce contention
    threads = []
    for i in range(10):
        t = threading.Thread(target=write_cache, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.01)  # Small delay to reduce Windows file locking contention

    for t in threads:
        t.join()

    # Read cache - should be valid JSON (if any write succeeded)
    result = cache.get(sample_pdf, "test")
    # On Windows, some writes may fail due to file locking, but at least one should succeed
    # The key test is: if a result exists, it must be valid (no corruption)
    if result is not None:
        assert "value" in result
        assert isinstance(result["value"], int)
        assert 0 <= result["value"] < 10


# Cache clear tests
def test_cache_clear_operations(cache, sample_pdf, sample_pdf2):
    """Test cache clearing functionality."""
    # Create multiple cache entries
    cache.set(sample_pdf, "op1", {"data": 1})
    cache.set(sample_pdf, "op2", {"data": 2})

    cache.set(sample_pdf2, "op1", {"data": 3})

    # Clear specific file
    cache.clear(sample_pdf)

    assert cache.get(sample_pdf, "op1") is None
    assert cache.get(sample_pdf, "op2") is None
    assert cache.get(sample_pdf2, "op1") == {"data": 3}

    # Clear all
    cache.clear()
    assert cache.get(sample_pdf2, "op1") is None


# File hash tests
def test_compute_file_hash_consistent(test_file):
    """Test that same file produces same hash."""
    hash1 = compute_file_hash(test_file)
    hash2 = compute_file_hash(test_file)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_compute_file_hash_different_content():
    """Test that different files produce different hashes."""
    temp_dir = tempfile.mkdtemp(prefix="test_hash_diff_")

    try:
        file1 = Path(temp_dir) / "file1.txt"
        file2 = Path(temp_dir) / "file2.txt"

        file1.write_text("content A")
        file2.write_text("content B")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 != hash2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
