"""`scripts/eval_specialist_routing.py` exits the way a person reading it would expect.

The retrieval script once exited 1 on the state its own suite asserted was
correct, which teaches people to ignore it. This one exits 0 on the recorded
state, 1 on any drift in either direction, and 2 -- without routing anything --
when asked to measure the model router with no real model to measure.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.evaluation import specialist_routing

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "eval_specialist_routing.py"


def _load():
    spec = importlib.util.spec_from_file_location("eval_specialist_routing", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_recorded_state_exits_zero(capsys):
    assert _load().main([]) == 0
    assert "class accuracy" in capsys.readouterr().out


def test_a_new_miss_exits_one(monkeypatch, capsys):
    missing_one = dict(specialist_routing.KNOWN_MISROUTES)
    missing_one.pop("sec-10")
    monkeypatch.setattr(specialist_routing, "KNOWN_MISROUTES", missing_one)

    assert _load().main([]) == 1
    assert "NEW" in capsys.readouterr().out


def test_a_miss_that_now_routes_right_exits_one(monkeypatch, capsys):
    stale = {**specialist_routing.KNOWN_MISROUTES, "gen-01": (("general", "compare_entities"), "stale")}
    monkeypatch.setattr(specialist_routing, "KNOWN_MISROUTES", stale)

    assert _load().main([]) == 1
    assert "FIXED gen-01" in capsys.readouterr().out


def test_the_model_router_is_not_measured_without_a_model(monkeypatch, capsys):
    script = _load()
    monkeypatch.setattr(script, "_chat_model_refusal", lambda: "chat model is degraded (local)")
    routed: list[str] = []
    monkeypatch.setattr(script, "_llm_route", lambda question: routed.append(question) or ("general", "x"))

    assert script.main(["--llm"]) == script.REFUSED
    assert routed == []
    assert "refused" in capsys.readouterr().err


@pytest.mark.parametrize("flag", [[], ["--llm"]])
def test_it_takes_no_path_argument(flag):
    """No --queries: a path from the command line would need the S8707 containment rule."""

    with pytest.raises(SystemExit):
        _load().main([*flag, "--queries", "x.json"])
