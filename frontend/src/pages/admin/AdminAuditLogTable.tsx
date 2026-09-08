import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AuditLogEntry } from "@/types/api";
import { cn } from "@/lib/utils";
import {
  AdminBlock,
  AuditBadge,
  CellStack,
  KpiCard,
  KpiGrid,
  SectionHead,
  TwoCol,
} from "./components/AdminPrimitives";
import {
  ADMIN_CODE,
  ADMIN_TABLE,
  ADMIN_TABLE_WIDE,
  ADMIN_TABLE_WRAP,
  CHART_AXIS,
  CHART_GRID,
  CHART_TOOLTIP,
} from "./components/adminClasses";

type Props = {
  logs: AuditLogEntry[];
  formatAuditTime: (ts?: string | null) => string;
};

const COLORS = ["#5b8cff", "#4fc3f7", "#8b7aff", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"];

/** A one-line mono cell: a timestamp, an ip, a secondary id. */
const MONO_CELL = "truncate font-mono text-[11px] text-ink-muted";

export function AdminAuditLogTable({ logs, formatAuditTime }: Readonly<Props>) {
  const { t } = useTranslation();

  const stats = useMemo(() => {
    const byCategory = logs.reduce<Record<string, number>>((acc, log) => {
      const category = log.event_category || "Unknown";
      acc[category] = (acc[category] || 0) + 1;
      return acc;
    }, {});

    const bySeverity = logs.reduce<Record<string, number>>((acc, log) => {
      const severity = log.severity || "Unknown";
      acc[severity] = (acc[severity] || 0) + 1;
      return acc;
    }, {});

    const byResult = logs.reduce<Record<string, number>>((acc, log) => {
      const result = log.result || "Unknown";
      acc[result] = (acc[result] || 0) + 1;
      return acc;
    }, {});

    const byActor = logs.reduce<Record<string, number>>((acc, log) => {
      const actor = log.actor_user_id || "Unknown";
      acc[actor] = (acc[actor] || 0) + 1;
      return acc;
    }, {});

    return {
      byCategory: Object.entries(byCategory).map(([name, value]) => ({ name, value })),
      bySeverity: Object.entries(bySeverity).map(([name, value]) => ({ name, value })),
      byResult: Object.entries(byResult).map(([name, value]) => ({ name, value })),
      byActor: Object.entries(byActor)
        .slice(0, 10)
        .map(([name, value]) => ({
          name: name.length > 15 ? `${name.slice(0, 15)}...` : name,
          value,
        })),
    };
  }, [logs]);

  const successRate =
    logs.length > 0 ? ((logs.filter((log) => log.result === "success").length / logs.length) * 100).toFixed(1) : 0;

  return (
    <div className="space-y-6">
      {logs.length > 0 && (
        <>
          <SectionHead title={t("admin.ui.auditStatistics", "Audit Statistics")} />

          <TwoCol>
            <AdminBlock titleAs="h3" title={t("admin.ui.byCategory", "Events by Category")}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={stats.byCategory}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    labelLine={false}
                  >
                    {stats.byCategory.map((entry, index) => (
                      <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </AdminBlock>

            <AdminBlock titleAs="h3" title={t("admin.ui.bySeverity", "Events by Severity")}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={stats.bySeverity}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis dataKey="name" stroke={CHART_AXIS} fontSize={11} />
                  <YAxis stroke={CHART_AXIS} fontSize={11} />
                  <Tooltip contentStyle={CHART_TOOLTIP} />
                  <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </AdminBlock>
          </TwoCol>

          <TwoCol className="mt-6">
            <AdminBlock titleAs="h3" title={t("admin.ui.byResult", "Events by Result")}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={stats.byResult}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis dataKey="name" stroke={CHART_AXIS} fontSize={11} />
                  <YAxis stroke={CHART_AXIS} fontSize={11} />
                  <Tooltip contentStyle={CHART_TOOLTIP} />
                  <Bar dataKey="value" fill="var(--info)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </AdminBlock>

            <AdminBlock titleAs="h3" title={t("admin.ui.topActors", "Top Actors")}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={stats.byActor} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis type="number" stroke={CHART_AXIS} fontSize={11} />
                  <YAxis dataKey="name" type="category" stroke={CHART_AXIS} fontSize={10} width={100} />
                  <Tooltip contentStyle={CHART_TOOLTIP} />
                  <Bar dataKey="value" fill="var(--warning)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </AdminBlock>
          </TwoCol>

          <KpiGrid cols={6} className="mt-5">
            <KpiCard label={t("admin.ui.totalEvents", "Total Events")} value={logs.length} />
            <KpiCard
              label={t("admin.ui.uniqueActors", "Unique Actors")}
              value={new Set(logs.map((log) => log.actor_user_id)).size}
            />
            <KpiCard label={t("admin.ui.successRate", "Success Rate")} value={`${successRate}%`} tone="success" />
            <KpiCard
              label={t("admin.ui.failureCount", "Failures")}
              value={logs.filter((log) => log.result === "failure").length}
              tone="danger"
            />
          </KpiGrid>

          <SectionHead title={t("admin.ui.detailedLogs", "Detailed Audit Logs")} />
        </>
      )}

      <div className={ADMIN_TABLE_WRAP}>
        <table className={cn(ADMIN_TABLE, ADMIN_TABLE_WIDE, "min-w-[1760px]")}>
        <thead>
          <tr>
            <th className="min-w-[170px]">{t("admin.ui.time")}</th>
            <th className="min-w-[260px]">{t("admin.ui.actor")}</th>
            <th className="min-w-[220px]">{t("admin.ui.action")}</th>
            <th className="w-[100px] text-center">{t("admin.ui.category")}</th>
            <th className="w-20 text-center">{t("admin.ui.severity")}</th>
            <th className="min-w-[260px]">{t("admin.ui.resource")}</th>
            <th className="w-20 text-center">{t("admin.ui.result")}</th>
            <th className="min-w-[110px]">IP</th>
            <th className="min-w-[360px]">{t("admin.ui.detail")}</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((entry) => (
            <tr key={entry.event_id}>
              <td className={MONO_CELL}>{formatAuditTime(entry.created_at)}</td>
              <td>
                <CellStack>
                  <span className="truncate font-mono text-[11px] font-semibold" title={entry.actor_user_id || "-"}>
                    {entry.actor_user_id || "-"}
                  </span>
                  <span className={MONO_CELL}>{entry.actor_role || "-"}</span>
                </CellStack>
              </td>
              <td>
                <span className={ADMIN_CODE} title={entry.action || "-"}>
                  {entry.action || "-"}
                </span>
              </td>
              <td className="text-center">
                <AuditBadge value={entry.event_category} />
              </td>
              <td className="text-center">
                <AuditBadge value={entry.severity} kind="severity" />
              </td>
              <td>
                <CellStack>
                  <span className={ADMIN_CODE} title={entry.resource_type || "-"}>
                    {entry.resource_type || "-"}
                  </span>
                  <span className={MONO_CELL} title={entry.resource_id || "-"}>
                    {entry.resource_id || "-"}
                  </span>
                </CellStack>
              </td>
              <td className="text-center">
                <AuditBadge value={entry.result} kind="result" />
              </td>
              <td className={MONO_CELL}>{entry.ip || "-"}</td>
              <td className="max-w-[300px] truncate text-[11px] text-ink-muted" title={entry.detail || "-"}>
                {entry.detail || "-"}
              </td>
            </tr>
          ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
