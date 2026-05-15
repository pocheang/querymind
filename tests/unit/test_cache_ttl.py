"""Unit tests for PDF processing cache TTL (Time-To-Live) functionality."""

import pytest
import json
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.ingestion.utils.performance import PDFProcessingCache


@pytest.fixture
def temp_cache_dir():
    """Provide a temporary cache directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_cache_ttl_")
    cache_dir = Path(temp_dir) / "test_cache"
    cache_dir.mkdir()
    yield cache_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_pdf_ttl_")
    pdf_path = Path(temp_dir) / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest content")
    yield pdf_path
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def cache_with_ttl(temp_cache_dir):
    """Provide a PDFProcessingCache instance with TTL support."""
    return PDFProcessingCache(cache_dir=temp_cache_dir, ttl_days=30)


@pytest.fixture
def cache_short_ttl(temp_cache_dir):
    """Provide a PDFProcessingCache instance with short TTL for testing."""
    return PDFProcessingCache(cache_dir=temp_cache_dir, ttl_days=1)


# TTL Initialization Tests
def test_cache_ttl_initialization(temp_cache_dir):
    """Test that ttl_days parameter is correctly stored and converted to seconds."""
    cache = PDFProcessingCache(cache_dir=temp_cache_dir, ttl_days=30)

    assert cache.ttl_days == 30
    assert cache.ttl_seconds == 30 * 24 * 3600
    assert cache.ttl_seconds == 2592000


def test_cache_ttl_default_value(temp_cache_dir):
    """Test that default ttl_days is 30."""
    cache = PDFProcessingCache(cache_dir=temp_cache_dir)

    assert cache.ttl_days == 30
    assert cache.ttl_seconds == 30 * 24 * 3600


def test_cache_ttl_custom_value(temp_cache_dir):
    """Test that custom ttl_days values are correctly stored."""
    cache = PDFProcessingCache(cache_dir=temp_cache_dir, ttl_days=7)

    assert cache.ttl_days == 7
    assert cache.ttl_seconds == 7 * 24 * 3600
    assert cache.ttl_seconds == 604800


# is_cache_valid Tests
def test_is_cache_valid_fresh_cache(cache_with_ttl, sample_pdf):
    """Test that fresh cache is considered valid."""
    # Create a cache entry
    cache_with_ttl.set(sample_pdf, "docling", {"data": "test"})
    cache_path = cache_with_ttl.get_cache_path(sample_pdf, "docling")

    # Fresh cache should be valid
    assert cache_with_ttl.is_cache_valid(cache_path) is True


def test_is_cache_valid_expired_cache(cache_short_ttl, sample_pdf):
    """Test that expired cache is considered invalid."""
    # Create a cache entry
    cache_short_ttl.set(sample_pdf, "docling", {"data": "test"})
    cache_path = cache_short_ttl.get_cache_path(sample_pdf, "docling")

    # Mock the file's modification time to be older than TTL
    old_mtime = time.time() - (2 * 24 * 3600)  # 2 days ago

    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = old_mtime
        mock_stat.return_value = mock_stat_result

        # Expired cache should be invalid
        assert cache_short_ttl.is_cache_valid(cache_path) is False


def test_is_cache_valid_missing_file(cache_with_ttl, sample_pdf):
    """Test that missing cache file is considered invalid."""
    cache_path = cache_with_ttl.get_cache_path(sample_pdf, "nonexistent")

    # Missing file should be invalid
    assert cache_with_ttl.is_cache_valid(cache_path) is False


def test_is_cache_valid_boundary_case(cache_short_ttl, sample_pdf):
    """Test cache validity at TTL boundary."""
    # Create a cache entry
    cache_short_ttl.set(sample_pdf, "docling", {"data": "test"})
    cache_path = cache_short_ttl.get_cache_path(sample_pdf, "docling")

    # Mock the file's modification time to be exactly at TTL boundary
    boundary_mtime = time.time() - cache_short_ttl.ttl_seconds

    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = boundary_mtime
        mock_stat.return_value = mock_stat_result

        # At boundary (exactly TTL seconds old), should be invalid
        assert cache_short_ttl.is_cache_valid(cache_path) is False


# get() with TTL Tests
def test_get_with_expired_cache(cache_short_ttl, sample_pdf):
    """Test that get() returns None and deletes expired cache."""
    # Create a cache entry
    cache_short_ttl.set(sample_pdf, "docling", {"data": "test"})
    cache_path = cache_short_ttl.get_cache_path(sample_pdf, "docling")

    assert cache_path.exists()

    # Mock the file's modification time to be older than TTL
    old_mtime = time.time() - (2 * 24 * 3600)  # 2 days ago

    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = old_mtime
        mock_stat.return_value = mock_stat_result

        # get() should return None for expired cache
        result = cache_short_ttl.get(sample_pdf, "docling")
        assert result is None

    # Cache file should be deleted
    assert not cache_path.exists()


def test_get_with_valid_cache(cache_with_ttl, sample_pdf):
    """Test that get() returns data for valid cache."""
    test_data = {"pages": 10, "content": "test"}

    # Create a cache entry
    cache_with_ttl.set(sample_pdf, "docling", test_data)

    # get() should return the data for valid cache
    result = cache_with_ttl.get(sample_pdf, "docling")
    assert result == test_data


def test_get_with_missing_cache(cache_with_ttl, sample_pdf):
    """Test that get() returns None for missing cache."""
    result = cache_with_ttl.get(sample_pdf, "nonexistent")
    assert result is None


# cleanup_expired Tests
def test_cleanup_expired_removes_old_files(cache_short_ttl, sample_pdf):
    """Test that cleanup_expired() removes only expired files."""
    # Create multiple cache entries
    cache_short_ttl.set(sample_pdf, "op1", {"data": 1})
    cache_short_ttl.set(sample_pdf, "op2", {"data": 2})

    cache_path1 = cache_short_ttl.get_cache_path(sample_pdf, "op1")
    cache_path2 = cache_short_ttl.get_cache_path(sample_pdf, "op2")

    assert cache_path1.exists()
    assert cache_path2.exists()

    # Mock the file's modification time for both to be expired
    old_mtime = time.time() - (2 * 24 * 3600)  # 2 days ago

    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = old_mtime
        mock_stat.return_value = mock_stat_result

        # cleanup_expired should remove expired files
        cleaned = cache_short_ttl.cleanup_expired()
        assert cleaned == 2  # Both files are expired in this mock


def test_cleanup_expired_preserves_valid_files(cache_with_ttl, sample_pdf):
    """Test that cleanup_expired() preserves valid cache files."""
    # Create cache entries
    cache_with_ttl.set(sample_pdf, "op1", {"data": 1})
    cache_with_ttl.set(sample_pdf, "op2", {"data": 2})

    cache_path1 = cache_with_ttl.get_cache_path(sample_pdf, "op1")
    cache_path2 = cache_with_ttl.get_cache_path(sample_pdf, "op2")

    # cleanup_expired should not remove fresh files
    cleaned = cache_with_ttl.cleanup_expired()
    assert cleaned == 0

    # Files should still exist
    assert cache_path1.exists()
    assert cache_path2.exists()


def test_cleanup_expired_returns_count(cache_short_ttl, sample_pdf):
    """Test that cleanup_expired() returns correct count of cleaned files."""
    # Create cache entries
    cache_short_ttl.set(sample_pdf, "op1", {"data": 1})
    cache_short_ttl.set(sample_pdf, "op2", {"data": 2})
    cache_short_ttl.set(sample_pdf, "op3", {"data": 3})

    # Mock all files as expired
    old_mtime = time.time() - (2 * 24 * 3600)

    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = old_mtime
        mock_stat.return_value = mock_stat_result

        cleaned = cache_short_ttl.cleanup_expired()
        assert cleaned == 3


def test_cleanup_expired_empty_cache(cache_with_ttl):
    """Test that cleanup_expired() handles empty cache gracefully."""
    cleaned = cache_with_ttl.cleanup_expired()
    assert cleaned == 0


def test_cleanup_expired_handles_exceptions(cache_with_ttl, sample_pdf):
    """Test that cleanup_expired() handles exceptions gracefully."""
    # Create a cache entry
    cache_with_ttl.set(sample_pdf, "op1", {"data": 1})

    # Mock stat to raise an exception
    with patch('pathlib.Path.stat', side_effect=OSError("Permission denied")):
        # Should not raise, should handle gracefully
        cleaned = cache_with_ttl.cleanup_expired()
        assert cleaned == 0


# get_cache_stats Tests
def test_get_cache_stats_accuracy(cache_with_ttl, sample_pdf):
    """Test that get_cache_stats() returns accurate statistics."""
    # Create cache entries
    cache_with_ttl.set(sample_pdf, "op1", {"data": 1})
    cache_with_ttl.set(sample_pdf, "op2", {"data": 2})

    stats = cache_with_ttl.get_cache_stats()

    assert "total_files" in stats
    assert "total_size_mb" in stats
    assert "expired_files" in stats
    assert "valid_files" in stats

    assert stats["total_files"] == 2
    assert stats["valid_files"] == 2
    assert stats["expired_files"] == 0
    assert stats["total_size_mb"] > 0


def test_get_cache_stats_with_expired_files(cache_short_ttl, sample_pdf):
    """Test that get_cache_stats() correctly counts expired files."""
    # Create cache entries
    cache_short_ttl.set(sample_pdf, "op1", {"data": 1})
    cache_short_ttl.set(sample_pdf, "op2", {"data": 2})

    # Get the actual cache paths
    cache_path1 = cache_short_ttl.get_cache_path(sample_pdf, "op1")
    cache_path2 = cache_short_ttl.get_cache_path(sample_pdf, "op2")

    # Mock one file as expired by patching is_cache_valid
    original_is_cache_valid = cache_short_ttl.is_cache_valid

    def mock_is_cache_valid(path):
        if path == cache_path1:
            return False  # op1 is expired
        return original_is_cache_valid(path)

    with patch.object(cache_short_ttl, 'is_cache_valid', side_effect=mock_is_cache_valid):
        stats = cache_short_ttl.get_cache_stats()

        assert stats["total_files"] == 2
        assert stats["expired_files"] == 1
        assert stats["valid_files"] == 1


def test_get_cache_stats_empty_cache(cache_with_ttl):
    """Test that get_cache_stats() handles empty cache."""
    stats = cache_with_ttl.get_cache_stats()

    assert stats["total_files"] == 0
    assert stats["total_size_mb"] == 0
    assert stats["expired_files"] == 0
    assert stats["valid_files"] == 0


def test_get_cache_stats_size_calculation(cache_with_ttl, sample_pdf):
    """Test that get_cache_stats() correctly calculates total size."""
    # Create cache entries with known data
    cache_with_ttl.set(sample_pdf, "op1", {"data": "x" * 1000})  # ~1KB
    cache_with_ttl.set(sample_pdf, "op2", {"data": "y" * 1000})  # ~1KB

    stats = cache_with_ttl.get_cache_stats()

    # Should have at least 2KB total (accounting for JSON formatting)
    assert stats["total_size_mb"] > 0
    assert stats["total_files"] == 2


def test_get_cache_stats_handles_exceptions(cache_with_ttl, sample_pdf):
    """Test that get_cache_stats() handles exceptions gracefully."""
    # Create a cache entry
    cache_with_ttl.set(sample_pdf, "op1", {"data": 1})

    # Mock stat to raise an exception
    with patch('pathlib.Path.stat', side_effect=OSError("Permission denied")):
        # Should not raise, should handle gracefully
        stats = cache_with_ttl.get_cache_stats()
        assert isinstance(stats, dict)
        assert "total_files" in stats
