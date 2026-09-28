"""One load at a time for a process-wide cached model loader.

`functools.lru_cache` does not lock: two threads that miss the cache together
both run the function. For a model loader that is two copies of a multi-second,
multi-gigabyte load -- the startup warm-up and the first request that arrives
before it finishes, or two concurrent first requests. Wrapping the cached loader
makes every caller after the first wait for that one load and then read the
cache. Once loaded, the lock costs one uncontended acquire per call.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")

__all__ = ["single_flight"]


def single_flight(loader: Callable[[], T]) -> Callable[[], T]:
    """Serialize calls to a zero-argument cached loader; keeps its `cache_clear`."""

    lock = threading.Lock()

    @wraps(loader)
    def wrapper() -> T:
        with lock:
            return loader()

    # The reload path clears these caches by name (`clear_reranker_cache` and
    # friends); they must keep working through the wrapper.
    wrapper.cache_clear = loader.cache_clear  # type: ignore[attr-defined]
    wrapper.cache_info = loader.cache_info  # type: ignore[attr-defined]
    wrapper.__wrapped_loader__ = loader  # type: ignore[attr-defined]
    return wrapper
