"""Tests for rate limiter atomicity fix."""

import threading

from app.services.rate_limiter import SlidingWindowLimiter


def test_rate_limiter_atomic_operation():
    """Test that try_acquire is atomic and prevents race conditions."""
    limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)
    key = "test_user"

    # Reset before testing
    limiter.reset(key)

    # Should be able to acquire 5 times
    for i in range(5):
        assert limiter.try_acquire(key), f"Attempt {i + 1} should succeed"

    # 6th attempt should fail
    assert not limiter.try_acquire(key), "6th attempt should fail"


def test_rate_limiter_concurrent_access():
    """Test rate limiter under concurrent access."""
    limiter = SlidingWindowLimiter(max_attempts=10, window_seconds=60)
    key = "concurrent_user"
    limiter.reset(key)

    success_count = [0]
    lock = threading.Lock()

    def worker():
        if limiter.try_acquire(key):
            with lock:
                success_count[0] += 1

    # Start 20 threads trying to acquire
    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should only allow exactly 10 successes
    assert success_count[0] == 10, f"Expected 10 successes, got {success_count[0]}"


def test_rate_limiter_backwards_compatibility():
    """Test that old is_limited/record pattern still works."""
    limiter = SlidingWindowLimiter(max_attempts=3, window_seconds=60)
    key = "compat_user"
    limiter.reset(key)

    # Old pattern should still work
    assert not limiter.is_limited(key)
    limiter.record(key)
    assert not limiter.is_limited(key)
    limiter.record(key)
    assert not limiter.is_limited(key)
    limiter.record(key)
    assert limiter.is_limited(key)
