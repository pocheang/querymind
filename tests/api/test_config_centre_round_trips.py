"""How many times one saved change asks the configuration centre for a document.

Every `Settings()` construction runs `RemoteSettingsSource`, which fetches one
document per data id; `RemoteDocuments()` does the same. Neither is obvious at a
call site, so the count crept: one `POST /admin/config/values` used to cost about
six fetches per data id, all synchronous, inside a request handler, each bounded
only by `NACOS_TIMEOUT_MS` (3s by default). With three data ids and an unhealthy
centre that is a request that hangs for the better part of a minute.

Where they went, and why three of the five are gone:

- `validate_values` called `Settings(**values)`, so **type-checking a form did
  network I/O**. It supplies every field as an init argument and init outranks
  every source below it, so nothing the centre returns can change the answer --
  only cost a round trip to say so. `without_remote_config()` is that statement.
- the pinned check called `describe(...)`, which fetches every document to fill
  in a column the check does not read; only the environment layer can refuse a
  write, so it asks for that.
- `reload_settings()` built `Settings` twice, once to validate and once through
  `get_settings()`. That also meant the object installed was not the object
  validated, which the fetch count is a proxy for rather than the point.

What is left is what the operation genuinely needs: read the documents to rewrite
them whole, re-read on reload, and re-read once more to answer with the new state.

The number is asserted exactly, not as a ceiling. A ceiling far from reality is
this repository's recurring failure -- a check that cannot fire -- and the whole
reason this crept in the first place is that nothing counted.
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.application import config_reload
from app.api.routes.admin import config as admin_config
from app.core import remote_config
from app.core.config import Settings, get_settings
from app.core.config_schema import validate_values
from app.core.remote_config import RemoteConfigSettings, RemoteDocuments, without_remote_config

ADMIN = {"user_id": "admin-1", "username": "ops-admin", "role": "admin", "permissions": ["admin:ops_manage"]}

CONFIG = RemoteConfigSettings(
    enabled=True,
    server_addr="127.0.0.1:8848",
    namespace="",
    group="DEFAULT_GROUP",
    data_ids=("querymind-base", "querymind-retrieval"),
    username="",
    password="",
    timeout_ms=3000,
)


class CountingClient:
    """The real network boundary, counted."""

    def __init__(self) -> None:
        self.fetches: list[str] = []
        self.documents = {"querymind-base": "TOP_K=7\n", "querymind-retrieval": "RERANKER_TOP_N=5\n"}

    def fetch(self, group: str, data_id: str) -> str | None:
        self.fetches.append(data_id)
        return self.documents.get(data_id)

    def publish(self, group: str, data_id: str, content: str) -> bool:
        self.documents[data_id] = content
        return True


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


@pytest.fixture
def client(monkeypatch, tmp_path):
    """A real `RemoteDocuments` over a counting client, with no snapshot to hide behind."""

    counter = CountingClient()
    monkeypatch.setattr(remote_config, "SNAPSHOT_ROOT", tmp_path / "snapshots")
    monkeypatch.setattr(remote_config, "_bootstrap", lambda: CONFIG)
    monkeypatch.setattr(remote_config.RemoteDocuments, "_resolve_client", lambda self: counter, raising=False)
    monkeypatch.setattr(config_reload, "remote_config_enabled", lambda: True)
    monkeypatch.setattr(admin_config, "remote_config_enabled", lambda: True)
    monkeypatch.setattr(admin_config, "_audit", lambda *a, **k: None)
    monkeypatch.setattr(admin_config, "_require_permission", lambda *a, **k: None)
    monkeypatch.setattr(config_reload, "apply_config_reload", lambda: config_reload.reload_settings())
    monkeypatch.delenv("TOP_K", raising=False)
    get_settings.cache_clear()
    # Warm, because that is the state a running process is in: `get_settings` is
    # `lru_cache`d, so measuring from cold would count a construction the save did
    # not cause and hide the one it did.
    get_settings()
    yield counter
    get_settings.cache_clear()


def test_the_counter_sees_the_real_fetches(client):
    """A counter wired to nothing would make every assertion below read zero."""

    client.fetches.clear()

    RemoteDocuments(config=CONFIG).all()

    assert client.fetches == ["querymind-base", "querymind-retrieval"]


def test_type_checking_a_change_costs_no_round_trips(client):
    """It used to cost one per data id, as a side effect of `Settings(**values)`."""

    client.fetches.clear()

    validate_values({"TOP_K": "9"}, current=Settings.model_construct())

    assert client.fetches == []


def test_suppression_does_not_leak_past_the_block(client):
    """A `finally`, not trust: a failed validation must not switch the centre off."""

    with pytest.raises(ValueError):
        with without_remote_config():
            raise ValueError("boom")

    client.fetches.clear()
    RemoteDocuments(config=CONFIG).all()
    assert len(client.fetches) == 2


def test_a_reload_reads_each_document_once(client):
    """`reload_settings` built Settings twice, so this was two per data id."""

    client.fetches.clear()

    config_reload.reload_settings()

    assert client.fetches == ["querymind-base", "querymind-retrieval"]


def test_a_reload_installs_the_settings_it_validated(client):
    """The fetch count is a proxy; this is the property underneath it.

    Two constructions meant the object handed to `validate_security_settings` and
    the object the process then ran were different reads of the centre.
    """

    seen: list[Settings] = []
    import app.core.config as config_module

    original = config_module.validate_security_settings
    try:
        config_module.validate_security_settings = lambda settings: seen.append(settings)
        installed = config_reload.reload_settings()
    finally:
        config_module.validate_security_settings = original

    assert seen and seen[0] is installed


def test_one_save_reads_each_document_three_times(client):
    """Read to rewrite whole, re-read on reload, re-read to answer with the new state."""

    client.fetches.clear()

    admin_config.admin_save_config(admin_config.ConfigValues(values={"TOP_K": "9"}), _request(), ADMIN)

    assert client.fetches.count("querymind-base") == 3
    assert client.fetches.count("querymind-retrieval") == 3


def test_the_save_still_writes_what_it_was_asked_to(client):
    """A count that went to zero because the save stopped working is not an improvement."""

    body = admin_config.admin_save_config(admin_config.ConfigValues(values={"TOP_K": "9"}), _request(), ADMIN)

    assert body["ok"] is True
    assert "TOP_K=9" in client.documents["querymind-base"]
