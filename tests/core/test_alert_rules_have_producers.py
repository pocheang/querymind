"""Every alert rule watches a series something produces (ARC-01 phase 8).

Until 2026-09-25, 19 of the 21 rules in alert_rules.yml named metrics nothing in
app/ emitted -- agent_execution_total, query_duration_seconds, circuit_breaker_state,
*_health, llm_api_cost_usd_total -- and so could never fire; only the two on `up`
could. An alert that cannot fire looks exactly like a system with nothing wrong.

The produced set is taken from what `render()` actually emits after one of each
metric has been recorded, not from a list written here, so a renamed metric
fails this test instead of agreeing with it.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from prometheus_client.parser import text_string_to_metric_families

from app.api.routes.operations.metrics_collectors import DeploymentStateCollector
from app.services.runtime import runtime_metrics

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "observability" / "prometheus" / "alert_rules.yml"

# Series Prometheus itself produces for every scrape target.
FROM_PROMETHEUS = {"up"}

_PROMQL_WORDS = {
    "sum", "max", "min", "avg", "count", "rate", "increase", "irate", "by", "without", "on", "ignoring",
    "and", "or", "unless", "histogram_quantile", "avg_over_time", "max_over_time", "min_over_time",
    "time", "changes", "delta", "abs", "bool", "offset", "group_left", "group_right", "le",
}  # fmt: skip


def metric_names(expr: str) -> set[str]:
    """Series names in a PromQL expression: identifiers that are not functions, keywords or labels."""

    without_matchers = re.sub(r"\{[^}]*\}", " ", expr)
    without_ranges = re.sub(r"\[[^\]]*\]", " ", without_matchers)
    without_groupings = re.sub(r"\b(by|without|on|ignoring)\s*\([^)]*\)", " ", without_ranges)
    names = set()
    for match in re.finditer(r"[a-zA-Z_:][a-zA-Z0-9_:]*", without_groupings):
        word = match.group(0)
        followed_by_call = without_groupings[match.end() :].lstrip().startswith("(")
        if word in _PROMQL_WORDS or followed_by_call:
            continue
        names.add(word)
    return names


def _rules() -> list[dict]:
    data = yaml.safe_load(RULES.read_text(encoding="utf-8-sig"))
    return [rule for group in data["groups"] for rule in group["rules"]]


def _produced() -> set[str]:
    runtime_metrics.record_request(200, 0.1, "query")
    runtime_metrics.record_embedding_reindex("failed")
    runtime_metrics.record_circuit_breaker("probe", 0.0)
    collector = DeploymentStateCollector({"inflight": 0, "waiting": 0}, {"redis": {"ok": True, "required": True}})
    text = runtime_metrics.render([collector])[0].decode()
    return {sample.name for family in text_string_to_metric_families(text) for sample in family.samples}


def test_every_rule_names_only_produced_series():
    produced = _produced() | FROM_PROMETHEUS
    missing = {
        rule["alert"]: sorted(metric_names(rule["expr"]) - produced)
        for rule in _rules()
        if metric_names(rule["expr"]) - produced
    }

    assert missing == {}


def test_every_rule_names_at_least_one_series():
    """A rule the extractor reads as naming nothing would pass the test above vacuously."""

    assert all(metric_names(rule["expr"]) for rule in _rules())


def test_the_extractor_finds_a_series_nothing_produces():
    expr = 'sum(rate(agent_execution_total{status="failed"}[5m])) by (agent) / sum(rate(up[5m]))'

    assert metric_names(expr) == {"agent_execution_total", "up"}


def test_the_rules_file_still_has_rules():
    assert len(_rules()) >= 8
