"""The admin console's audit filter, and the helpers it is built from.

`_filter_audit_rows` is what every audit view in `app/api/routes/admin/ops.py`
narrows its rows with, and it had **no test at all**. That matters more here than
the coverage number suggests, because this function is the second half of a
failure this repository has already recorded once: the console offered sixteen
action filters and four of them could only ever return nothing, since they named
actions no module writes. A filter that matches no row reports "no results",
which is indistinguishable from a quiet afternoon.

`tests/security/test_audit_action_vocabulary.py` closed the naming half -- the
console's list is checked against `AuditAction` in both directions. What was
still unpinned is the *matching* half: the console assumes a case-insensitive
substring match on `action` and an exact match on the actor, and nothing said so.
The two rules are different, on one function, and neither was asserted.

`handle_service_exception` is the other untested piece here. It runs from six
`except` blocks in `admin/users.py`, so it executes precisely when an
administrative operation has already gone wrong -- and the thing it must not get
wrong is writing the audit row *before* it raises.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.api.deps.admin import (
    _filter_audit_rows,
    _parse_audit_ts,
    _parse_request_ts,
    handle_service_exception,
)
from app.services.security.audit_actions import AuditAction

CUTOFF = datetime(2026, 9, 1, tzinfo=UTC)
RECENT = "2026-09-10T12:00:00+00:00"
OLD = "2026-08-01T12:00:00+00:00"


def _row(action: str, actor: str = "u1", created_at: str = RECENT) -> dict:
    return {"action": action, "actor_user_id": actor, "created_at": created_at}


# --------------------------------------------------------------------------
# _filter_audit_rows: what the console actually asks of it
# --------------------------------------------------------------------------


def test_an_action_filter_matching_nothing_returns_nothing_rather_than_everything():
    """The documented failure, from the side the vocabulary test cannot see.

    A filter naming an action no module writes must return an empty list. It is
    the *combination* of this and a plausible-looking console option that made
    four filters dead for so long: the page says "no results", which is what an
    empty window looks like too. Returning every row instead would at least have
    been visible.
    """
    rows = [_row(AuditAction.AUTH_LOGIN), _row(AuditAction.AUTH_LOGOUT)]
    assert _filter_audit_rows(rows, CUTOFF, action_keyword="admin.user.create") == []
    # ...and the real name does match, so the assertion above is not passing
    # merely because the filter rejects everything.
    assert len(_filter_audit_rows(rows, CUTOFF, action_keyword=AuditAction.AUTH_LOGIN)) == 1


def test_the_action_filter_is_a_case_insensitive_substring():
    """Substring, not equality -- which is what makes a *near* miss silent."""
    rows = [_row(AuditAction.AUTH_LOGIN)]
    assert len(_filter_audit_rows(rows, CUTOFF, action_keyword="auth")) == 1
    assert len(_filter_audit_rows(rows, CUTOFF, action_keyword="AUTH.LOGIN")) == 1
    assert len(_filter_audit_rows(rows, CUTOFF, action_keyword="login")) == 1
    # A superstring is not a substring: asking for more than the row says matches
    # nothing, which is the shape the four dead console options had.
    assert _filter_audit_rows(rows, CUTOFF, action_keyword="auth.login.failed") == []


def test_the_actor_filter_is_exact_where_the_action_filter_is_not():
    """Two different matching rules on one function, stated once."""
    rows = [_row(AuditAction.AUTH_LOGIN, actor="alice")]
    assert len(_filter_audit_rows(rows, CUTOFF, actor_user_id="alice")) == 1
    # Substring semantics here would be a disclosure bug, not a convenience:
    # filtering by "alice" must not surface "alice2"'s rows.
    assert _filter_audit_rows(rows, CUTOFF, actor_user_id="alic") == []
    assert _filter_audit_rows([_row(AuditAction.AUTH_LOGIN, actor="alice2")], CUTOFF, actor_user_id="alice") == []


def test_blank_and_whitespace_filters_mean_no_filter():
    rows = [_row(AuditAction.AUTH_LOGIN, actor="alice")]
    for blank in (None, "", "   "):
        assert len(_filter_audit_rows(rows, CUTOFF, actor_user_id=blank)) == 1
        assert len(_filter_audit_rows(rows, CUTOFF, action_keyword=blank)) == 1


def test_filters_compose_as_and_not_or():
    rows = [
        _row(AuditAction.AUTH_LOGIN, actor="alice"),
        _row(AuditAction.AUTH_LOGOUT, actor="bob"),
    ]
    both = _filter_audit_rows(rows, CUTOFF, actor_user_id="alice", action_keyword="logout")
    assert both == [], "a row must satisfy every filter, not any of them"


def test_the_cutoff_drops_older_rows():
    rows = [_row(AuditAction.AUTH_LOGIN, created_at=RECENT), _row(AuditAction.AUTH_LOGOUT, created_at=OLD)]
    kept = _filter_audit_rows(rows, CUTOFF)
    assert [r["action"] for r in kept] == [AuditAction.AUTH_LOGIN]


def test_a_row_with_an_unreadable_timestamp_is_dropped_by_any_realistic_window():
    """Worth stating because it is a silent data loss, not an error.

    An unparseable `created_at` parses to the epoch, so it falls before every
    cutoff a console would ask for. A corrupted audit row therefore vanishes from
    the view rather than being flagged. That is defensible -- a row whose time is
    unknown cannot be placed in a time window -- but it should be a decision
    somebody made rather than one nobody noticed.
    """
    rows = [_row(AuditAction.AUTH_LOGIN, created_at="not-a-timestamp"), _row(AuditAction.AUTH_LOGOUT)]
    kept = _filter_audit_rows(rows, CUTOFF)
    assert [r["action"] for r in kept] == [AuditAction.AUTH_LOGOUT]
    # An epoch-wide window keeps it, which proves the row was dropped by the
    # cutoff rather than by the filter refusing to read it at all.
    assert len(_filter_audit_rows(rows, datetime.fromtimestamp(0, tz=UTC))) == 2


def test_a_missing_action_or_actor_key_does_not_raise():
    """The rows come from SQLite via `json.loads`; a missing key is possible."""
    assert _filter_audit_rows([{"created_at": RECENT}], CUTOFF, action_keyword="auth") == []
    assert _filter_audit_rows([{"created_at": RECENT}], CUTOFF, actor_user_id="alice") == []
    assert len(_filter_audit_rows([{"created_at": RECENT}], CUTOFF)) == 1


# --------------------------------------------------------------------------
# the two timestamp parsers
# --------------------------------------------------------------------------

TIMESTAMP_CASES = [
    (None, datetime.fromtimestamp(0, tz=UTC)),
    ("", datetime.fromtimestamp(0, tz=UTC)),
    ("not-a-timestamp", datetime.fromtimestamp(0, tz=UTC)),
    ("2026-09-10T12:00:00+00:00", datetime(2026, 9, 10, 12, tzinfo=UTC)),
    # naive is read as UTC rather than as local time -- otherwise the same row
    # lands in a different bucket depending on the server's timezone.
    ("2026-09-10T12:00:00", datetime(2026, 9, 10, 12, tzinfo=UTC)),
    ("2026-09-10T20:00:00+08:00", datetime(2026, 9, 10, 12, tzinfo=UTC)),
]


@pytest.mark.parametrize(("value", "expected"), TIMESTAMP_CASES)
def test_parse_audit_ts(value, expected):
    assert _parse_audit_ts(value) == expected


@pytest.fixture
def server_timezone(monkeypatch):
    """Set the process timezone for one test, and put it back properly.

    `monkeypatch.setenv` restores `os.environ`, but the C library caches the zone
    until `tzset()` is called again -- so undoing the variable without re-calling
    it leaves every later test running in whichever zone this one picked. The
    teardown is the point of the fixture.
    """
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset() is only available on Unix/Linux systems")

    def _set(name: str) -> None:
        monkeypatch.setenv("TZ", name)
        time.tzset()

    yield _set
    monkeypatch.undo()
    time.tzset()


# UTC first, deliberately: with it last the fixture's teardown is unfalsifiable,
# because the final tzset() would restore UTC by coincidence rather than by the
# teardown doing its job. Verified by sabotaging the teardown -- a sentinel test
# after this file goes red only in this order.
@pytest.mark.parametrize("tz", ["UTC", "Asia/Shanghai", "America/New_York"])
def test_a_naive_timestamp_is_read_as_utc_whatever_the_server_is_set_to(tz, server_timezone):
    """The case above cannot fail on a UTC machine, and this one can.

    `replace(tzinfo=UTC)` and `astimezone(UTC)` do the same thing to a naive
    datetime exactly when the process is running in UTC -- which CI and this
    container are. So the parametrized case pins the value without pinning the
    *rule*, and swapping one call for the other in the source turns nothing red.
    Found by mutating the source rather than by reading the test.

    The rule matters because these timestamps bucket the admin console's charts:
    read as local time, the same audit row lands in a different hour depending on
    where the server happens to be, and rows written before a deployment moved
    zone would silently disagree with rows written after.
    """
    server_timezone(tz)
    assert _parse_audit_ts("2026-09-10T12:00:00") == datetime(2026, 9, 10, 12, tzinfo=UTC)
    assert _parse_request_ts("2026-09-10T12:00:00") == datetime(2026, 9, 10, 12, tzinfo=UTC)


@pytest.mark.parametrize(("value", "expected"), TIMESTAMP_CASES)
def test_the_two_parsers_agree(value, expected):
    """`_parse_audit_ts` and `_parse_request_ts` are the same function twice.

    They read different fields at their call sites (`created_at` against `ts`)
    but their bodies are identical apart from the docstring, and both feed the
    same admin views. This is the guard `test_table_separator_regex.py` already
    applies to a pattern copied four times: assert the copies agree, so one of
    them cannot be fixed alone. One definition is the better end state and is not
    made here.
    """
    assert _parse_request_ts(value) == _parse_audit_ts(value) == expected


# --------------------------------------------------------------------------
# handle_service_exception
# --------------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def _raise_through(exc: Exception, resource_id: str | None = "u-1"):
    audit = _Recorder()
    with pytest.raises(HTTPException) as caught:
        handle_service_exception(
            exc,
            audit,
            request=object(),
            action=AuditAction.ADMIN_USER_ROLE_UPDATE,
            user={"user_id": "admin-1"},
            resource_id=resource_id,
        )
    return audit, caught.value


def test_the_failure_is_audited_before_it_is_raised():
    """The property the six call sites depend on.

    Every caller is an `except` block: the exception is already in flight, and
    this function's job is to record it and convert it. If the raise moved ahead
    of the callback, administrative failures would stop being audited and nothing
    would report that -- the audit log would simply be quieter.
    """
    audit, _ = _raise_through(ValueError("bad role"))
    assert len(audit.calls) == 1, "the audit row must be written even though the call raises"


def test_a_value_error_becomes_400_and_keeps_its_message():
    """A rejected input is the caller's fault and must say what was wrong."""
    _, exc = _raise_through(ValueError("role must be one of admin, user"))
    assert exc.status_code == 400
    assert "role must be one of" in str(exc.detail)


def test_any_other_exception_becomes_500_and_does_not_leak_its_message():
    """The mirror case: an unexpected failure says nothing about internals.

    A `KeyError` or a `sqlite3` error carries table names and internal state. The
    audit row keeps the detail -- that is what it is for -- and the HTTP response
    does not.
    """
    audit, exc = _raise_through(KeyError("users.secret_column"))
    assert exc.status_code == 500
    assert "secret_column" not in str(exc.detail)
    assert "secret_column" in audit.calls[0][1]["detail"], "the audit row must keep what the response drops"


def test_the_audit_row_names_the_exception_type_and_the_failure():
    audit, _ = _raise_through(ValueError("nope"))
    _, kwargs = audit.calls[0]
    assert kwargs["detail"].startswith("ValueError: ")
    assert kwargs["result"] == "failed"
    assert kwargs["action"] == AuditAction.ADMIN_USER_ROLE_UPDATE
    assert kwargs["resource_id"] == "u-1"


def test_the_resource_id_is_optional():
    """Three of the six call sites omit it (`create_admin` has no target yet)."""
    audit, exc = _raise_through(ValueError("nope"), resource_id=None)
    assert exc.status_code == 400
    assert audit.calls[0][1]["resource_id"] is None
