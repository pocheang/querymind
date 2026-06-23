"""
Tests for role-based rate limiting.
"""

import time
from datetime import UTC

from app.services.role_based_rate_limiter import RoleBasedRateLimiter, SlidingWindowLimiter


class TestRoleBasedRateLimiter:
    """Test role-based rate limiter."""

    def test_basic_rate_limiting(self):
        """Test basic rate limiting without roles."""
        limiter = RoleBasedRateLimiter(default_max_attempts=3, default_window_seconds=1)

        # First 3 requests should pass
        assert not limiter.is_limited("user1")
        limiter.record("user1")
        assert not limiter.is_limited("user1")
        limiter.record("user1")
        assert not limiter.is_limited("user1")
        limiter.record("user1")

        # 4th request should be limited
        assert limiter.is_limited("user1")

    def test_role_based_limits(self):
        """Test different limits for different roles."""
        limiter = RoleBasedRateLimiter(
            default_max_attempts=2, default_window_seconds=60, role_limits={"admin": (10, 60), "user": (2, 60)}
        )

        # Admin can make 10 requests
        for _i in range(10):
            assert not limiter.is_limited("admin1", role="admin")
            limiter.record("admin1", role="admin")

        assert limiter.is_limited("admin1", role="admin")

        # Regular user can only make 2 requests
        assert not limiter.is_limited("user1", role="user")
        limiter.record("user1", role="user")
        assert not limiter.is_limited("user1", role="user")
        limiter.record("user1", role="user")
        assert limiter.is_limited("user1", role="user")

    def test_window_expiration(self):
        """Test that limits reset after window expires."""
        limiter = RoleBasedRateLimiter(default_max_attempts=2, default_window_seconds=1)

        # Use up quota
        limiter.record("user1")
        limiter.record("user1")
        assert limiter.is_limited("user1")

        # Wait for window to expire
        time.sleep(1.1)

        # Should be able to make requests again
        assert not limiter.is_limited("user1")

    def test_get_remaining(self):
        """Test getting remaining quota."""
        limiter = RoleBasedRateLimiter(
            default_max_attempts=5, default_window_seconds=60, role_limits={"admin": (10, 60)}
        )

        # Admin starts with 10 remaining
        assert limiter.get_remaining("admin1", role="admin") == 10

        # After 3 requests
        for _ in range(3):
            limiter.record("admin1", role="admin")

        assert limiter.get_remaining("admin1", role="admin") == 7

        # User starts with 5 remaining (default)
        assert limiter.get_remaining("user1", role="user") == 5

    def test_reset(self):
        """Test resetting rate limit."""
        limiter = RoleBasedRateLimiter(default_max_attempts=2, default_window_seconds=60)

        # Use up quota
        limiter.record("user1")
        limiter.record("user1")
        assert limiter.is_limited("user1")

        # Reset
        limiter.reset("user1")

        # Should be able to make requests again
        assert not limiter.is_limited("user1")
        assert limiter.get_remaining("user1") == 2

    def test_multiple_users_isolated(self):
        """Test that different users have isolated quotas."""
        limiter = RoleBasedRateLimiter(default_max_attempts=2, default_window_seconds=60)

        # User1 uses quota
        limiter.record("user1")
        limiter.record("user1")
        assert limiter.is_limited("user1")

        # User2 still has quota
        assert not limiter.is_limited("user2")
        assert limiter.get_remaining("user2") == 2

    def test_get_reset_time(self):
        """Test getting reset time."""
        limiter = RoleBasedRateLimiter(default_max_attempts=2, default_window_seconds=60)

        # No reset time when no requests
        assert limiter.get_reset_time("user1") is None

        # After first request
        limiter.record("user1")
        reset_time = limiter.get_reset_time("user1")
        assert reset_time is not None

        # Reset time should be ~60 seconds in future
        from datetime import datetime

        now = datetime.now(UTC)
        time_diff = (reset_time - now).total_seconds()
        assert 59 <= time_diff <= 61


class TestBackwardCompatibility:
    """Test backward compatibility with SlidingWindowLimiter."""

    def test_legacy_limiter(self):
        """Test that legacy SlidingWindowLimiter still works."""
        limiter = SlidingWindowLimiter(max_attempts=3, window_seconds=1)

        # Should work exactly like before
        assert not limiter.is_limited("user1")
        limiter.record("user1")
        assert not limiter.is_limited("user1")
        limiter.record("user1")
        assert not limiter.is_limited("user1")
        limiter.record("user1")
        assert limiter.is_limited("user1")

    def test_legacy_reset(self):
        """Test reset in legacy limiter."""
        limiter = SlidingWindowLimiter(max_attempts=2, window_seconds=60)

        limiter.record("user1")
        limiter.record("user1")
        assert limiter.is_limited("user1")

        limiter.reset("user1")
        assert not limiter.is_limited("user1")


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_key(self):
        """Test handling of empty keys."""
        limiter = RoleBasedRateLimiter(default_max_attempts=3, default_window_seconds=60)

        # Empty key should not be limited
        assert not limiter.is_limited("")
        assert not limiter.is_limited(None)

        # Recording empty key should not crash
        limiter.record("")
        limiter.record(None)

    def test_zero_or_negative_limits(self):
        """Test that limits are always >= 1."""
        limiter = RoleBasedRateLimiter(
            default_max_attempts=0,  # Should be clamped to 1
            default_window_seconds=0,  # Should be clamped to 1
        )

        # Should still allow at least 1 request
        assert not limiter.is_limited("user1")
        limiter.record("user1")
        assert limiter.is_limited("user1")

    def test_unknown_role(self):
        """Test handling of unknown roles."""
        limiter = RoleBasedRateLimiter(
            default_max_attempts=2, default_window_seconds=60, role_limits={"admin": (10, 60)}
        )

        # Unknown role should use default limits
        assert limiter.get_remaining("user1", role="unknown") == 2
        assert limiter.get_remaining("user1", role="nonexistent") == 2
