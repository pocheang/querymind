import types

import httpx

import app.services.alerting as alerting


def test_emit_alert_webhook_failure_does_not_raise(monkeypatch):
    """Webhook errors should be swallowed so alerting never cascades failures."""

    settings = types.SimpleNamespace(
        alerting_enabled=True,
        alert_webhook_url="https://alerts.example.test/hook",
        alert_webhook_allowlist="example.test",
        alert_min_interval_seconds=1,
    )
    monkeypatch.setattr(alerting, "get_settings", lambda: settings)
    alerting._LAST_SENT.clear()

    class BrokenClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, _url, json):
            raise httpx.RequestError("webhook down")

    monkeypatch.setattr(alerting.httpx, "Client", BrokenClient)

    assert alerting.emit_alert("query_failed", {"trace_id": "trace-1"}) is False
