import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
  Area,
  AreaChart,
} from "recharts";
import type { AdminRuntimeSnapshot } from "@/types/api";
import { adminOpsApi } from "@/lib/admin-ops-api";
import { Button } from "@/components/ui/button";
import {
  AdminPanel,
  KpiCard,
  KpiGrid,
  OpsGrid,
  RowActions,
  StatePanel,
  SubTitle,
} from "./components/AdminPrimitives";
import { CHART_AXIS, CHART_GRID, CHART_TOOLTIP } from "./components/adminClasses";

export function AdminSystemMonitor() {
  const { t } = useTranslation();
  const [snapshot, setSnapshot] = useState<AdminRuntimeSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadSnapshot = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await adminOpsApi.adminRuntimeSnapshot();
      setSnapshot(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSnapshot();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(() => void loadSnapshot(), 3000);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  if (loading && !snapshot) {
    return (
      <main className="space-y-6">
        <StatePanel>{t("common.loading", "Loading...")}</StatePanel>
      </main>
    );
  }

  if (error && !snapshot) {
    return (
      <main className="space-y-6">
        <StatePanel tone="error">{error}</StatePanel>
        <Button size="sm" onClick={() => void loadSnapshot()}>
          {t("common.retry", "Retry")}
        </Button>
      </main>
    );
  }

  if (!snapshot) {
    return (
      <main className="space-y-6">
        <StatePanel>{t("common.noData", "No data available")}</StatePanel>
      </main>
    );
  }

  const healthy = snapshot.status === "healthy";

  // Prepare chart data
  const resourceData = [
    { name: "CPU", value: snapshot.resources.cpu_percent, fill: "#3b82f6" },
    { name: "Memory", value: snapshot.resources.memory_percent, fill: "#8b5cf6" },
    { name: "Disk", value: snapshot.resources.disk_percent, fill: "#06b6d4" },
  ];

  const servicesData = Object.entries(snapshot.services).map(([name, health]) => ({
    name,
    status: health.ok ? 1 : 0,
    latency: health.latency_ms || 0,
  }));

  return (
    <main className="space-y-6">
      <AdminPanel>
        <RowActions className="mb-4 justify-between">
          <SubTitle>{t("admin.systemMonitor.title", "Runtime Monitor")}</SubTitle>
          <RowActions>
            <label className="flex cursor-pointer select-none items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
              <input
                className="size-4 shrink-0 accent-[var(--brand)]"
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              {t("admin.systemMonitor.autoRefresh", "Auto-refresh (3s)")}
            </label>
            <Button variant="secondary" size="sm" onClick={() => void loadSnapshot()} disabled={loading}>
              {loading ? t("common.loading", "Loading...") : t("common.refresh", "Refresh")}
            </Button>
          </RowActions>
        </RowActions>

        {error && <StatePanel tone="error">{error}</StatePanel>}

        <KpiGrid cols={6} className="mb-0">
          <KpiCard
            label={t("admin.systemMonitor.systemStatus", "System Status")}
            value={
              <>
                {snapshot.status.toUpperCase()}
                <span className="mt-1 block text-[11px] font-normal text-ink-muted">
                  {new Date(snapshot.generated_at).toLocaleTimeString()}
                </span>
              </>
            }
            tone={healthy ? "success" : "danger"}
          />
          <KpiCard
            label={t("admin.systemMonitor.cpu", "CPU")}
            value={`${snapshot.resources.cpu_percent.toFixed(1)}%`}
          />
          <KpiCard
            label={t("admin.systemMonitor.memory", "Memory")}
            value={`${snapshot.resources.memory_percent.toFixed(1)}%`}
          />
          <KpiCard
            label={t("admin.systemMonitor.disk", "Disk")}
            value={`${snapshot.resources.disk_percent.toFixed(1)}%`}
          />
          <KpiCard
            label={t("admin.systemMonitor.totalRequests", "Total Requests")}
            value={
              <>
                {snapshot.traffic.requests_total}
                <span className="mt-1 block text-[11px] font-normal text-ink-muted">
                  {t("admin.systemMonitor.last", "Last")} {snapshot.traffic.window_seconds}s
                </span>
              </>
            }
          />
          <KpiCard
            label={t("admin.systemMonitor.avgResponse", "Avg Response")}
            value={`${snapshot.traffic.avg_response_ms.toFixed(1)} ms`}
          />
          <KpiCard
            label={t("admin.systemMonitor.errorRate", "Error Rate")}
            value={`${snapshot.traffic.error_rate_percent.toFixed(2)}%`}
          />
          <KpiCard
            label={t("admin.systemMonitor.activeRequests", "Active Requests")}
            value={snapshot.traffic.active_requests}
          />
        </KpiGrid>
      </AdminPanel>

      <OpsGrid>
        <AdminPanel>
          <SubTitle>{t("admin.systemMonitor.resources", "System Resources")}</SubTitle>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={resourceData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="name" stroke={CHART_AXIS} fontSize={14} />
              <YAxis stroke={CHART_AXIS} domain={[0, 100]} fontSize={14} />
              <Tooltip
                contentStyle={CHART_TOOLTIP}
                formatter={(value: unknown) => [`${Number(value).toFixed(1)}%`, 'Usage']}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {resourceData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </AdminPanel>

        <AdminPanel>
          <SubTitle>{t("admin.systemMonitor.trafficMetrics", "Traffic Metrics")}</SubTitle>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart
              data={[
                {
                  name: 'Current',
                  requests: snapshot.traffic.requests_total,
                  errors: Math.round((snapshot.traffic.requests_total * snapshot.traffic.error_rate_percent) / 100),
                }
              ]}
              margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
            >
              <defs>
                <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="colorErrors" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="name" stroke={CHART_AXIS} fontSize={14} />
              <YAxis stroke={CHART_AXIS} fontSize={14} />
              <Tooltip
                contentStyle={CHART_TOOLTIP}
              />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              <Area
                type="monotone"
                dataKey="requests"
                stroke="#3b82f6"
                fillOpacity={1}
                fill="url(#colorRequests)"
                name="Total Requests"
              />
              <Area
                type="monotone"
                dataKey="errors"
                stroke="#ef4444"
                fillOpacity={1}
                fill="url(#colorErrors)"
                name="Errors"
              />
            </AreaChart>
          </ResponsiveContainer>
        </AdminPanel>
      </OpsGrid>

      <OpsGrid>
        <AdminPanel>
          <SubTitle>{t("admin.systemMonitor.serviceLatency", "Service Latency")}</SubTitle>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={servicesData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="name" stroke={CHART_AXIS} fontSize={14} />
              <YAxis stroke={CHART_AXIS} fontSize={14} />
              <Tooltip
                contentStyle={CHART_TOOLTIP}
                formatter={(value: unknown) => [`${Number(value)} ms`, 'Latency']}
              />
              <Bar dataKey="latency" fill="#10b981" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </AdminPanel>

        <AdminPanel>
          <SubTitle>{t("admin.systemMonitor.responseTime", "Response Time")}</SubTitle>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart
              data={[
                { name: 'Avg', value: snapshot.traffic.avg_response_ms },
                { name: 'P95', value: snapshot.traffic.p95_response_ms },
              ]}
              margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
              <XAxis dataKey="name" stroke={CHART_AXIS} fontSize={14} />
              <YAxis stroke={CHART_AXIS} fontSize={14} />
              <Tooltip
                contentStyle={CHART_TOOLTIP}
                formatter={(value: unknown) => [`${Number(value).toFixed(1)} ms`, 'Response Time']}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#f59e0b"
                strokeWidth={3}
                dot={{ fill: '#f59e0b', r: 6 }}
                activeDot={{ r: 8 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </AdminPanel>
      </OpsGrid>

      <AdminPanel>
        <SubTitle>{t("admin.systemMonitor.serviceStatus", "Service Health")}</SubTitle>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Object.entries(snapshot.services).map(([name, health]) => (
            <div
              key={name}
              className="grid min-w-0 grid-cols-[auto_1fr_auto] items-center gap-3 rounded-card border border-line bg-surface p-4"
            >
              <span
                className={
                  "size-2.5 shrink-0 rounded-pill " +
                  (health.ok
                    ? "bg-success shadow-[0_0_12px_color-mix(in_srgb,var(--success)_65%,transparent)]"
                    : "bg-danger shadow-[0_0_12px_color-mix(in_srgb,var(--danger)_55%,transparent)]")
                }
                aria-hidden="true"
              />
              <div className="min-w-0">
                <strong className="block truncate text-xs capitalize text-ink">{name}</strong>
                <p className="mt-1 truncate text-[11px] text-ink-muted">
                  {health.required ? t("common.required", "Required") : t("common.optional", "Optional")}
                  {health.latency_ms !== undefined && ` • ${health.latency_ms}ms`}
                </p>
              </div>
              <code className="font-mono text-[11px] text-ink-muted">{health.ok ? "OK" : "FAILED"}</code>
            </div>
          ))}
        </div>
      </AdminPanel>

      <AdminPanel>
        <SubTitle>{t("admin.systemMonitor.model", "Model Configuration")}</SubTitle>
        <KpiGrid cols={5} className="mb-0">
          <KpiCard
            label={t("admin.systemMonitor.enabled", "Enabled")}
            value={snapshot.model.enabled ? t("common.yes", "是") : t("common.no", "否")}
          />
          <KpiCard label={t("admin.systemMonitor.provider", "Provider")} value={snapshot.model.provider} />
          <KpiCard
            label={t("admin.systemMonitor.chatModel", "Chat Model")}
            value={<span className="text-sm">{snapshot.model.chat_model}</span>}
          />
          <KpiCard
            label={t("admin.systemMonitor.reasoningModel", "Reasoning Model")}
            value={<span className="text-sm">{snapshot.model.reasoning_model}</span>}
          />
          <KpiCard
            label={t("admin.systemMonitor.embeddingModel", "Embedding Model")}
            value={<span className="text-sm">{snapshot.model.embedding_model || "-"}</span>}
          />
          <KpiCard
            label={t("admin.systemMonitor.baseUrl", "Base URL")}
            value={<span className="text-xs [overflow-wrap:anywhere]">{snapshot.model.base_url}</span>}
          />
        </KpiGrid>
      </AdminPanel>
    </main>
  );
}
