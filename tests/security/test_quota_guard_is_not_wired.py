"""`QuotaGuard` is built on every query runtime and nothing ever calls it.

This file exists because the honest answer to "the quota module is 44% covered"
is not to write unit tests for it. Its uncovered lines are `_scope_key`,
`enforce_query_quota` and `enforce_web_quota` -- which is to say the coverage
gap *is* the unreachability, and covering it would produce a control that is
written, tested and unreachable: the most expensive version of the failure
CLAUDE.md keeps recording, manufactured deliberately.

The shape is unusually clear here because the wired guard sits on the adjacent
line. `_build_query_runtime` constructs a `QueryLoadGuard` and a `QuotaGuard`
into the same frozen `QueryRuntime`; `_reserve_chat_credit` opens
`get_query_runtime().query_guard.acquire(user_key)` on every query entry point,
and `quota_guard` is never read again by anything. Four `Settings` fields --
`QUOTA_ENABLED`, `QUOTA_QUERY_MAX_PER_MINUTE`, `QUOTA_WEB_MAX_PER_MINUTE`,
`QUOTA_MODE` -- gate nothing, and none of them appears in any layer under
`config/`. They survive `test_settings_have_readers` because `QuotaGuard.__init__`
reads them, which is that guard's documented blind spot: assigning a field to an
attribute nobody reads counts as a reader.

`scripts/audit/reachability.py` does not report it either. It resolves a method
as reachable once its class is constructed somewhere in `app/`, and `QuotaGuard()`
is. That is not a defect in the tool so much as the same limit already recorded
for `test_every_modality_has_a_producer`: a static chain can confirm every link
exists and still miss that the last one is never traversed.

So this is a `xfail(strict=True)`, the idiom this repository already uses for a
gap that is real and should fail loudly the day it closes. Two outcomes are
correct and nothing else is: the enforcement gets a call site, at which point
these XPASS strictly and the suite stays red until somebody deletes this file
and writes real tests for a live control; or the decision is that per-user
quotas are not wanted, and the class, the four settings and this file go
together. What must not happen is that it stays as it is and acquires a test
suite that makes it look guarded.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
QUOTA = APP / "services" / "security" / "quota.py"


def _is_called_in_app(method: str) -> bool:
    """True when some module in `app/` calls `<something>.<method>(...)`.

    An attribute call rather than a bare name, because these are methods and the
    call sites would read `runtime.quota_guard.enforce_query_quota(user)`. The
    defining module is excluded so a recursive call could not satisfy it.
    """

    for path in APP.rglob("*.py"):
        if path == QUOTA:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - a file that does not parse is a different failure
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == method:
                return True
    return False


def test_the_load_guard_next_to_it_is_wired() -> None:
    """The control, and the reason the xfails below are a finding rather than a
    description of how this codebase happens to be written.

    Both guards are built into the same `QueryRuntime`. One of them is reached
    from every query; if this ever stops being true the two xfails mean
    something else entirely, so it is asserted rather than assumed.
    """

    assert _is_called_in_app("acquire"), "QueryLoadGuard.acquire has lost its call site too"


@pytest.mark.xfail(strict=True, reason="QuotaGuard is constructed per runtime and never called")
def test_the_query_quota_is_enforced_somewhere() -> None:
    assert _is_called_in_app("enforce_query_quota")


@pytest.mark.xfail(strict=True, reason="QuotaGuard is constructed per runtime and never called")
def test_the_web_quota_is_enforced_somewhere() -> None:
    assert _is_called_in_app("enforce_web_quota")


def test_the_guard_is_still_built_into_every_query_runtime() -> None:
    """Which is what makes it look wired to a reader of `dependencies.py`.

    If `quota_guard` is dropped from `QueryRuntime` the gap has been closed by
    deletion -- also a correct outcome -- and this file should go with it.
    """

    from app.api.dependencies import QueryRuntime

    assert "quota_guard" in QueryRuntime.__annotations__
