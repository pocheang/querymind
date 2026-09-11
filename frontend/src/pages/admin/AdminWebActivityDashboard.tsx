import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, authRequest } from "@/lib/api-client";
import { ExportButtons } from "@/utils/exportUtils";
import { WebActivityKpiCards } from "./components/WebActivityKpiCards";
import { WebActivityCharts } from "./components/WebActivityCharts";
import { WebActivityTables } from "./components/WebActivityTables";
import { Button } from "@/components/ui/button";
import { AdminSkeleton, RowActions, SectionHead, StatePanel } from "./components/AdminPrimitives";

interface WebActivityStats {
  summary: {
    total_searches: number;
    successful_searches: number;
    success_rate: number;
    sanitized_queries: number;
    unique_users: number;
    unique_websites: number;
    avg_query_length: number;
    avg_search_time: number;
  };
  top_websites: Array<{ domain: string; visit_count: number; avg_trust_score: number }>;
  top_users: Array<{ user_id: string; search_count: number }>;
  hourly_distribution: Record<string, number>;
}

interface Alert {
  timestamp: string;
  rule_name: string;
  level: string;
  message: string;
  metric_value: number;
  threshold: number;
}

interface AlertsResponse {
  alerts?: Alert[];
}

export function AdminWebActivityDashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<WebActivityStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [statsData, alertsData] = await Promise.all([
        authRequest<WebActivityStats>("/api/v1/admin/web-activity/stats"),
        authRequest<AlertsResponse>("/api/v1/admin/web-activity/alerts?hours=24"),
      ]);
      setStats(statsData);
      setAlerts(alertsData.alerts || []);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(t("admin.webActivity.authRequired", "Authentication required. Please sign in again."));
      } else {
        setError(t("admin.webActivity.loadingError", "Failed to fetch web activity data."));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
    if (!autoRefresh) return;
    const interval = window.setInterval(() => {
      void fetchData();
    }, 30000);
    return () => window.clearInterval(interval);
  }, [autoRefresh]);

  const hourlyData = stats
    ? Array.from({ length: 24 }, (_, i) => ({ hour: `${i}:00`, searches: stats.hourly_distribution[i] || 0 }))
    : [];

  const websitesData = stats?.top_websites.slice(0, 10) || [];
  const usersData = stats?.top_users.slice(0, 10) || [];

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    void fetchData();
  };

  if (loading) {
    return (
      <main className="space-y-6">
        <AdminSkeleton />
      </main>
    );
  }

  if (error) {
    return (
      <main className="space-y-6">
        <SectionHead title={t("admin.webActivity.title", "Web Search Activity")}></SectionHead>
        <StatePanel tone="error">
          <p>{error}</p>
          <Button variant="secondary" size="xs" onClick={handleRetry}>{t("admin.webActivity.retry", "Retry")}</Button>
        </StatePanel>
      </main>
    );
  }

  return (
    <main className="space-y-6">
      <SectionHead title={t("admin.webActivity.title", "Web Search Activity")}>
<RowActions>
          <ExportButtons
            data={stats ? [{ ...stats.summary, top_users: usersData, top_websites: websitesData }] : []}
            filename={`web-activity-${new Date().toISOString().split("T")[0]}`}
          />
          <Button variant="secondary" size="xs" onClick={() => void fetchData()}>{t("admin.webActivity.refresh", "Refresh")}</Button>
        </RowActions></SectionHead>

      <label className="flex shrink-0 cursor-pointer select-none items-center gap-2 whitespace-nowrap rounded-control border border-transparent px-3 py-2 text-xs font-bold uppercase tracking-wider text-ink/80 transition-colors hover:border-brand-border hover:bg-brand-surface">
        <input className="size-3.5 shrink-0 accent-[var(--brand)]" type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
        <span>{t("admin.ui.autoRefresh30")}</span>
      </label>

      {stats && (
        <>
          <WebActivityKpiCards stats={stats.summary} />
          <WebActivityCharts data={{ hourlyData, websitesData }} />
          <WebActivityTables usersData={usersData} websitesData={websitesData} alerts={alerts} />
        </>
      )}
    </main>
  );
}
