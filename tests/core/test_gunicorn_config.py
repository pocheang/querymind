"""The backend image runs gunicorn with the settings the rest of the system assumes (ARC-01 phase 9).

`deploy/gunicorn.conf.py` is a plain module gunicorn executes, so it is loaded
here the same way, with `runpy`. `app/gunicorn_worker.py` is **not** imported:
it subclasses `uvicorn_worker.UvicornWorker`, which needs `fcntl`, and this
suite runs on Windows too. Its one decision is checked by reading it.
"""

from __future__ import annotations

import ast
import json
import re
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "deploy" / "gunicorn.conf.py"
WORKER = ROOT / "app" / "gunicorn_worker.py"


def _conf(monkeypatch: pytest.MonkeyPatch, **environment: str | None) -> dict:
    for key in ("APP_WORKERS", "GUNICORN_TIMEOUT_SECONDS", "PROMETHEUS_MULTIPROC_DIR"):
        monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    return runpy.run_path(str(CONF))


@pytest.mark.parametrize(("declared", "started"), [(None, 1), ("", 1), ("0", 1), ("1", 1), ("2", 2), ("4", 4)])
def test_the_worker_count_is_the_one_settings_validates(monkeypatch, declared, started):
    """`validate_worker_topology` reads APP_WORKERS; gunicorn must start exactly that many."""

    assert _conf(monkeypatch, APP_WORKERS=declared)["workers"] == started


def test_a_wedged_worker_is_replaced_after_the_timeout(monkeypatch):
    assert _conf(monkeypatch)["timeout"] == 60
    assert _conf(monkeypatch, GUNICORN_TIMEOUT_SECONDS="90")["timeout"] == 90


def test_it_serves_where_the_healthchecks_and_nginx_look(monkeypatch):
    conf = _conf(monkeypatch)
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert conf["bind"] == "0.0.0.0:8000"
    assert "EXPOSE 8000" in dockerfile
    assert "http://backend:8000" in (ROOT / "nginx.conf").read_text(encoding="utf-8")


def test_the_image_starts_gunicorn_with_this_file():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    command = re.search(r"^CMD (\[.*\])$", dockerfile, re.MULTILINE)

    assert command, "the Dockerfile has no exec-form CMD"
    assert json.loads(command.group(1)) == ["gunicorn", "-c", "deploy/gunicorn.conf.py", "app.api.main:app"]


@pytest.mark.parametrize("package", ["gunicorn", "uvicorn-worker"])
def test_the_runtime_image_installs_it(package: str):
    """The image installs requirements/runtime.txt, a different export from the one tests run against."""

    runtime = (ROOT / "requirements" / "runtime.txt").read_text(encoding="utf-8")

    assert re.search(rf"^{re.escape(package)}==", runtime, re.MULTILINE)


def test_the_worker_class_is_ours(monkeypatch):
    module, _, name = _conf(monkeypatch)["worker_class"].rpartition(".")

    assert ROOT.joinpath(*module.split(".")).with_suffix(".py") == WORKER
    classes = {
        node.name: node for node in ast.parse(WORKER.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef)
    }
    assert name in classes
    assert [ast.unparse(base) for base in classes[name].bases] == ["UvicornWorker"]


def test_the_worker_honours_proxy_headers_only_from_trusted_proxies():
    """gunicorn's own `forwarded_allow_ips` refuses a network, so the worker replaces it after that check."""

    tree = ast.parse(WORKER.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CONFIG_KWARGS" for t in node.targets)
    )
    assert isinstance(assignment.value, ast.Dict)
    entries = {
        (ast.unparse(key) if key is not None else "**"): ast.unparse(value)
        for key, value in zip(assignment.value.keys, assignment.value.values, strict=True)
    }

    assert entries["**"] == "UvicornWorker.CONFIG_KWARGS", "the base worker's settings must be kept"
    assert entries["'forwarded_allow_ips'"] == "trusted_proxies()"
    assert entries["'proxy_headers'"] == "True"


def test_the_metrics_directory_starts_empty(monkeypatch, tmp_path):
    """Files a previous run's workers left are not this run's workers."""

    directory = tmp_path / "metrics"
    directory.mkdir()
    (directory / "counter_1234.db").write_bytes(b"stale")
    conf = _conf(monkeypatch, PROMETHEUS_MULTIPROC_DIR=str(directory))

    conf["on_starting"](SimpleNamespace())

    assert directory.is_dir()
    assert list(directory.iterdir()) == []


def test_the_metrics_directory_is_created_when_missing(monkeypatch, tmp_path):
    directory = tmp_path / "not-yet"
    conf = _conf(monkeypatch, PROMETHEUS_MULTIPROC_DIR=str(directory))

    conf["on_starting"](SimpleNamespace())

    assert directory.is_dir()


def test_a_finished_worker_stops_reporting_its_live_gauges(monkeypatch, tmp_path):
    from prometheus_client import multiprocess

    dead: list[int] = []
    monkeypatch.setattr(multiprocess, "mark_process_dead", dead.append)
    conf = _conf(monkeypatch, PROMETHEUS_MULTIPROC_DIR=str(tmp_path))

    conf["child_exit"](SimpleNamespace(), SimpleNamespace(pid=4242))

    assert dead == [4242]


def test_without_multiprocess_metrics_the_hooks_touch_nothing(monkeypatch):
    from prometheus_client import multiprocess

    monkeypatch.setattr(multiprocess, "mark_process_dead", lambda pid: pytest.fail("called without a directory"))
    conf = _conf(monkeypatch)

    conf["on_starting"](SimpleNamespace())
    conf["child_exit"](SimpleNamespace(), SimpleNamespace(pid=4242))


def _environment_names_read_by(source: str) -> set[str]:
    reads = re.findall(r"""os\.environ(?:\.get\(|\[|\.setdefault\()\s*["']([A-Z_][A-Z0-9_]*)""", source)
    membership = re.findall(r"""["']([A-Z_][A-Z0-9_]*)["']\s+in\s+os\.environ""", source)
    return set(reads) | set(membership)


def _gunicorn_environment_names() -> set[str]:
    """What gunicorn's own settings read from the environment -- from its source, since it needs `grp`."""

    import importlib.util

    spec = importlib.util.find_spec("gunicorn")
    assert spec and spec.submodule_search_locations, "gunicorn is not installed"
    return _environment_names_read_by((Path(spec.submodule_search_locations[0]) / "config.py").read_text("utf-8"))


def test_the_trust_variable_is_not_one_gunicorn_claims():
    """gunicorn reads FORWARDED_ALLOW_IPS at import and refuses a network there.

    The trust list used to live under that name, and the subnet stopped every
    worker from booting -- found only by running the image. Any variable
    gunicorn reads would do the same, so the check is against all of them.
    """

    source = (ROOT / "app" / "api" / "transport" / "client_address.py").read_text(encoding="utf-8")
    ours = _environment_names_read_by(source)
    claimed = _gunicorn_environment_names()

    assert ours == {"QUERYMIND_TRUSTED_PROXIES"}
    assert "FORWARDED_ALLOW_IPS" in claimed, "the scan no longer finds what it exists to find"
    assert not ours & claimed
