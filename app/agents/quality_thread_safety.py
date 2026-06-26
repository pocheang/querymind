"""
Thread Safety Utilities for Quality Assurance Agents (P3-15).

Provides thread-safe wrappers for shared resources in high-concurrency scenarios.
"""

import threading
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, Optional


class ThreadSafeContextStore:
    """
    Thread-safe wrapper for Context Tracker's context store.

    Use this in production for high-concurrency environments where multiple
    requests may update the same session simultaneously.
    """

    def __init__(self):
        """Initialize with a lock."""
        self._store: Dict[str, Any] = {}
        self._lock = threading.RLock()  # Reentrant lock for nested calls

    def get(self, session_id: str) -> Optional[Any]:
        """Thread-safe get."""
        with self._lock:
            return self._store.get(session_id)

    def set(self, session_id: str, context: Any) -> None:
        """Thread-safe set."""
        with self._lock:
            self._store[session_id] = context

    def delete(self, session_id: str) -> bool:
        """Thread-safe delete."""
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False

    def keys(self) -> list:
        """Thread-safe keys."""
        with self._lock:
            return list(self._store.keys())

    def items(self):
        """Thread-safe items iterator."""
        with self._lock:
            # Return a copy to avoid concurrent modification
            return list(self._store.items())

    def __len__(self):
        """Thread-safe length."""
        with self._lock:
            return len(self._store)

    def clear(self):
        """Thread-safe clear."""
        with self._lock:
            self._store.clear()


class ThreadSafeCache:
    """
    Thread-safe LRU cache for concurrent access.

    Use this for router decisions, validation results, etc. in production.
    """

    def __init__(self, max_size: int = 100):
        """Initialize cache with lock."""
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Thread-safe get with LRU update."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        """Thread-safe set with LRU eviction."""
        with self._lock:
            if key in self._cache:
                # Update existing
                self._cache.move_to_end(key)
            else:
                # Add new
                if len(self._cache) >= self._max_size:
                    # Evict oldest
                    self._cache.popitem(last=False)

            self._cache[key] = value

    def clear(self) -> None:
        """Thread-safe clear."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, int]:
        """Thread-safe stats."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }


class ThreadSafeCounter:
    """
    Thread-safe counter for metrics and statistics.

    Use for tracking validation counts, error rates, etc.
    """

    def __init__(self, initial: int = 0):
        """Initialize counter."""
        self._value = initial
        self._lock = threading.Lock()

    def increment(self, delta: int = 1) -> int:
        """Increment and return new value."""
        with self._lock:
            self._value += delta
            return self._value

    def decrement(self, delta: int = 1) -> int:
        """Decrement and return new value."""
        with self._lock:
            self._value -= delta
            return self._value

    def get(self) -> int:
        """Get current value."""
        with self._lock:
            return self._value

    def set(self, value: int) -> None:
        """Set value."""
        with self._lock:
            self._value = value

    def reset(self) -> int:
        """Reset to 0 and return old value."""
        with self._lock:
            old = self._value
            self._value = 0
            return old


# Usage examples and migration guide:
"""
# 1. Context Tracker - Replace global dict with thread-safe store:

# Before (not thread-safe):
_context_store: Dict[str, ConversationContext] = {}

# After (thread-safe):
from app.agents.quality_thread_safety import ThreadSafeContextStore
_context_store = ThreadSafeContextStore()

# 2. Shared Cache - Replace with thread-safe cache:

# Before:
_cache = {}

# After:
from app.agents.quality_thread_safety import ThreadSafeCache
_cache = ThreadSafeCache(max_size=500)

# 3. Metrics - Use thread-safe counter:

from app.agents.quality_thread_safety import ThreadSafeCounter

validation_count = ThreadSafeCounter()
error_count = ThreadSafeCounter()

# In your code:
validation_count.increment()
if error:
    error_count.increment()

# Get stats:
total = validation_count.get()
errors = error_count.get()
error_rate = errors / total if total > 0 else 0
"""


# Note: For production deployment with high concurrency:
# 1. Replace context_tracker_agent._context_store with ThreadSafeContextStore
# 2. Replace shared_cache caches with ThreadSafeCache
# 3. Use ThreadSafeCounter for any shared metrics
#
# These changes are backward compatible - the API is the same, just thread-safe.
