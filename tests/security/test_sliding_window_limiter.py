"""What `SlidingWindowLimiter` actually enforces, and where it stops enforcing.

It is the counter behind every rate limit in this application -- the login and
register limiters in `app/api/dependencies.py`, the upload limiter, and the
per-user query rate inside `QueryLoadGuard` -- and it sat at 51%.
`tests/api/test_auth_route_rules.py` pins which *key* the login route builds;
this pins what the limiter does with one, which is the other half of the same
control and the half that decides whether anyone is actually stopped.

Four of its properties are not what a reader assumes from the method names, and
each is load-bearing somewhere:

- **`record` does not refuse.** It appends past `max_attempts`, so
  `attempts_used` can exceed the maximum and only `attempts_remaining` clamps.
  That is correct for the login route, which asks `is_limited` first and records
  a *failure* afterwards -- but it means `record` is not a gate and must never be
  read as one.
- **`is_limited` + `record` is not atomic; `try_acquire` is.** Two lock
  acquisitions against one, so the login route's pair can be raced past its
  ceiling by concurrent requests where the register route's cannot. Stated here
  rather than left to be discovered, because the two routes look symmetrical.
- **An empty key is unlimited in every method.** That is why the login route
  falls back to `"unknown"` rather than letting the username collapse to `""`.
- **A zero `max_attempts` becomes one, not zero and not unlimited.** A
  misconfigured `AUTH_LOGIN_MAX_FAILURES=0` therefore allows one attempt.

**One defect was found writing this, and fixed in the same commit.** `_events`
is a `defaultdict`, and both read-only methods reached it with `self._events[key]`
-- so *asking* whether a key was limited inserted that key. The login route asks
it with a key carrying the username the caller typed, before `auth_service` is
touched at all, so an unauthenticated caller varying the name grew the dict by
one permanent entry per name: measured, 1000 read-only `is_limited` calls left
1000 entries, and nothing anywhere sweeps them (`reset` runs only on a
*successful* login, and there is no equivalent of the token tracker's
`cleanup_expired`). Both readers use `.get` now and drop a key whose window has
emptied.

What that fix does **not** reach, and this file says so rather than implying
otherwise: a key created by `record` or `try_acquire` still outlives its window
until something asks about it again. That set is bounded by attempts actually
made rather than by names actually typed, which is a different order of
magnitude, but it is not zero.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import UTC, datetime, timedelta

import pytest

from app.services.security.rate_limiter import SlidingWindowLimiter


@pytest.fixture
def limiter() -> SlidingWindowLimiter:
    return SlidingWindowLimiter(max_attempts=3, window_seconds=60)


class TestTheCeiling:
    def test_max_attempts_is_a_count_of_allowed_attempts(self, limiter: SlidingWindowLimiter) -> None:
        """`>=` on the length, so the third is allowed and the fourth is not.

        Off by one in either direction is a real change: one way the limit is
        four, the other way a `max_attempts` of 1 refuses everything.
        """

        assert [limiter.try_acquire("k") for _ in range(5)] == [True, True, True, False, False]

    def test_is_limited_agrees_with_try_acquire_about_where_that_is(self, limiter: SlidingWindowLimiter) -> None:
        """Two methods, one ceiling. The login route reads one and the register
        route the other, so a disagreement would make the same configured
        number mean two different limits."""

        for _ in range(limiter.max_attempts - 1):
            limiter.record("k")
        assert limiter.is_limited("k") is False

        limiter.record("k")
        assert limiter.is_limited("k") is True

    def test_a_key_is_its_own_budget(self, limiter: SlidingWindowLimiter) -> None:
        for _ in range(limiter.max_attempts):
            limiter.try_acquire("a")

        assert limiter.try_acquire("a") is False
        assert limiter.try_acquire("b") is True

    def test_reset_returns_the_whole_budget(self, limiter: SlidingWindowLimiter) -> None:
        """What a successful login does. Without it, four typos and a correct
        password leave the account one mistake from a lockout it has already
        recovered from."""

        for _ in range(limiter.max_attempts):
            limiter.record("k")
        assert limiter.is_limited("k") is True

        limiter.reset("k")

        assert limiter.is_limited("k") is False


class TestTheWindowSlides:
    """Driven by rewriting the stored timestamps rather than by sleeping: a
    clock is a bad thing to assert on in CI, and the property is about which
    events `_trim` keeps, not about how fast the test runs."""

    @staticmethod
    def _age(limiter: SlidingWindowLimiter, key: str, seconds: float) -> None:
        limiter._events[key] = type(limiter._events[key])(
            stamp - timedelta(seconds=seconds) for stamp in limiter._events[key]
        )

    def test_an_event_older_than_the_window_stops_counting(self, limiter: SlidingWindowLimiter) -> None:
        for _ in range(limiter.max_attempts):
            limiter.record("k")
        assert limiter.is_limited("k") is True

        self._age(limiter, "k", 61)

        assert limiter.is_limited("k") is False

    def test_an_event_just_inside_the_window_still_counts(self, limiter: SlidingWindowLimiter) -> None:
        for _ in range(limiter.max_attempts):
            limiter.record("k")

        self._age(limiter, "k", 59)

        assert limiter.is_limited("k") is True

    def test_the_window_edge_is_inclusive(self, limiter: SlidingWindowLimiter) -> None:
        """`_trim` drops strictly-older events (`queue[0] < cutoff`), so an
        event exactly `window` old is kept. Flipping that to `<=` shortens every
        limit in the application by one tick -- invisible, and the direction
        that fails open.

        Asserted against `_trim` with an explicit `now` rather than through
        `is_limited`, because the exact case is not reachable from outside: the
        clock advances between aging an entry and asking about it, so "exactly
        60s" measured at record time is already 60.0001s by the time `cutoff` is
        computed. The first draft of this test went through `is_limited` and
        failed for that reason -- a boundary the public API cannot observe has
        to be tested on the thing that decides it.
        """

        now = datetime.now(UTC)
        exactly_at_the_edge = deque([now - limiter.window])
        one_microsecond_older = deque([now - limiter.window - timedelta(microseconds=1)])

        limiter._trim(exactly_at_the_edge, now)
        limiter._trim(one_microsecond_older, now)

        assert len(exactly_at_the_edge) == 1
        assert len(one_microsecond_older) == 0

    def test_only_the_expired_events_are_dropped(self, limiter: SlidingWindowLimiter) -> None:
        limiter.record("k")
        self._age(limiter, "k", 61)
        limiter.record("k")

        assert limiter.get_limit_info("k")["attempts_used"] == 1


class TestRecordIsNotAGate:
    def test_it_appends_past_the_ceiling(self) -> None:
        """So a caller must ask before recording. `record` returning None rather
        than a bool is the signature saying this, and it is asserted because the
        name does not."""

        limiter = SlidingWindowLimiter(max_attempts=2, window_seconds=60)

        for _ in range(5):
            assert limiter.record("k") is None

        assert limiter.get_limit_info("k")["attempts_used"] == 5

    def test_the_remaining_count_clamps_at_zero(self) -> None:
        """`attempts_used` is reported over the wire in the login route's 429
        body, so a negative remainder would reach a client."""

        limiter = SlidingWindowLimiter(max_attempts=2, window_seconds=60)
        for _ in range(5):
            limiter.record("k")

        assert limiter.get_limit_info("k")["attempts_remaining"] == 0


class TestTryAcquireIsAtomicAndTheOtherPairIsNot:
    def test_concurrent_callers_cannot_exceed_the_ceiling(self) -> None:
        """One lock acquisition covering both the check and the append.

        Ten threads racing for fifty slots must be granted exactly fifty. This
        is the property `record` + `is_limited` does not have, and the reason
        the register route uses this method.
        """

        limiter = SlidingWindowLimiter(max_attempts=50, window_seconds=600)
        granted: list[int] = []
        barrier = threading.Barrier(10)

        def worker() -> None:
            barrier.wait()
            for _ in range(20):
                if limiter.try_acquire("shared"):
                    granted.append(1)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(granted) == 50

    def test_a_refused_acquire_does_not_spend_a_slot(self) -> None:
        """Otherwise a caller already over the limit pushes the window forward
        on every attempt and can never recover -- a lockout that renews itself
        for as long as the client keeps retrying."""

        limiter = SlidingWindowLimiter(max_attempts=2, window_seconds=60)
        limiter.try_acquire("k")
        limiter.try_acquire("k")

        for _ in range(5):
            assert limiter.try_acquire("k") is False

        assert limiter.get_limit_info("k")["attempts_used"] == 2


class TestAnEmptyKeyIsUnlimited:
    """Every method treats it as "no subject", which is why the login route
    substitutes `"unknown"` rather than letting a blank username through."""

    def test_nothing_is_limited(self) -> None:
        limiter = SlidingWindowLimiter(max_attempts=1, window_seconds=60)

        assert limiter.is_limited("") is False
        assert [limiter.try_acquire("") for _ in range(5)] == [True] * 5
        assert limiter.record("") is None
        assert limiter.reset("") is None

    def test_it_reports_a_full_budget_rather_than_zeros(self) -> None:
        """A caller rendering this into a message must not tell somebody they
        have no attempts left when in fact nothing is counting them."""

        limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)

        assert limiter.get_limit_info("") == {
            "attempts_used": 0,
            "attempts_remaining": 5,
            "max_attempts": 5,
            "window_seconds": 60,
            "retry_after": 0,
        }


class TestRetryAfter:
    def test_it_is_zero_while_the_budget_holds(self, limiter: SlidingWindowLimiter) -> None:
        limiter.record("k")

        assert limiter.get_limit_info("k")["retry_after"] == 0

    def test_it_counts_down_to_the_oldest_event_leaving_the_window(self, limiter: SlidingWindowLimiter) -> None:
        """When the *next slot* frees, not when the window clears entirely.

        The login route renders this as "retry in N minutes", so a value
        measured from the newest event would tell a locked-out user to wait far
        longer than they must.
        """

        limiter.record("k")
        TestTheWindowSlides._age(limiter, "k", 50)
        for _ in range(limiter.max_attempts - 1):
            limiter.record("k")

        assert limiter.get_limit_info("k")["retry_after"] == pytest.approx(10, abs=1)

    def test_the_events_must_differ_in_age_for_that_to_mean_anything(self, limiter: SlidingWindowLimiter) -> None:
        """A note on how the test above is built, kept as an assertion.

        Its first draft aged the whole queue uniformly, so every event carried
        the same timestamp and `queue[0]` equalled `queue[-1]`: reading the
        newest event instead of the oldest passed it. Found by mutation, not by
        reading. The spread is what makes the choice observable, so it is
        asserted rather than left as a setup detail somebody tidies away.
        """

        limiter.record("k")
        TestTheWindowSlides._age(limiter, "k", 50)
        limiter.record("k")

        stamps = list(limiter._events["k"])
        assert stamps[0] != stamps[-1]


class TestAMisconfiguredLimit:
    @pytest.mark.parametrize("configured", [0, -5])
    def test_a_non_positive_maximum_becomes_one(self, configured: int) -> None:
        """Not zero and not unlimited. Worth stating because both other readings
        are plausible and one of them removes the limit entirely."""

        limiter = SlidingWindowLimiter(max_attempts=configured, window_seconds=60)

        assert limiter.max_attempts == 1
        assert [limiter.try_acquire("k") for _ in range(3)] == [True, False, False]

    @pytest.mark.parametrize("configured", [0, -5])
    def test_a_non_positive_window_becomes_one_second(self, configured: int) -> None:
        limiter = SlidingWindowLimiter(max_attempts=3, window_seconds=configured)

        assert limiter.window.total_seconds() == 1


class TestAskingIsNotRecording:
    """The defect this file's docstring describes, from the direction that
    matters: the read-only methods must not allocate.

    The login route asks `is_limited` with the username the caller typed, before
    any credential is checked, so an allocating read is unbounded memory growth
    driven by an unauthenticated stranger.
    """

    def test_a_thousand_questions_leave_nothing_behind(self) -> None:
        limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)

        for index in range(1000):
            assert limiter.is_limited(f"login::1.2.3.4::user{index}") is False

        assert limiter._events == {}

    def test_reading_the_limit_info_leaves_nothing_behind(self) -> None:
        limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)

        limiter.get_limit_info("never-seen")

        assert limiter._events == {}

    def test_a_key_whose_window_has_emptied_is_dropped(self) -> None:
        """A real attempt does allocate, and should: it is information. Once the
        window has passed it is not, so the next question drops it."""

        limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)
        limiter.record("k")
        assert "k" in limiter._events

        TestTheWindowSlides._age(limiter, "k", 61)
        limiter.is_limited("k")

        assert limiter._events == {}

    def test_the_limit_info_reader_drops_an_emptied_key_too(self) -> None:
        """Both readers, not just the one the login route happens to call first.

        `get_limit_info` runs on the 429 path, so it is asked about exactly the
        keys that have been hammered -- leaving it allocating would have kept
        the half of the growth that matters most.
        """

        limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)
        limiter.record("k")
        TestTheWindowSlides._age(limiter, "k", 61)

        assert limiter.get_limit_info("k")["attempts_used"] == 0
        assert limiter._events == {}

    def test_a_live_key_is_kept(self) -> None:
        """The direction that would break the limiter outright: dropping a key
        that still has events in its window resets somebody's budget on every
        question asked about them."""

        limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=60)
        limiter.record("k")

        limiter.is_limited("k")
        limiter.get_limit_info("k")

        assert limiter.get_limit_info("k")["attempts_used"] == 1
