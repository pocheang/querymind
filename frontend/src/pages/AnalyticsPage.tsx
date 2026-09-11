import { useCallback, useEffect, useState } from "react";
import { Download, RefreshCw } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { AppShell, PageHeader } from "@/components/layout/AppShell";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AuthUser } from "@/types/api";
import { analyticsApi, type AgentStats, type AnalyticsOverview, type DocumentStats } from "@/services/api/app";

type Props = {
  user: AuthUser | null;
  onLogout: () => Promise<void>;
};

/* Categorical series colours, read off the amber theme rather than the
   Recharts defaults so a chart sits in the same palette as the page around
   it. Each is a token this app already ships and has already measured. */
const COLORS = ["var(--brand)", "var(--info)", "var(--warning)", "var(--success)"];
const SERIES = { primary: "var(--brand)", secondary: "var(--info)", tertiary: "var(--warning)" };

/* Recharts renders its chrome as inline SVG/DOM, so its styling has to be
   passed as props rather than reached with a class. */
const TOOLTIP_STYLE = {
  background: "var(--surface)",
  border: "1px solid var(--brand-border)",
  borderRadius: "var(--shape-control)",
  fontSize: "12px",
  color: "var(--text-main)",
} as const;
const AXIS_TICK = { fill: "var(--text-muted)", fontSize: 11 } as const;
const LEGEND_STYLE = { fontSize: "12px" } as const;

export function AnalyticsPage({ user, onLogout }: Readonly<Props>) {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [agents, setAgents] = useState<AgentStats[]>([]);
  const [documents, setDocuments] = useState<DocumentStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const [overviewData, agentsData, docsData] = await Promise.all([
        analyticsApi.overview(),
        analyticsApi.agents(),
        analyticsApi.documents(10),
      ]);

      setOverview(overviewData);
      setAgents(agentsData);
      setDocuments(docsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("pages.analytics.loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void fetchData();
    const interval = window.setInterval(() => void fetchData(), 10000);
    return () => window.clearInterval(interval);
  }, [fetchData]);

  const handleExport = (format: "json" | "csv") => {
    window.open(analyticsApi.exportUrl(format), "_blank", "noopener,noreferrer");
  };

  if (loading && !overview) {
    return (
      <AppShell user={user} onLogout={onLogout} scroll>
        <div className="flex flex-1 items-center justify-center">
          <p className="text-xs text-ink-muted">{t("pages.analytics.loading")}</p>
        </div>
      </AppShell>
    );
  }

  const agentDistributionData = overview?.agent_distribution
    ? Object.entries(overview.agent_distribution).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const agentPerformanceData = agents.map((agent) => ({
    name: agent.agent_class,
    queries: agent.query_count,
    success_rate: agent.success_rate,
    avg_time: agent.avg_retrieval_time_ms,
  }));

  const documentHeatmapData = documents.map((doc) => ({
    name: doc.source.length > 30 ? `${doc.source.substring(0, 27)}...` : doc.source,
    retrievals: doc.retrieval_count,
    avg_score: doc.avg_score,
  }));

  return (
    <AppShell user={user} onLogout={onLogout} scroll>
      <PageHeader
        title={t("pages.analytics.dashboard")}
        description={t("pages.analytics.subtitle")}
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => void fetchData()}>
              <RefreshCw className={cn("size-3.5", loading && "animate-spin")} aria-hidden="true" />
              {loading ? t("pages.analytics.refreshing") : t("common.refresh")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleExport("json")}>
              <Download className="size-3.5" aria-hidden="true" />
              {t("pages.analytics.exportJson")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => handleExport("csv")}>
              <Download className="size-3.5" aria-hidden="true" />
              {t("pages.analytics.exportCsv")}
            </Button>
          </>
        }
      />

      <div className="mx-auto w-full max-w-6xl space-y-5 p-4 sm:p-6">
        {error && (
          <p
            className="rounded-control border border-danger-border bg-danger-surface px-3 py-2 text-xs sm:text-sm font-medium text-danger"
            role="alert"
          >
            {error}
          </p>
        )}

        {/* KPI tiles: the design's fixed three-line rhythm -- uppercase micro
            label, big mono number, optional note. */}
        <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
          {[
            { label: t("pages.analytics.totalQueries"), value: overview?.total_queries ?? 0 },
            {
              label: t("pages.analytics.successRate"),
              value: overview?.success_rate ? `${overview.success_rate.toFixed(1)}%` : "0%",
            },
            {
              label: t("pages.analytics.avgResponseTime"),
              value: overview?.avg_total_time_ms ? `${overview.avg_total_time_ms.toFixed(0)}ms` : "0ms",
              note: overview?.avg_retrieval_time_ms
                ? t("pages.analytics.avgResponseNote", { retrieval: overview.avg_retrieval_time_ms.toFixed(0) })
                : undefined,
            },
            {
              label: t("pages.analytics.avgRetrievedDocs"),
              value: overview?.avg_retrieved_count ? overview.avg_retrieved_count.toFixed(1) : "0",
            },
          ].map(({ label, value, note }) => (
            <Card key={label} className="p-4 sm:p-5">
              <p className="text-xs font-bold uppercase tracking-wider text-ink/80">{label}</p>
              <p className="mt-1.5 font-mono text-2xl sm:text-3xl font-bold text-brand-text-strong">{value}</p>
              {note && <p className="mt-1 text-xs text-ink-muted leading-relaxed">{note}</p>}
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card className="p-5">
            <h2 className="mb-3 text-sm sm:text-base font-bold text-ink">{t("pages.analytics.agentDistribution")}</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={agentDistributionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  dataKey="value"
                >
                  {agentDistributionData.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 text-sm sm:text-base font-bold text-ink">{t("pages.analytics.agentPerformance")}</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={agentPerformanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-neutral)" />
                <XAxis dataKey="name" tick={AXIS_TICK} />
                <YAxis tick={AXIS_TICK} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={LEGEND_STYLE} />
                <Bar dataKey="queries" fill={SERIES.primary} name={t("pages.analytics.queryCount")} />
                <Bar dataKey="success_rate" fill={SERIES.secondary} name={t("pages.analytics.successRatePercent")} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        <Card className="p-5">
          <h2 className="mb-3 text-sm sm:text-base font-bold text-ink">{t("pages.analytics.topDocuments")}</h2>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={documentHeatmapData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-neutral)" />
              <XAxis type="number" tick={AXIS_TICK} />
              <YAxis dataKey="name" type="category" width={200} tick={AXIS_TICK} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={LEGEND_STYLE} />
              <Bar dataKey="retrievals" fill={SERIES.primary} name={t("pages.analytics.retrievals")} />
              <Bar dataKey="avg_score" fill={SERIES.tertiary} name={t("pages.analytics.avgScore")} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </AppShell>
  );
}
