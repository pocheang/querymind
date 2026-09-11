import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { analyticsApi, type AnalyticsOverview } from "@/services/api/app";

/**
 * The top bar's live readout, from the design prototype.
 *
 * Two things about it are deliberate and worth knowing before changing it.
 *
 * **The numbers are real and labelled as what they are.** The prototype shows
 * `Latency: 184ms` and `Cache Hit: 89.4%` as hardcoded demo text. There is no
 * cache-hit metric in this system, and the only figure available is the
 * corpus-wide average from `/api/analytics/overview` -- not "your last request",
 * which is what a bare "Latency" in a top bar reads as. So the labels say
 * *average*, and the second slot carries success rate, which this system does
 * measure, rather than a cache-hit number invented to fill the shape.
 *
 * **It renders for admins only, because that is who can read it.**
 * `/api/analytics/overview` is gated on `ADMIN_OPS_MANAGE`; showing the strip
 * to anyone else would be a control that is permanently empty, which reads as
 * broken rather than as absent.
 *
 * A decorative readout must never be able to break the bar it sits in: a failed
 * fetch renders nothing and is not retried on a tighter loop, and polling stops
 * while the tab is hidden so a backgrounded dashboard is not a standing request
 * every minute.
 */
const POLL_MS = 60_000;

export function TopNavMetrics() {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);

  useEffect(() => {
    let cancelled = false;

    const read = async () => {
      if (document.hidden) return;
      try {
        const data = await analyticsApi.overview();
        if (!cancelled) setOverview(data);
      } catch {
        // Nothing: the bar keeps its last good numbers, or stays empty. An
        // error banner here would put a monitoring failure in front of every
        // page in the app.
      }
    };

    void read();
    const timer = window.setInterval(() => void read(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  // No samples is not zero performance. `RetrievalLogger` returns
  // `avg_total_time_ms: 0, success_rate: 0` for an empty log, which renders as
  // "Success: 0.0%" in warning amber -- a bar that says the system is failing
  // when what it means is that nobody has asked it anything yet. An absent
  // readout is the honest answer, and it is why this checks the SAMPLE COUNT
  // rather than the values.
  if (!overview || overview.total_queries <= 0) return null;

  const latency = overview.avg_total_time_ms;
  const success = overview.success_rate;

  return (
    <div className="ml-2 hidden items-center gap-3 text-xs font-medium text-ink/80 xl:flex">
      <Metric
        label={t("components.topNav.avgLatency", "Avg latency")}
        value={`${Math.round(latency)}ms`}
        tone={latency <= 2000 ? "good" : "warn"}
      />
      <span className="text-line-strong" aria-hidden="true">
        |
      </span>
      <Metric
        label={t("components.topNav.successRate", "Success")}
        value={`${(success * 100).toFixed(1)}%`}
        tone={success >= 0.95 ? "good" : "warn"}
      />
    </div>
  );
}

function Metric({ label, value, tone }: Readonly<{ label: string; value: string; tone: "good" | "warn" }>) {
  return (
    <span className="whitespace-nowrap">
      {label}:{" "}
      <b className={`font-mono font-semibold ${tone === "good" ? "text-success" : "text-warning"}`}>{value}</b>
    </span>
  );
}
