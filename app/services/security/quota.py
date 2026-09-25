"""Per-minute query and web-search quotas, per user or per business unit.

Wired on 2026-09-25. Until then `QuotaGuard` was constructed into every query
runtime and never called: its four settings gated nothing, and a pair of strict
xfails (`tests/security/test_quota_guard_is_not_wired.py`, now deleted) recorded
it. It also counted in process memory, so with several workers each would have
kept its own count and the effective limit would have been multiplied by the
worker count -- the ARC-01 defect. The counters come from `make_limiter`: Redis
with STATE_BACKEND=shared, one process otherwise.

Two gates, at the two places the cost is incurred:

- **Queries**, at the API edge beside the query load guard
  (`app/api/dependencies.py::_reserve_chat_credit`): over the quota is a 429
  with Retry-After, before anything runs.
- **Web searches**, inside retrieval (`app/knowledge/adapters.py::_retrieve_web`):
  one unit per search call, because that is what the search provider charges and
  throttles. A search the quota refuses is skipped and the question is answered
  from the other sources; only when every search of a question was refused does
  the web source fail, as `WebQuotaExceededError`, which the query route turns
  into a 429 when web was the only source there was.

`QUOTA_MODE=business_unit` counts a business unit together. The unit comes from
the user's profile, not from the signed-in user dict -- that dict does not carry
it, which is how the previous implementation would have counted per user in
business-unit mode without saying so.
"""

from __future__ import annotations

import threading

from app.core.config import get_settings
from app.services.security.rate_limiter import make_limiter

_WINDOW_SECONDS = 60


class QuotaExceededError(RuntimeError):
    """Over a quota; `retry_after` is when the oldest counted use leaves the window."""

    def __init__(self, message: str, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = max(1, int(retry_after))


class WebQuotaExceededError(QuotaExceededError):
    """Every web search this question planned was refused by the quota."""


class QuotaGuard:
    def __init__(self) -> None:
        settings = get_settings()
        self._query_limiter = make_limiter(
            "quota_query",
            max_attempts=max(1, int(getattr(settings, "quota_query_max_per_minute", 120) or 120)),
            window_seconds=_WINDOW_SECONDS,
        )
        self._web_limiter = make_limiter(
            "quota_web",
            max_attempts=max(1, int(getattr(settings, "quota_web_max_per_minute", 30) or 30)),
            window_seconds=_WINDOW_SECONDS,
        )
        self._mode = str(getattr(settings, "quota_mode", "user") or "user").strip().lower()

    @staticmethod
    def enabled() -> bool:
        return bool(getattr(get_settings(), "quota_enabled", False))

    def scope_key(self, user_id: str) -> str:
        """What is counted together: the business unit in that mode (when the user has one), else the user."""

        user_id = str(user_id or "").strip()
        if self._mode == "business_unit" and user_id:
            unit = _business_unit(user_id)
            if unit:
                return f"bu:{unit}"
        return f"user:{user_id}"

    def enforce_query_quota(self, user_id: str) -> None:
        """Count one query, or raise `QuotaExceededError`. Synchronous: call it off the event loop."""

        if not self.enabled():
            return
        key = self.scope_key(user_id)
        if not self._query_limiter.try_acquire(key):
            raise QuotaExceededError("query quota exceeded", self._query_limiter.get_limit_info(key)["retry_after"])

    def allow_web_search(self, user_id: str) -> bool:
        """Count one web search if the quota has room; False if it does not. Synchronous."""

        if not self.enabled():
            return True
        return self._web_limiter.try_acquire(f"web:{self.scope_key(user_id)}")

    def web_retry_after(self, user_id: str) -> int:
        return int(self._web_limiter.get_limit_info(f"web:{self.scope_key(user_id)}")["retry_after"])


def _business_unit(user_id: str) -> str:
    # The store directly, as app/services/models/config_store.py does: a service
    # must not import the API layer's `auth_service`. Only business-unit mode
    # pays for this read.
    from app.services.auth.auth_service import AuthDBService

    profile = AuthDBService().get_user_profile(user_id) or {}
    return str(profile.get("business_unit") or "").strip().lower()


_GUARD: QuotaGuard | None = None
_GUARD_LOCK = threading.Lock()


def get_quota_guard() -> QuotaGuard:
    """The process's guard. One instance, so the in-process counters (memory mode) are one set."""

    global _GUARD
    with _GUARD_LOCK:
        if _GUARD is None:
            _GUARD = QuotaGuard()
        return _GUARD


def reset_quota_guard() -> None:
    """Rebuild from current settings on the next use -- the limits and the mode are read at construction."""

    global _GUARD
    with _GUARD_LOCK:
        _GUARD = None
