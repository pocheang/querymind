import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ApiError, authRequest } from "@/lib/api-client";
import { ExportButtons } from "@/utils/exportUtils";
import { Button } from "@/components/ui/button";
import {
  AdminBlock,
  AdminSkeleton,
  ControlsRow,
  KpiCard,
  KpiGrid,
  RowActions,
  SectionBlock,
  SectionHead,
  StatePanel,
  SubTitle,
  TwoCol,
} from "./components/AdminPrimitives";
import {
  ADMIN_FIELD,
  ADMIN_TABLE,
  ADMIN_TABLE_WRAP,
  CHART_AXIS,
  CHART_GRID,
  CHART_TOOLTIP,
} from "./components/adminClasses";

interface AgentMetrics {
  agent_name: string;
  total_executions: number;
  success_count: number;
  failure_count: number;
  success_rate: number;
  avg_execution_time: number;
  avg_token_usage: number;
  last_execution: string;
  error_types: Record<string, number>;
}

interface AgentQualityStats {
  summary: {
    total_agents: number;
    total_executions: number;
    overall_success_rate: number;
    avg_response_time: number;
    active_agents: number;
  };
  agents: AgentMetrics[];
  timeline: Array<{
    timestamp: string;
    success: number;
    failure: number;
  }>;
  error_distribution: Record<string, number>;
}

const COLORS = ["#5b8cff", "#4fc3f7", "#8b7aff", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"];

function getStatusTone(successRate: number) {
  if (successRate >= 0.9) return "success";
  if (successRate >= 0.7) return "warning";
  return "danger";
}

function getStatusLabel(successRate: number) {
  if (successRate >= 0.9) return "Excellent";
  if (successRate >= 0.7) return "Good";
  return "Poor";
}

export function AdminAgentQualityDashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<AgentQualityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string>("all");

  const fetchStats = async () => {
    try {
      setError(null);
      const data = await authRequest<AgentQualityStats>("/api/v1/admin/agent-quality/stats");
      setStats(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(t("admin.agentQuality.authRequired", "Authentication required. Please sign in again."));
      } else {
        setError(t("admin.agentQuality.loadingError", "Failed to fetch agent quality data."));
      }
      console.error("Failed to fetch agent quality stats:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchStats();

    if (!autoRefresh) return;

    const interval = window.setInterval(() => {
      void fetchStats();
    }, 30000);

    return () => {
      window.clearInterval(interval);
    };
  }, [autoRefresh]);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    void fetchStats();
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
        <SectionHead title={t("admin.agentQuality.title", "Agent Quality Monitor")}></SectionHead>
        <StatePanel tone="error">
          <p>{error}</p>
          <Button variant="secondary" size="xs" onClick={handleRetry}>
            {t("common.retry", "Retry")}
          </Button>
        </StatePanel>
      </main>
    );
  }

  const filteredAgents =
    selectedAgent === "all" ? stats?.agents || [] : stats?.agents.filter((agent) => agent.agent_name === selectedAgent) || [];

  const errorData = Object.entries(stats?.error_distribution || {}).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <main className="space-y-6">
      <SectionHead title={t("admin.agentQuality.title", "Agent Quality Monitor")}>
<RowActions>
          <ExportButtons
            data={(stats?.agents || []) as unknown as Array<Record<string, unknown>>}
            filename={`agent-quality-${new Date().toISOString().split("T")[0]}`}
          />
          <Button variant="secondary" size="xs" onClick={() => void fetchStats()}>
            {t("common.refresh", "Refresh")}
          </Button>
        </RowActions></SectionHead>

      <ControlsRow>
        <select className={ADMIN_FIELD} value={selectedAgent} onChange={(event) => setSelectedAgent(event.target.value)}>
          <option value="all">{t("admin.agentQuality.allAgents", "All Agents")}</option>
          {stats?.agents.map((agent) => (
            <option key={agent.agent_name} value={agent.agent_name}>
              {agent.agent_name}
            </option>
          ))}
        </select>

        <label className="flex shrink-0 cursor-pointer select-none items-center gap-2 whitespace-nowrap rounded-control border border-transparent px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-ink-muted transition-colors hover:border-brand-border hover:bg-brand-surface">
          <input className="size-3.5 shrink-0 accent-[var(--brand)]" type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />
          <span>{t("admin.ui.autoRefresh30", "Auto refresh every 30s")}</span>
        </label>
      </ControlsRow>

      {stats && (
        <>
          <KpiGrid cols={6}>
            <KpiCard label={t("admin.agentQuality.totalAgents", "Total Agents")} value={stats.summary.total_agents} />
            <KpiCard
              label={t("admin.agentQuality.activeAgents", "Active Agents")}
              value={stats.summary.active_agents}
              tone="success"
            />
            <KpiCard
              label={t("admin.agentQuality.totalExecutions", "Total Executions")}
              value={stats.summary.total_executions}
            />
            <KpiCard
              label={t("admin.agentQuality.successRate", "Success Rate")}
              value={`${(stats.summary.overall_success_rate * 100).toFixed(1)}%`}
              tone={getStatusTone(stats.summary.overall_success_rate)}
            />
            <KpiCard
              label={t("admin.agentQuality.avgResponseTime", "Avg Response Time")}
              value={`${stats.summary.avg_response_time.toFixed(2)}s`}
            />
          </KpiGrid>

          <TwoCol>
            <AdminBlock titleAs="h3" title={t("admin.agentQuality.successFailureTimeline", "Success/Failure Timeline")}>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={stats.timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis dataKey="timestamp" stroke={CHART_AXIS} fontSize={10} />
                  <YAxis stroke={CHART_AXIS} fontSize={12} />
                  <Tooltip
                    contentStyle={CHART_TOOLTIP}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="success" stroke="var(--success)" strokeWidth={2} name={t("admin.agentQuality.success", "Success")} />
                  <Line type="monotone" dataKey="failure" stroke="var(--danger)" strokeWidth={2} name={t("admin.agentQuality.failure", "Failure")} />
                </LineChart>
              </ResponsiveContainer>
            </AdminBlock>

            <AdminBlock titleAs="h3" title={t("admin.agentQuality.errorDistribution", "Error Distribution")}>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={errorData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} labelLine={false}>
                    {errorData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </AdminBlock>
          </TwoCol>

          <SectionBlock>
            <SubTitle>{t("admin.agentQuality.agentPerformance", "Agent Performance Details")}</SubTitle>
            <div className={ADMIN_TABLE_WRAP}>
              <table className={ADMIN_TABLE}>
                <thead>
                  <tr>
                    <th className="w-[200px]">{t("admin.agentQuality.agentName", "Agent Name")}</th>
                    <th className="w-[100px] text-right">{t("admin.agentQuality.executions", "Executions")}</th>
                    <th className="w-[100px] text-center">{t("admin.agentQuality.successRate", "Success Rate")}</th>
                    <th className="w-[120px] text-right">{t("admin.agentQuality.avgTime", "Avg Time")}</th>
                    <th className="w-[120px] text-right">{t("admin.agentQuality.avgTokens", "Avg Tokens")}</th>
                    <th className="w-[180px]">{t("admin.agentQuality.lastExecution", "Last Execution")}</th>
                    <th className="w-[100px] text-center">{t("admin.agentQuality.status", "Status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAgents.map((agent) => {
                    const statusTone = getStatusTone(agent.success_rate);
                    return (
                      <tr key={agent.agent_name}>
                        <td className="font-semibold">{agent.agent_name}</td>
                        <td className="text-right font-mono">{agent.total_executions}</td>
                        <td className="text-center">
                          <span className={`badge badge-${statusTone}`}>{(agent.success_rate * 100).toFixed(1)}%</span>
                        </td>
                        <td className="text-right font-mono">{agent.avg_execution_time.toFixed(2)}s</td>
                        <td className="text-right font-mono">{agent.avg_token_usage.toFixed(0)}</td>
                        <td className="font-mono text-[11px]">
                          {agent.last_execution ? new Date(agent.last_execution).toLocaleString() : "N/A"}
                        </td>
                        <td className="text-center">
                          <span className={`badge badge-${statusTone}`}>{getStatusLabel(agent.success_rate)}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </SectionBlock>

          <SectionBlock>
            <SubTitle>{t("admin.agentQuality.healthOverview", "Agent Health Overview")}</SubTitle>
            <TwoCol>
              <AdminBlock titleAs="h3" title={t("admin.agentQuality.executionCount", "Execution Count by Agent")}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={filteredAgents} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                    <XAxis type="number" stroke={CHART_AXIS} fontSize={11} />
                    <YAxis dataKey="agent_name" type="category" stroke={CHART_AXIS} fontSize={10} width={150} />
                    <Tooltip
                      contentStyle={CHART_TOOLTIP}
                    />
                    <Bar dataKey="total_executions" fill="var(--accent)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </AdminBlock>

              <AdminBlock titleAs="h3" title={t("admin.agentQuality.avgExecutionTime", "Avg Execution Time by Agent")}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={filteredAgents} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                    <XAxis type="number" stroke={CHART_AXIS} fontSize={11} />
                    <YAxis dataKey="agent_name" type="category" stroke={CHART_AXIS} fontSize={10} width={150} />
                    <Tooltip
                      contentStyle={CHART_TOOLTIP}
                    />
                    <Bar dataKey="avg_execution_time" fill="var(--warning)" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </AdminBlock>
            </TwoCol>
          </SectionBlock>
        </>
      )}
    </main>
  );
}
