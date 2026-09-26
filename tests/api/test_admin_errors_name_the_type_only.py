"""Admin endpoints report a failure's type; the details go to the server log (CodeQL #29, #31-#35).

The web-activity data manager and two health checks returned `str(e)` in their
JSON. They are admin-only, so this was never an anonymous disclosure, but an
exception message carries filesystem paths, hostnames and driver internals,
and the server log is where an operator reads those. The response now names
the exception's type, which is enough to know what kind of failure it was.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import pytest

SECRET = "/srv/querymind/private/backups is not writable by uid 1001"


def test_a_failed_backup_names_the_type_not_the_message(tmp_path, monkeypatch):
    import tarfile

    from app.services.web_activity.data_manager import WebActivityDataManager

    manager = WebActivityDataManager(
        log_dir=str(tmp_path / "logs"),
        backup_dir=str(tmp_path / "backups"),
        archive_dir=str(tmp_path / "archives"),
    )
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / f"web_activity_{datetime.now():%Y%m%d}.jsonl").write_text("{}\n", encoding="utf-8")

    def refuse(*_args, **_kwargs):
        raise OSError(SECRET)

    monkeypatch.setattr(tarfile, "open", refuse)

    result = manager.backup_logs(days=7)

    assert result["success"] is False
    assert "OSError" in result["message"]
    assert SECRET not in result["message"]


def test_the_web_activity_health_check_names_the_type_and_logs_the_rest(monkeypatch, caplog):
    from app.api.routes.admin import web_activity

    def broken():
        raise RuntimeError(SECRET)

    monkeypatch.setattr(web_activity, "get_activity_logger", broken)

    with caplog.at_level(logging.ERROR):
        health = asyncio.run(web_activity.health_check())

    assert health["components"]["logger"] == "error: RuntimeError"
    assert SECRET not in str(health)
    assert SECRET in caplog.text


@pytest.mark.parametrize("failing", ["neo4j", "cache"])
def test_the_graph_rag_health_check_names_the_type_and_logs_the_rest(failing, monkeypatch, caplog):
    from app.api.routes.admin import graph_rag
    from app.graph.knowledge import client

    def broken(*_args, **_kwargs):
        raise ConnectionError(SECRET)

    monkeypatch.setattr(graph_rag, "_require_permission", lambda *a, **k: None)
    if failing == "neo4j":
        monkeypatch.setattr(client, "Neo4jClient", broken)
    else:
        monkeypatch.setattr(graph_rag, "get_graph_rag_cache_stats_facade", broken)

    with caplog.at_level(logging.ERROR):
        health = asyncio.run(graph_rag.graph_rag_health_check(request=None, user={}))

    assert health["checks"][failing] == {"status": "error", "error": "ConnectionError"}
    assert SECRET not in str(health)
    assert SECRET in caplog.text
