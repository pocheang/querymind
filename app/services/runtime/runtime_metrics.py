from __future__ import annotations

import threading
import time
from typing import Any


class RuntimeMetrics:
    """
    Enhanced runtime metrics collector with label support.

    Supports Prometheus-style metrics with labels for better dimensionality.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Legacy flat metrics (backward compatible)
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._hist: dict[str, list[float]] = {}

        # New labeled metrics (metric_name -> {label_key: {label_value: value}})
        self._labeled_counters: dict[str, dict[str, dict[str, float]]] = {}
        self._labeled_gauges: dict[str, dict[str, dict[str, float]]] = {}
        self._labeled_hist: dict[str, dict[str, dict[str, list[float]]]] = {}

    def inc(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter, optionally with labels."""
        with self._lock:
            if labels:
                # Labeled counter
                if name not in self._labeled_counters:
                    self._labeled_counters[name] = {}

                for label_key, label_value in labels.items():
                    if label_key not in self._labeled_counters[name]:
                        self._labeled_counters[name][label_key] = {}

                    current = self._labeled_counters[name][label_key].get(label_value, 0.0)
                    self._labeled_counters[name][label_key][label_value] = float(current + value)
            else:
                # Legacy flat counter
                self._counters[name] = float(self._counters.get(name, 0.0) + value)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value, optionally with labels."""
        with self._lock:
            if labels:
                # Labeled gauge
                if name not in self._labeled_gauges:
                    self._labeled_gauges[name] = {}

                for label_key, label_value in labels.items():
                    if label_key not in self._labeled_gauges[name]:
                        self._labeled_gauges[name][label_key] = {}

                    self._labeled_gauges[name][label_key][label_value] = float(value)
            else:
                # Legacy flat gauge
                self._gauges[name] = float(value)

    @staticmethod
    def _append_bounded(arr: list[float], value: float, cap: int = 5000) -> None:
        arr.append(float(value))
        if len(arr) > cap:
            del arr[: len(arr) - cap]

    def _observe_labeled(self, name: str, value: float, labels: dict[str, str]) -> None:
        if name not in self._labeled_hist:
            self._labeled_hist[name] = {}
        for label_key, label_value in labels.items():
            if label_key not in self._labeled_hist[name]:
                self._labeled_hist[name][label_key] = {}
            arr = self._labeled_hist[name][label_key].setdefault(label_value, [])
            self._append_bounded(arr, value)

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation, optionally with labels."""
        with self._lock:
            if labels:
                self._observe_labeled(name, value, labels)
            else:
                arr = self._hist.setdefault(name, [])
                self._append_bounded(arr, value)

    def inc_agent_execution(self, agent_name: str, status: str, route: str | None = None) -> None:
        """Business metric: Increment agent execution counter."""
        labels = {"agent": agent_name, "status": status}
        if route:
            labels["route"] = route
        self.inc("agent_execution_total", 1.0, labels)

    def observe_retrieval_quality(self, score: float, strategy: str) -> None:
        """Business metric: Record retrieval quality score."""
        self.observe("retrieval_quality_score", score, {"strategy": strategy})

    def inc_llm_cost(self, cost_usd: float, provider: str, model: str) -> None:
        """Business metric: Track LLM API costs."""
        self.inc("llm_api_cost_usd_total", cost_usd, {"provider": provider, "model": model})

    def inc_cache_operations(self, operation: str, hit: bool, layer: str) -> None:
        """Business metric: Track cache hit/miss by layer."""
        labels = {"operation": operation, "result": "hit" if hit else "miss", "layer": layer}
        self.inc("cache_operations_total", 1.0, labels)

    def observe_session_duration(self, duration_seconds: float, user_type: str) -> None:
        """Business metric: Track user session duration."""
        self.observe("user_session_duration_seconds", duration_seconds, {"user_type": user_type})

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "hist": {k: list(v) for k, v in self._hist.items()},
                "labeled_counters": {
                    name: {label_key: dict(values) for label_key, values in labels.items()}
                    for name, labels in self._labeled_counters.items()
                },
                "labeled_gauges": {
                    name: {label_key: dict(values) for label_key, values in labels.items()}
                    for name, labels in self._labeled_gauges.items()
                },
                "labeled_hist": {
                    name: {
                        label_key: {label_value: list(arr) for label_value, arr in values.items()}
                        for label_key, values in labels.items()
                    }
                    for name, labels in self._labeled_hist.items()
                },
            }

    def render_prometheus(self) -> str:
        """The exposition format, six series kinds in a fixed order.

        Flat and labelled are the same series written two ways, so each pair
        shares a renderer and differs only in whether a label set is appended.
        """

        s = self.snapshot()
        lines: list[str] = []
        lines += _flat_series(s.get("counters"), "counter")
        lines += _labeled_series(s.get("labeled_counters"), "counter")
        lines += _flat_series(s.get("gauges"), "gauge")
        lines += _labeled_series(s.get("labeled_gauges"), "gauge")
        lines += _flat_histograms(s.get("hist"))
        lines += _labeled_histograms(s.get("labeled_hist"))
        lines.append(f"process_time_seconds {time.time():.6f}")
        return "\n".join(lines) + "\n"


def _metric_name(name: str) -> str:
    out = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(name))
    if not out:
        out = "metric"
    if out[0].isdigit():
        out = f"m_{out}"
    return out


_QUANTILES = (0.5, 0.9, 0.95, 0.99)


def _flat_series(values, kind: str) -> list[str]:
    """An unlabelled counter or gauge: a TYPE line and a value line each."""

    lines: list[str] = []
    for key, value in sorted((values or {}).items()):
        name = _metric_name(key)
        lines.append(f"# TYPE {name} {kind}")
        lines.append(f"{name} {float(value):.6f}")
    return lines


def _labeled_series(data, kind: str) -> list[str]:
    """The same series carrying one label pair; the TYPE line is written once."""

    lines: list[str] = []
    for metric_name, label_data in sorted((data or {}).items()):
        prom_name = _metric_name(metric_name)
        lines.append(f"# TYPE {prom_name} {kind}")
        for label_key, label_values in sorted(label_data.items()):
            for label_value, value in sorted(label_values.items()):
                lines.append(f'{prom_name}{{{label_key}="{label_value}"}} {float(value):.6f}')
    return lines


def _summary_body(name: str, values, label_str: str = "") -> list[str]:
    """Quantiles, sum and count for one histogram, labelled or not.

    The quantile index is a position in the sorted sample, not an interpolation
    -- which is what makes this a Prometheus *summary* rather than a histogram,
    and is preserved exactly.
    """

    arr = sorted(float(x) for x in values)
    count = len(arr)
    inner = f",{label_str}" if label_str else ""
    braces = f"{{{label_str}}}" if label_str else ""
    lines = [
        f'{name}_seconds{{quantile="{q}"{inner}}} {arr[min(count - 1, max(0, int(q * (count - 1))))]:.6f}'
        for q in _QUANTILES
    ]
    lines.append(f"{name}_seconds_sum{braces} {sum(arr):.6f}")
    lines.append(f"{name}_seconds_count{braces} {count}")
    return lines


def _flat_histograms(hist) -> list[str]:
    """An empty sample emits nothing at all, TYPE line included."""

    lines: list[str] = []
    for key, values in sorted((hist or {}).items()):
        if not values:
            continue
        name = _metric_name(key)
        lines.append(f"# TYPE {name}_seconds summary")
        lines += _summary_body(name, values)
    return lines


def _labeled_histograms(data) -> list[str]:
    """Here the TYPE line IS emitted even when every sample is empty.

    That asymmetry with `_flat_histograms` is the shipped behaviour and is kept
    deliberately; a metric declared with no series is valid exposition, and
    changing it would move bytes a scraper already parses.
    """

    lines: list[str] = []
    for metric_name, label_data in sorted((data or {}).items()):
        prom_name = _metric_name(metric_name)
        lines.append(f"# TYPE {prom_name}_seconds summary")
        for label_key, label_values in sorted(label_data.items()):
            for label_value, values in sorted(label_values.items()):
                if not values:
                    continue
                lines += _summary_body(prom_name, values, f'{label_key}="{label_value}"')
    return lines
