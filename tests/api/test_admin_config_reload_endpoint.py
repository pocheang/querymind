"""`POST /admin/config/reload` answered 500 every time, and the reload had worked.

The endpoint built its response from `new_settings.retrieval_profile` -- a field
`Settings` has never had; the only mention of that name anywhere in the tree was
this one line. `Settings` is a pydantic model, so the read raised `AttributeError`,
and it raised *after* `apply_config_reload()` had run and after the audit row had
been written with `result="success"`. So the configuration really did reload, the
audit log said so, and the administrator was shown `配置热加载失败`.

Nothing reported it because nothing exercised it: the endpoint had no test at all,
and the frontend (`opsActions.ts::reloadConfig`) discards the response body, so the
only symptom was a toast. This is the failure this repository keeps recording --
a surface that reports the opposite of what ran -- reached through a hand-written
list of attribute names with nothing checking that the names exist.

The fix is not deleting the bad name. It is that the list is now data
(`RELOAD_SNAPSHOT_FIELDS`) and a test resolves every entry against
`Settings.model_fields`, so the next typo fails here rather than at a 500.
"""

from __future__ import annotations

from typing import Any

import pytest
from starlette.requests import Request

from app.api.routes.admin import settings as admin_settings
from app.core.config import Settings

ADMIN = {"user_id": "admin-1", "username": "ops-admin", "role": "admin", "permissions": ["admin:ops_manage"]}


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/admin/config/reload",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 0),
            "query_string": b"",
        }
    )


@pytest.fixture
def _reload(monkeypatch):
    """Drive the endpoint without touching the audit database or the real runtime."""

    audited: list[dict[str, Any]] = []
    monkeypatch.setattr(admin_settings, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(admin_settings, "_audit", lambda *a, **k: audited.append(dict(k)))
    monkeypatch.setattr(admin_settings, "apply_config_reload", Settings)
    monkeypatch.setattr(admin_settings, "get_global_model_settings", lambda: None)
    monkeypatch.setattr(admin_settings, "public_global_model_settings", lambda value: {"enabled": False})
    return audited


def test_the_reload_endpoint_answers_instead_of_raising(_reload):
    """The whole defect: this call used to raise AttributeError out of the handler."""

    body = admin_settings.admin_reload_config(_request(), ADMIN)

    assert body["ok"] is True
    assert body["reloaded_at"]
    assert body["snapshot"]["top_k"] == Settings().top_k


def test_the_reload_snapshot_only_names_real_settings_fields():
    """The guard the endpoint did not have.

    `retrieval_profile` was not a renamed field or a removed one -- it never
    existed. A name that resolves to nothing has to fail somewhere, and the
    choice is here or in an administrator's browser.
    """

    fields = set(Settings.model_fields)
    unknown = sorted(set(admin_settings.RELOAD_SNAPSHOT_FIELDS) - fields)

    assert unknown == [], f"the reload snapshot names fields Settings does not have: {unknown}"


def test_the_snapshot_reports_the_settings_the_reload_returned(_reload, monkeypatch):
    """Not `get_settings()`, which is what makes the value evidence of a reload."""

    reloaded = Settings(TOP_K="19")
    monkeypatch.setattr(admin_settings, "apply_config_reload", lambda: reloaded)

    body = admin_settings.admin_reload_config(_request(), ADMIN)

    assert body["snapshot"]["top_k"] == 19


def test_the_audit_row_is_written(_reload):
    """It was already written on the broken path -- the point is that it still is."""

    admin_settings.admin_reload_config(_request(), ADMIN)

    assert [row["result"] for row in _reload] == ["success"]
