"""Unit tests for PDF utility functions."""

import pytest
import hashlib
import tempfile
import shutil
from pathlib import Path
from app.ingestion.utils.performance import compute_file_hash


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path("tests/temp")
    temp_path.mkdir(parents=True, exist_ok=True)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_file(temp_dir):
    """Create a test file with known content."""
    file_path = temp_dir / "test.txt"
    file_path.write_text("test content for hashing")
    return file_path


def test_compute_file_hash_consistent(test_file):
    """Test that same file produces same hash."""
    hash1 = compute_file_hash(test_file)
    hash2 = compute_file_hash(test_file)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_compute_file_hash_different_content(temp_dir):
    """Test that different files produce different hashes."""
    file1 = temp_dir / "file1.txt"
    file2 = temp_dir / "file2.txt"

    file1.write_text("content A")
    file2.write_text("content B")

    hash1 = compute_file_hash(file1)
    hash2 = compute_file_hash(file2)

    assert hash1 != hash2


def test_compute_file_hash_large_file(temp_dir):
    """Test hashing of large files (chunked reading)."""
    large_file = temp_dir / "large.bin"

    # Create 10MB file
    large_file.write_bytes(b"x" * (10 * 1024 * 1024))

    hash_result = compute_file_hash(large_file)

    assert len(hash_result) == 64
    assert hash_result.isalnum()
