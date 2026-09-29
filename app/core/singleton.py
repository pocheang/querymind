"""A lazily built, resettable process-wide instance.

Replaces the `global _x; if _x is None: _x = build()` shape that was repeated
across the code base: each copy re-implemented the lock (or forgot it), and the
`global` statement made the dependency invisible to readers and to tests, which
had to reach into module variables to reset it. Holding the state in one
object keeps it findable (`Singleton(...)` at module scope is what the
process-state scanner in `tests/core` looks for) and gives every user the same
locked construction.

Reads are lock-free once built; construction is serialized, and the factory may
itself ask for another singleton (the lock is reentrant).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class Singleton(Generic[T]):
    __slots__ = ("_factory", "_lock", "_value")

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._lock = threading.RLock()
        self._value: T | None = None

    def get(self) -> T:
        value = self._value
        if value is not None:
            return value
        with self._lock:
            if self._value is None:
                self._value = self._factory()
            return self._value

    def peek(self) -> T | None:
        """The instance if one exists; never builds."""
        return self._value

    def reset(self) -> T | None:
        """Forget the instance so the next `get` builds a new one; returns the old one."""
        with self._lock:
            old, self._value = self._value, None
        return old

    def set(self, value: T | None) -> None:
        with self._lock:
            self._value = value


class Cell(Generic[T]):
    """A named, mutable slot for process-wide state that is not built lazily.

    Flags ("installed"), a cache entry, the last thread started. Holding it in
    an object means writing it needs no `global` statement, and a test can
    replace it with `monkeypatch.setattr(module.CELL, "value", ...)`.
    """

    __slots__ = ("value",)

    def __init__(self, value: T) -> None:
        self.value = value
