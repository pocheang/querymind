"""A change spanning two documents is two publishes, and they are not one write.

`write_config_values` routes each edited key back to the document that already
defines it, so an ordinary two-field save is two `publish` calls against an
external system. The second one can fail after the first has landed.

That case raised `ConfigWriteRefused`, so the endpoint audited
`result="failure"`, answered 400, and said "refused" -- for a change one half of
which was already in the configuration centre. It also skipped
`apply_config_reload()`, so the process went on serving the old values while the
centre held the new ones, and the change then took effect on its own up to
`NACOS_POLL_INTERVAL_MS` later, with nothing connecting it to the save that had
been reported as rejected.

**Rolling the written half back was considered and rejected.** The rollback is
one more publish against the system that has just failed, so it can fail too and
leave a third state nobody has described; and the centre owns version history and
rollback, which is exactly why `write_config_values` rewrites documents whole
rather than merging. So the residue is named instead -- the same reasoning
`ConnectorMetadataRepository` records for its deletion order, where which residue
an interrupted operation leaves *is* the design.

What is pinned here is therefore the three things a reader of the audit log or
the response needs: which documents landed, that the process was reloaded onto
them, and that the answer is not "your input was rejected".
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.application import config_reload
from app.api.routes.admin import config as admin_config

ADMIN = {"user_id": "admin-1", "username": "ops-admin", "role": "admin", "permissions": ["admin:ops_manage"]}


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/admin/config/values",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 0),
            "query_string": b"",
        }
    )


class FlakyDocuments:
    """A centre that accepts every document but one."""

    def __init__(self, rejects: str, raises: bool = False) -> None:
        self._rejects = rejects
        self._raises = raises
        self.published: list[str] = []

        class _Config:
            data_ids = ("querymind-base", "querymind-retrieval")
            group = "DEFAULT_GROUP"

        self.config = _Config()

    def all(self) -> dict[str, str]:
        return {"querymind-base": "TOP_K=7\n", "querymind-retrieval": "RERANKER_TOP_N=5\n"}

    def publish(self, data_id: str, values: dict[str, str]) -> bool:
        if data_id == self._rejects:
            if self._raises:
                raise RuntimeError("connection reset")
            return False
        self.published.append(data_id)
        return True


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch):
    monkeypatch.setattr(admin_config, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(admin_config, "_require_permission", lambda *a, **k: None)
    monkeypatch.delenv("TOP_K", raising=False)
    monkeypatch.delenv("RERANKER_TOP_N", raising=False)


@pytest.fixture
def _reloads(monkeypatch):
    reloads: list[int] = []
    monkeypatch.setattr(config_reload, "remote_config_enabled", lambda: True)
    monkeypatch.setattr(admin_config, "remote_config_enabled", lambda: True)
    monkeypatch.setattr(config_reload, "apply_config_reload", lambda: reloads.append(1))
    return reloads


def _centre(monkeypatch, documents):
    monkeypatch.setattr(config_reload, "RemoteDocuments", lambda *a, **k: documents)
    monkeypatch.setattr(admin_config, "RemoteDocuments", lambda *a, **k: documents)
    return documents


# --- the write path -------------------------------------------------------


def test_a_second_document_failing_is_reported_as_partly_applied(monkeypatch, _reloads):
    """`querymind-base` is written first (sorted), then `querymind-retrieval` fails."""

    documents = _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval"))

    with pytest.raises(config_reload.ConfigWritePartiallyApplied) as excinfo:
        config_reload.write_config_values({"TOP_K": "9", "RERANKER_TOP_N": "6"})

    assert documents.published == ["querymind-base"]
    assert excinfo.value.written == ["querymind-base"]
    assert excinfo.value.failed == "querymind-retrieval"


def test_the_process_is_reloaded_onto_what_the_centre_now_holds(monkeypatch, _reloads):
    """Otherwise the page shows one configuration and the process runs another.

    The change lands anyway when the poller next notices, so not reloading buys
    nothing and costs the connection between the save and its effect.
    """

    _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval"))

    with pytest.raises(config_reload.ConfigWritePartiallyApplied):
        config_reload.write_config_values({"TOP_K": "9", "RERANKER_TOP_N": "6"})

    assert _reloads == [1]


def test_the_first_document_failing_is_a_plain_refusal(monkeypatch, _reloads):
    """Nothing landed, so nothing has to be described -- and nothing is reloaded."""

    documents = _centre(monkeypatch, FlakyDocuments(rejects="querymind-base"))

    with pytest.raises(config_reload.ConfigWriteRefused) as excinfo:
        config_reload.write_config_values({"TOP_K": "9", "RERANKER_TOP_N": "6"})

    assert not isinstance(excinfo.value, config_reload.ConfigWritePartiallyApplied)
    assert documents.published == []
    assert _reloads == []


def test_a_raising_client_is_treated_the_same_as_a_refusing_one(monkeypatch, _reloads):
    """A dropped connection leaves exactly the residue a rejection does."""

    _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval", raises=True))

    with pytest.raises(config_reload.ConfigWritePartiallyApplied, match="connection reset"):
        config_reload.write_config_values({"TOP_K": "9", "RERANKER_TOP_N": "6"})


def test_documents_are_written_in_a_deterministic_order(monkeypatch, _reloads):
    """So which half survives is a property of the change, not of dict ordering.

    The same edit is submitted with its keys the other way round; the document
    that lands is the same one.
    """

    documents = _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval"))

    with pytest.raises(config_reload.ConfigWritePartiallyApplied):
        config_reload.write_config_values({"RERANKER_TOP_N": "6", "TOP_K": "9"})

    assert documents.published == ["querymind-base"]


def test_a_change_that_all_lands_still_returns_normally(monkeypatch, _reloads):
    """The refusals prove nothing if the accepting path has stopped working."""

    _centre(monkeypatch, FlakyDocuments(rejects="nothing-at-all"))

    assert config_reload.write_config_values({"TOP_K": "9", "RERANKER_TOP_N": "6"}) == [
        "querymind-base",
        "querymind-retrieval",
    ]
    assert _reloads == [1]


# --- how the endpoint reports it -----------------------------------------


def test_the_endpoint_answers_503_rather_than_400(monkeypatch, _reloads):
    """400 says the administrator's input was wrong. It was not.

    The same line this repository already draws on the retrieval path: 500 sends
    an operator to look at this service, 503 at what it depends on.
    """

    _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval"))
    payload = admin_config.ConfigValues(values={"TOP_K": "9", "RERANKER_TOP_N": "6"})

    with pytest.raises(HTTPException) as excinfo:
        admin_config.admin_save_config(payload, _request(), ADMIN)

    assert excinfo.value.status_code == 503


def test_the_answer_names_what_landed_and_does_not_say_refused(monkeypatch, _reloads):
    _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval"))
    payload = admin_config.ConfigValues(values={"TOP_K": "9", "RERANKER_TOP_N": "6"})

    with pytest.raises(HTTPException) as excinfo:
        admin_config.admin_save_config(payload, _request(), ADMIN)

    detail = str(excinfo.value.detail)
    assert "querymind-base" in detail
    assert "querymind-retrieval" in detail
    assert "refused" not in detail.lower()


def test_the_audit_row_says_which_documents_landed(monkeypatch, _reloads):
    """A row reading "refused: TOP_K; RERANKER_TOP_N" describes a state that does
    not exist, and leaves the reader no way to know what to re-apply."""

    rows: list[dict] = []
    monkeypatch.setattr(admin_config, "_audit", lambda *a, **k: rows.append(dict(k)))
    _centre(monkeypatch, FlakyDocuments(rejects="querymind-retrieval"))
    payload = admin_config.ConfigValues(values={"TOP_K": "9", "RERANKER_TOP_N": "6"})

    with pytest.raises(HTTPException):
        admin_config.admin_save_config(payload, _request(), ADMIN)

    assert len(rows) == 1
    assert rows[0]["result"] == "failure"
    assert rows[0]["resource_id"] == "querymind-base"
    assert "partially applied" in rows[0]["detail"]
    assert "refused" not in rows[0]["detail"]


def test_an_ordinary_refusal_still_answers_400(monkeypatch, _reloads):
    """The 503 must not swallow the case it was carved out of."""

    _centre(monkeypatch, FlakyDocuments(rejects="querymind-base"))
    payload = admin_config.ConfigValues(values={"TOP_K": "9", "RERANKER_TOP_N": "6"})

    with pytest.raises(HTTPException) as excinfo:
        admin_config.admin_save_config(payload, _request(), ADMIN)

    assert excinfo.value.status_code == 400
