"""What "single-use" means for an admin approval token, and for how long.

`validate_admin_approval_token` is the last thing between a caller and
`POST /admin/users/create-admin`, which mints an administrator.
`test_approval_token_has_one_definition.py` pins that there is one definition of
it and that a refusal raises; nothing pinned what it decides. The module sat at
46%.

**"Single-use" is single-use for `expiry_hours`, not forever**, and that is the
first thing to know before reading this module. `is_token_used` returns True only
while the *used-record* is younger than the expiry; past it the record is deleted
and the same token validates again. Measured: first call `(True, "hash")`, second
`(False, "already_used")`, and after aging the record 25 hours, `(True, "hash")`
again.

That is defensible as a rate limit on a long-lived configured secret -- there is
one `ADMIN_CREATE_APPROVAL_TOKEN_HASH`, so a strict single-use would make the
endpoint work exactly once per rotation -- but the class docstring calls it
"single-use and expiration mechanisms" as though those were two features rather
than one undoing the other. It is pinned here rather than changed, because which
of the two it should be is a decision about the product, not a defect to fix in a
test commit. The test is written so that changing it fails loudly.

**Two methods on this class have no caller anywhere in `app/`**: `cleanup_expired`
and `get_usage_stats`. They are not covered here, for the reason
`test_quota_guard_is_not_wired.py` gives at length -- with one exception, the
boundary test below, which exists because `cleanup_expired` and `is_token_used`
independently decide the same thing and a disagreement between them would hand a
spent token back early.

Two things were changed in the commit that added this file, both the
caller-dependent shape already recorded for `admin_security`:

- `configured_hash` is normalized inside the function. The digest is lowercase
  hex and the one live call site lowercases before calling, so an operator's
  upper-case hash works only by that caller's grace -- verified, it returned
  `(False, "hash")` before.
- `token_tracker = get_token_tracker()` at module scope was deleted. Nothing
  imported it, and it constructed the global at import, so the lazy getter
  beside it had never once been the thing that created the tracker.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading

import pytest

from app.services.security import admin_token_tracker as tracker_module
from app.services.security.admin_token_tracker import AdminTokenTracker, validate_admin_approval_token

TOKEN = "an-operator-chosen-approval-token"
HASH = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()


@pytest.fixture
def tracker(tmp_path) -> AdminTokenTracker:
    # The records are rows in app.db since ARC-01 phase 2e; a test's go in a scratch file.
    return AdminTokenTracker(expiry_hours=24, db_path=tmp_path / "app.db")


def _age_record(tracker: AdminTokenTracker, digest: str, hours: float) -> None:
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("UPDATE admin_token_uses SET used_at = used_at - ? WHERE token_hash = ?", (hours * 3600, digest))


def _used_count(tracker: AdminTokenTracker) -> int:
    return tracker.get_usage_stats()["total_used_tokens"]


class TestTheHappyPathIsExactlyOnce:
    def test_the_configured_token_is_accepted(self, tracker: AdminTokenTracker) -> None:
        assert validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker) == (True, "hash")

    def test_the_second_use_is_refused(self, tracker: AdminTokenTracker) -> None:
        validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker)

        assert validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker) == (False, "already_used")

    def test_a_different_administrator_does_not_get_a_fresh_use(self, tracker: AdminTokenTracker) -> None:
        """The record is keyed on the token, not on who spent it. Keying it on
        the pair would give every administrator their own use of one secret,
        which is not what a shared approval token is for."""

        validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker)

        assert validate_admin_approval_token(TOKEN, HASH, "admin-2", tracker) == (False, "already_used")

    def test_the_token_is_only_spent_when_it_was_right(self, tracker: AdminTokenTracker) -> None:
        """A wrong guess must not burn the real token: otherwise anyone who can
        reach the endpoint can disable administrator creation for a day by
        submitting garbage."""

        assert validate_admin_approval_token("not-the-token", HASH, "attacker", tracker) == (False, "hash")

        assert validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker) == (True, "hash")


class TestSingleUseExpires:
    """The property this module's name does not say out loud."""

    def test_the_used_record_ages_out_and_the_token_works_again(self, tracker: AdminTokenTracker) -> None:
        validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker)
        assert validate_admin_approval_token(TOKEN, HASH, "admin-2", tracker) == (False, "already_used")

        _age_record(tracker, HASH, 25)

        assert validate_admin_approval_token(TOKEN, HASH, "admin-3", tracker) == (True, "hash"), (
            "single-use is scoped to expiry_hours; if this now refuses, the "
            "semantics changed and this file's docstring is the thing to update"
        )

    def test_the_record_is_still_held_just_inside_the_window(self, tracker: AdminTokenTracker) -> None:
        validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker)

        _age_record(tracker, HASH, 23)

        assert validate_admin_approval_token(TOKEN, HASH, "admin-2", tracker) == (False, "already_used")

    def test_a_shorter_expiry_is_honoured(self, tmp_path) -> None:
        """`expiry_hours` is a constructor argument and `get_token_tracker`
        hardcodes 24. Asserted separately so the window is known to follow the
        configured value rather than a constant that happens to match."""

        tracker = AdminTokenTracker(expiry_hours=1, db_path=tmp_path / "app.db")
        validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker)

        _age_record(tracker, HASH, 2)

        assert validate_admin_approval_token(TOKEN, HASH, "admin-2", tracker) == (True, "hash")

    def test_the_two_expiry_decisions_agree(self, tracker: AdminTokenTracker) -> None:
        """`cleanup_expired` has no caller today, and this is the one thing
        about it worth asserting: it must not remove a record `is_token_used`
        still counts.

        The two were written with complementary comparisons (`<` against `>=`)
        in different methods, so a future sweep -- a startup task, an operator
        endpoint -- that disagreed by one boundary would hand a spent token back
        early, silently, on the endpoint that creates administrators.
        """

        validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker)

        _age_record(tracker, HASH, 23)
        assert tracker.cleanup_expired() == 0
        assert tracker.is_token_used(HASH) is True

        _age_record(tracker, HASH, 2)
        assert tracker.is_token_used(HASH) is False, "is_token_used drops it first"

        validate_admin_approval_token(TOKEN, HASH, "admin-2", tracker)
        _age_record(tracker, HASH, 25)
        assert tracker.cleanup_expired() == 1, "and cleanup_expired agrees about which records those are"


class TestTheRefusalModes:
    """Four modes, and the audit row carries the one that fired. Two of them say
    something about the deployment rather than about the caller, which is what
    makes them worth distinguishing at all."""

    def test_no_configured_hash_is_missing_not_a_wrong_token(self, tracker: AdminTokenTracker) -> None:
        """An operator who never set `ADMIN_CREATE_APPROVAL_TOKEN_HASH` needs to
        read `mode=missing` in the audit row, not conclude somebody guessed."""

        assert validate_admin_approval_token(TOKEN, "", "admin-1", tracker) == (False, "missing")

    def test_an_absent_token_is_empty(self, tracker: AdminTokenTracker) -> None:
        assert validate_admin_approval_token("", HASH, "admin-1", tracker) == (False, "empty")

    @pytest.mark.parametrize("submitted", ["   ", "\t\n", None])
    def test_a_blank_submission_is_empty_rather_than_wrong(self, submitted, tracker: AdminTokenTracker) -> None:
        """Including None: the endpoint passes `req.approval_token or ""`, but
        the function takes the argument and must not depend on that."""

        assert validate_admin_approval_token(submitted, HASH, "admin-1", tracker) == (False, "empty")

    def test_a_wrong_token_and_a_right_one_share_a_mode(self, tracker: AdminTokenTracker) -> None:
        """`"hash"` means "a hash comparison decided this", not "it passed".

        Worth pinning because the audit detail reads `approval_failed; mode=hash`
        and a reader could take that for a distinct failure kind. The boolean is
        what says whether it was right.
        """

        assert validate_admin_approval_token("wrong", HASH, "a", tracker) == (False, "hash")
        assert validate_admin_approval_token(TOKEN, HASH, "a", tracker) == (True, "hash")

    def test_neither_refusal_spends_the_token(self, tracker: AdminTokenTracker) -> None:
        """`missing` and `empty` both return before the token is claimed. Claiming
        there would let an unconfigured deployment, or an empty POST, consume
        the real token."""

        validate_admin_approval_token(TOKEN, "", "a", tracker)
        validate_admin_approval_token("", HASH, "a", tracker)

        assert _used_count(tracker) == 0
        assert validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker) == (True, "hash")


class TestWhatIsNormalizedAndWhatIsNot:
    def test_the_submitted_token_is_stripped(self, tracker: AdminTokenTracker) -> None:
        """A token pasted out of a terminal carries whitespace, and rejecting it
        for that would be indistinguishable from the wrong token."""

        assert validate_admin_approval_token(f"  {TOKEN}\n", HASH, "admin-1", tracker) == (True, "hash")

    def test_the_configured_hash_is_case_folded(self, tracker: AdminTokenTracker) -> None:
        """The digest is lowercase hex. Before this was normalized inside the
        function, an upper-case configured hash returned `(False, "hash")` --
        indistinguishable from a wrong token, on the one endpoint whose refusal
        an operator most needs to understand."""

        assert validate_admin_approval_token(TOKEN, HASH.upper(), "admin-1", tracker) == (True, "hash")

    def test_the_configured_hash_is_stripped(self, tracker: AdminTokenTracker) -> None:
        assert validate_admin_approval_token(TOKEN, f"  {HASH}  ", "admin-1", tracker) == (True, "hash")

    def test_the_token_itself_is_case_sensitive(self, tracker: AdminTokenTracker) -> None:
        """Only the *hash* is hex and therefore case-free. Folding the secret
        would throw away entropy."""

        assert validate_admin_approval_token(TOKEN.upper(), HASH, "admin-1", tracker) == (False, "hash")


class TestTheTrackerIsOneObjectPerProcess:
    def test_the_getter_returns_the_same_instance(self) -> None:
        """Two trackers means a token spent against one is unspent against the
        other -- the same two-stores failure the approval store already has
        recorded for connector tokens."""

        assert tracker_module.get_token_tracker() is tracker_module.get_token_tracker()

    def test_it_is_built_lazily(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """`token_tracker = get_token_tracker()` used to run at import, so the
        `if _global_tracker is None` beside it had never once been the branch
        that created it. Deleted with the unused export."""

        monkeypatch.setattr(tracker_module, "_global_tracker", None)

        assert tracker_module.get_token_tracker() is not None

    def test_no_module_scope_instance_remains(self) -> None:
        """An eagerly-built global is an import-time side effect nothing asked
        for, and it is how the lazy path stopped being exercised."""

        assert not hasattr(tracker_module, "token_tracker")


class TestSingleUseHoldsAcrossWorkers:
    """ARC-01 phase 2e. The records were a dict per process, so "single-use" was
    single-use per worker; and "check it is unused, then mark it" let two
    requests on one worker through as well."""

    def test_a_token_spent_on_one_worker_is_spent_on_another(self, tmp_path) -> None:
        worker_a = AdminTokenTracker(expiry_hours=24, db_path=tmp_path / "app.db")
        worker_b = AdminTokenTracker(expiry_hours=24, db_path=tmp_path / "app.db")

        assert validate_admin_approval_token(TOKEN, HASH, "admin-1", worker_a) == (True, "hash")
        assert validate_admin_approval_token(TOKEN, HASH, "admin-2", worker_b) == (False, "already_used")

    def test_concurrent_uses_of_one_token_admit_exactly_one(self, tmp_path) -> None:
        outcomes: list[tuple[bool, str]] = []
        lock = threading.Lock()
        start = threading.Barrier(8)

        def attempt(index: int) -> None:
            tracker = AdminTokenTracker(expiry_hours=24, db_path=tmp_path / "app.db")
            start.wait()
            outcome = validate_admin_approval_token(TOKEN, HASH, f"admin-{index}", tracker)
            with lock:
                outcomes.append(outcome)

        threads = [threading.Thread(target=attempt, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert outcomes.count((True, "hash")) == 1
        assert all(outcome == (False, "already_used") for outcome in outcomes if outcome[0] is False)

    def test_the_race_is_settled_by_the_claim_not_by_the_check(self, tracker: AdminTokenTracker) -> None:
        """The deterministic form of the race above: the check says unused, and
        another request spends the token before this one claims it."""

        tracker.is_token_used = lambda digest: False  # the check lost the race
        assert tracker.claim(HASH, "admin-0") is True  # the other request's claim

        assert validate_admin_approval_token(TOKEN, HASH, "admin-1", tracker) == (False, "already_used")

    def test_an_expired_record_can_be_claimed_again(self, tracker: AdminTokenTracker) -> None:
        assert tracker.claim(HASH, "admin-1") is True
        assert tracker.claim(HASH, "admin-2") is False

        _age_record(tracker, HASH, 25)
        assert tracker.claim(HASH, "admin-2") is True
