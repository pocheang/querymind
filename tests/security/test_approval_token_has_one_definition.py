"""There is one definition of "is this approval token valid", and it refuses by raising.

Two functions called `validate_and_check_approval_token` existed until
2026-09-09, and they took their arguments in **different orders**:

    app/api/deps/admin.py         (token, actor, audit_callback, request, user, action)
    app/services/security/...     (token, actor, action, audit_callback, request, user, resource_id)

Nothing imported the first; all three call sites in `admin/users.py` take the
second. So it was dead code -- but the dangerous shape of dead code, because
writing the wrong order passes an action *name* where the audit callback
belongs, and the failure lands at the moment a refusal is being recorded. Found
by chasing a SonarCloud `python:S1481` on a discarded `token_ok`, which is a
reminder that the duplicated literal is rarely the defect and reading the sites
together is what exposes one.

The second half is what makes discarding that boolean safe. `_, token_mode = ...`
is only correct while a refusal **raises**; the day it returns `(False, mode)`
instead, three admin endpoints would carry on past a rejected approval token.
That is not a hypothesis about style, it is the property the call sites depend
on, so it is asserted rather than assumed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
NAME = "validate_and_check_approval_token"


def _definitions() -> list[str]:
    found = []
    for path in APP.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - a file that does not parse is a different failure
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == NAME:
                found.append(str(path.relative_to(APP.parent)).replace("\\", "/"))
    return sorted(found)


def test_there_is_exactly_one_definition():
    """A second one is not a duplicate to tidy: the orders disagreed."""

    assert _definitions() == ["app/services/security/admin_security.py"]


def test_every_call_site_takes_the_live_one():
    """An import of the retired module would compile and take the wrong order."""

    users = (APP / "api" / "routes" / "admin" / "users.py").read_text(encoding="utf-8")

    assert "from app.services.security.admin_security import" in users
    assert f"from app.api.deps.admin import {NAME}" not in users


def test_a_rejected_token_raises_rather_than_returning_false():
    """The property the call sites rely on when they discard the boolean.

    All three write `_, token_mode = ...`. That is safe only while the refusal
    is an exception; a returned False would be dropped on the floor and the
    endpoint would continue.
    """

    from fastapi import HTTPException

    from app.services.security import admin_security

    audited: list[dict] = []

    with pytest.raises(HTTPException) as raised:
        admin_security.validate_and_check_approval_token(
            "not-the-configured-token",
            "actor-1",
            "admin.user.create_admin",
            lambda request, **fields: audited.append(fields),
            None,
            {"user_id": "actor-1"},
        )

    assert raised.value.status_code == 403
    # And it says nothing about why, which is the point of the unified error.
    assert raised.value.detail == "unauthorized"


def test_the_refusal_is_audited_before_it_raises():
    """A rejected approval token that leaves no row is a silent refusal."""

    from fastapi import HTTPException

    from app.services.security import admin_security

    audited: list[dict] = []

    with pytest.raises(HTTPException):
        admin_security.validate_and_check_approval_token(
            "not-the-configured-token",
            "actor-1",
            "admin.user.create_admin",
            lambda request, **fields: audited.append(fields),
            None,
            {"user_id": "actor-1"},
        )

    assert len(audited) == 1
    assert audited[0]["result"] == "failed"
    assert audited[0]["action"] == "admin.user.create_admin"
    # The mode is reported; the configured hash never is.
    assert "approval_failed" in audited[0]["detail"]
