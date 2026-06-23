"""Tests for bulkhead semaphore fix."""

import pytest

from app.services.bulkhead import BulkheadRejectedError, bulkhead, reset_bulkheads


def test_bulkhead_release_on_success():
    """Test that bulkhead releases semaphore on success."""
    reset_bulkheads()

    # Should be able to acquire and release multiple times
    for _ in range(3):
        with bulkhead("test"):
            pass  # Should release properly


def test_bulkhead_release_on_exception():
    """Test that bulkhead releases semaphore even on exception."""
    reset_bulkheads()

    # Exception should still release the semaphore
    for _ in range(3):
        try:
            with bulkhead("test"):
                raise ValueError("test error")
        except ValueError:
            pass  # Expected

    # Should still be able to acquire after exceptions
    with bulkhead("test"):
        pass


def test_bulkhead_no_release_on_timeout():
    """Test that bulkhead doesn't release when acquire fails."""
    from unittest.mock import MagicMock, patch

    reset_bulkheads()

    # Mock semaphore to always timeout
    with patch("app.services.bulkhead._semaphore") as mock_sem_fn:
        mock_sem = MagicMock()
        mock_sem.acquire.return_value = False  # Simulate timeout
        mock_sem_fn.return_value = mock_sem

        with pytest.raises(BulkheadRejectedError):
            with bulkhead("test"):
                pass

        # Verify release was NOT called when acquire failed
        mock_sem.release.assert_not_called()


def test_bulkhead_disabled():
    """Test that bulkhead can be disabled via settings."""
    from unittest.mock import patch

    reset_bulkheads()

    # Mock settings to disable bulkhead
    with patch("app.services.bulkhead.get_settings") as mock_settings:
        mock_settings.return_value.bulkhead_enabled = False

        # Should pass through without acquiring semaphore
        with bulkhead("test"):
            pass
