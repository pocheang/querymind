"""The five guards on the admin user routes, and what each of them refuses.

`validate_and_check_approval_token` already has its own file. The other five in
`app/services/security/admin_security.py` had no test at all, which is the
asymmetry a coverage pass over the security modules found: the invariant
*definitions* next door sit at 94-100% (`privacy/dlp.py`, `rbac.py`,
`access_scope.py`) against 50% for the plumbing that applies them. The rules are
tested; the gates are not.

Every one of these is reached from `app/api/routes/admin/users.py` -- three from
`create-admin`, `reset-password` and `reset-approval-token`, two from the role
and status updates -- and each returns `None` on the accepting path. That is the
same property `test_approval_token_has_one_definition.py` pins for the token
check and it is pinned here for the same reason: a call site writes
`validate_ticket_id(ticket_id)` and discards nothing, so the day one of these
returns `False` instead of raising, an admin route carries straight on past a
rejected input.

**Two of them were correct only because of what their callers do**, and both
were changed in the commit that added this file rather than asserted as they
stood -- a test that pins accidental correctness is worse than no test, because
it makes the accident look like a decision:

- `check_self_modification` stringified the actor's id and not the target's, so
  `"1" == 1` was False and an admin holding an integer id could act on their own
  account. Unreachable today: every `user_id` on those routes is annotated
  `str`, so FastAPI coerces it.
- `validate_ticket_id` anchored with `$`, which in Python also matches just
  before a trailing newline -- so `"JIRA-123\n"` validated. Unreachable today
  too: all three call sites `.strip()` first. An accepted ticket id goes into an
  audit `detail`, where a newline is a forged row.

Neither changes behaviour for any existing caller. Both remove a refusal that
depended on somebody else cleaning the input first.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.security import admin_security


def _refusal(call) -> HTTPException:
    with pytest.raises(HTTPException) as raised:
        call()
    return raised.value


class TestSelfModification:
    """An admin may not act on their own account, whatever the operation."""

    def test_the_matching_id_is_refused(self) -> None:
        refusal = _refusal(lambda: admin_security.check_self_modification("u-1", {"user_id": "u-1"}, "admin.user.role"))

        assert refusal.status_code == 403
        assert refusal.detail == "cannot modify your own account"

    def test_another_account_is_allowed_through(self) -> None:
        assert admin_security.check_self_modification("u-2", {"user_id": "u-1"}, "admin.user.role") is None

    def test_the_refusal_is_audited_before_it_raises(self) -> None:
        """A blocked self-modification that leaves no row is a silent refusal.

        The same shape as `handle_service_exception`, which audits and then
        raises: moving the raise ahead of the callback stops recording the one
        event an admin audit exists for, and nothing else would report it.
        """

        audited: list[dict] = []

        _refusal(
            lambda: admin_security.check_self_modification(
                "u-1",
                {"user_id": "u-1", "role": "admin"},
                "admin.user.status",
                lambda request, **fields: audited.append(fields),
                object(),
            )
        )

        assert len(audited) == 1
        assert audited[0]["result"] == "blocked_self_modification"
        assert audited[0]["action"] == "admin.user.status"
        assert audited[0]["resource_id"] == "u-1"

    def test_it_still_refuses_with_no_audit_callback(self) -> None:
        """The audit is conditional on a callback and a request; the refusal is not.

        Two of the three call sites in `users.py` pass both, but the signature
        defaults them to None -- so a caller that cannot audit must still be
        stopped rather than quietly allowed.
        """

        assert _refusal(lambda: admin_security.check_self_modification("u-1", {"user_id": "u-1"}, "op")).status_code

    def test_an_actor_with_no_id_does_not_match_a_real_target(self) -> None:
        """`.get("user_id", "")` makes a missing actor id the empty string.

        If a target id could also be empty they would match and the refusal
        would fire on an unrelated account -- so the direction that matters is
        that a real target is not caught by an anonymous actor.
        """

        assert admin_security.check_self_modification("u-1", {}, "op") is None

    def test_both_sides_are_stringified(self) -> None:
        """Not a type-coercion nicety: this is the refusal failing open.

        The guard used to stringify the actor's id alone, so an integer id on
        both sides compared unequal and the admin was allowed through against
        their own account.
        """

        assert _refusal(lambda: admin_security.check_self_modification(1, {"user_id": 1}, "op")).status_code == 403


class TestAdminRolePromotion:
    """`PATCH /admin/users/{id}/role` may not mint an administrator."""

    @pytest.mark.parametrize("role", ["admin", "ADMIN", "Admin", "AdMiN", " admin ", "\tadmin\n"])
    def test_every_spelling_of_admin_is_refused(self, role: str) -> None:
        """`normalize_string(lowercase=True)` is doing the work here.

        A plain `role == "admin"` reads as equivalent and lets `"ADMIN"` through,
        which is privilege escalation by letter case.
        """

        refusal = _refusal(lambda: admin_security.check_admin_role_change(role))

        assert refusal.status_code == 400
        assert "create-admin" in refusal.detail, "the refusal names the endpoint that can do this"

    @pytest.mark.parametrize("role", ["user", "viewer", "administrator", "admin2", "superadmin"])
    def test_an_ordinary_role_passes(self, role: str) -> None:
        """Including the ones that merely contain it: the test is equality on
        the normalized value, not a substring scan."""

        assert admin_security.check_admin_role_change(role) is None


class TestTicketId:
    """`PROJECT-NUMBER`, and nothing that merely contains one."""

    @pytest.mark.parametrize("ticket", ["JIRA-123", "AB-1", "TICKET-456", "OPS-00042"])
    def test_a_well_formed_ticket_passes(self, ticket: str) -> None:
        assert admin_security.validate_ticket_id(ticket) is None

    @pytest.mark.parametrize("ticket", ["xJIRA-123", "JIRA-123x", " JIRA-123", "JIRA-123 ", "see JIRA-123 please"])
    def test_the_pattern_is_anchored_at_both_ends(self, ticket: str) -> None:
        r"""Unanchored, the check becomes "contains something ticket shaped",
        which is not a validation.

        Which half does the anchoring is worth stating, because the obvious
        reading is wrong: the leading `^` is redundant with `re.match`, and
        deleting it reddens nothing. The two halves that carry it are `.match`
        (start) and `\Z` (end) -- measured, a pattern unanchored at both ends
        reddens six of the tests in this class.
        """

        assert _refusal(lambda: admin_security.validate_ticket_id(ticket)).status_code == 400

    def test_a_trailing_newline_is_refused(self) -> None:
        """`$` matches before a trailing newline and `\\Z` does not.

        The ticket id is written into an audit `detail`, so a value carrying a
        newline is a row an operator reads as two.
        """

        assert _refusal(lambda: admin_security.validate_ticket_id("JIRA-123\n")).status_code == 400

    @pytest.mark.parametrize("ticket", ["jira-123", "Jira-123"])
    def test_the_project_is_upper_case(self, ticket: str) -> None:
        assert _refusal(lambda: admin_security.validate_ticket_id(ticket)).status_code == 400

    @pytest.mark.parametrize("ticket", ["JIRA-", "-123", "JIRA123", "123-JIRA"])
    def test_both_halves_are_required_in_that_order(self, ticket: str) -> None:
        assert _refusal(lambda: admin_security.validate_ticket_id(ticket)).status_code == 400

    @pytest.mark.parametrize("ticket", ["", "A", "AB"])
    def test_a_short_value_is_refused_by_the_length_check_first(self, ticket: str) -> None:
        """Two refusals with different wording, and the order decides which an
        operator is shown. The length check runs first, so an empty ticket id is
        reported as missing rather than as malformed."""

        refusal = _refusal(lambda: admin_security.validate_ticket_id(ticket))

        assert refusal.status_code == 400
        assert "minimum 3 characters" in refusal.detail


class TestReasonAndTokenLength:
    """Two length floors, asserted at the boundary rather than well inside it."""

    @pytest.mark.parametrize(("length", "accepted"), [(0, False), (4, False), (5, True), (6, True)])
    def test_the_reason_floor_is_five(self, length: int, accepted: bool) -> None:
        call = lambda: admin_security.validate_reason("x" * length)  # noqa: E731

        if accepted:
            assert call() is None
        else:
            assert _refusal(call).status_code == 400

    @pytest.mark.parametrize(("length", "accepted"), [(0, False), (11, False), (12, True), (13, True)])
    def test_the_approval_token_floor_is_twelve(self, length: int, accepted: bool) -> None:
        call = lambda: admin_security.validate_approval_token_length("x" * length)  # noqa: E731

        if accepted:
            assert call() is None
        else:
            assert _refusal(call).status_code == 400

    def test_the_floor_is_a_parameter_and_the_message_follows_it(self) -> None:
        """Both take a `min_length`, and no call site passes one today. The
        message has to be derived from it rather than written out, or a caller
        raising the floor gets a refusal quoting the old number."""

        assert "minimum 40 characters" in _refusal(lambda: admin_security.validate_reason("short", 40)).detail
        assert (
            "minimum 64 characters"
            in _refusal(lambda: admin_security.validate_approval_token_length("short", 64)).detail
        )


def test_no_guard_answers_a_refusal_with_a_return_value() -> None:
    """The property every call site in `users.py` depends on.

    None of them inspects a result -- `validate_ticket_id(ticket_id)` stands on
    its own line -- so a guard that returned False instead of raising would be
    dropped on the floor and the admin route would continue past a rejected
    input. Stated once over all five rather than per function, because it is one
    rule and a new guard in this module should inherit it.
    """

    refusals = [
        lambda: admin_security.check_self_modification("u-1", {"user_id": "u-1"}, "op"),
        lambda: admin_security.check_admin_role_change("admin"),
        lambda: admin_security.validate_ticket_id("nope"),
        lambda: admin_security.validate_reason(""),
        lambda: admin_security.validate_approval_token_length(""),
    ]

    for call in refusals:
        with pytest.raises(HTTPException):
            call()
