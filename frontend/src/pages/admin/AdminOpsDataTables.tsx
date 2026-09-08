import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { OpsOverview } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import {
  AdminBlock,
  KpiCard,
  KpiGrid,
  Muted,
  SectionBlock,
  SectionHead,
  StateIcon,
  StatePanel,
  TwoCol,
} from "./components/AdminPrimitives";
import { ADMIN_TABLE, ADMIN_TABLE_WRAP, CHART_AXIS, CHART_GRID, CHART_TOOLTIP } from "./components/adminClasses";

type Props = {
  ops: OpsOverview;
  formatAuditTime: (ts?: string | null) => string;
};

const COLORS = ["#5b8cff", "#4fc3f7", "#8b7aff", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899"];

/** Cells that hold an id, a path or a stack trace: mono, one line, elided. */
const MONO_CELL = "truncate font-mono";

export function AdminOpsDataTables({ ops, formatAuditTime }: Readonly<Props>) {
  const { t } = useTranslation();
  const recentFailures = ops?.diagnostics?.recent_failures ?? [];
  const recentErrors = ops?.diagnostics?.recent_errors ?? [];

  const failuresByStatus = recentFailures.reduce<Record<string, number>>((acc, item) => {
    const status = item.status_code.toString();
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});

  const statusChartData = Object.entries(failuresByStatus).map(([status, count]) => ({
    status,
    count,
    name: `HTTP ${status}`,
  }));

  const errorsByLogger = recentErrors.reduce<Record<string, number>>((acc, item) => {
    const logger = item.logger || "Unknown";
    acc[logger] = (acc[logger] || 0) + 1;
    return acc;
  }, {});

  const loggerChartData = Object.entries(errorsByLogger).map(([logger, count]) => ({
    logger: logger.length > 20 ? `${logger.slice(0, 20)}...` : logger,
    count,
  }));

  const failureTimeline = recentFailures
    .slice(0, 10)
    .reverse()
    .map((item, index) => ({
      time: `T-${10 - index}`,
      count: 1,
      duration: item.duration_ms,
    }));

  return (
    <>
      <SectionHead className="mt-6" title={t("admin.ui.recentFailedRequests", "Recent Failed Requests")} />

      {recentFailures.length > 0 ? (
        <SectionBlock className="mt-4 gap-4">
          <TwoCol>
            <AdminBlock titleAs="h3" title={t("admin.ui.failureByStatus", "Failures by Status Code")}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={statusChartData}
                    dataKey="count"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    labelLine={false}
                  >
                    {statusChartData.map((entry) => (
                      <Cell
                        key={entry.status}
                        fill={COLORS[Object.keys(failuresByStatus).indexOf(entry.status) % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </AdminBlock>

            <AdminBlock titleAs="h3" title={t("admin.ui.failureTimeline", "Failure Timeline")}>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={failureTimeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis dataKey="time" stroke={CHART_AXIS} fontSize={11} />
                  <YAxis stroke={CHART_AXIS} fontSize={11} />
                  <Tooltip contentStyle={CHART_TOOLTIP} />
                  <Line
                    type="monotone"
                    dataKey="duration"
                    stroke="var(--danger)"
                    strokeWidth={2}
                    dot={{ fill: "var(--danger)" }}
                    name="Duration (ms)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </AdminBlock>
          </TwoCol>

          <div className={ADMIN_TABLE_WRAP}>
            <table className={ADMIN_TABLE}>
              <thead>
                <tr>
                  <th className="w-36">{t("admin.ui.time", "Time")}</th>
                  <th className="w-52">{t("admin.ui.path", "Path")}</th>
                  <th className="w-20 text-center">{t("admin.ui.statusCode", "Status")}</th>
                  <th className="w-24 text-right">{t("admin.ui.duration", "Duration")}</th>
                  <th>{t("admin.ui.error", "Error")}</th>
                </tr>
              </thead>
              <tbody>
                {recentFailures.map((item, index) => (
                  <tr key={`${item.ts}-${index}`}>
                    <td className={MONO_CELL}>{formatAuditTime(item.ts)}</td>
                    <td className={MONO_CELL}>{item.path}</td>
                    <td className="text-center">
                      <Badge variant="danger" mono>
                        {item.status_code}
                      </Badge>
                    </td>
                    <td className="text-right font-mono">{item.duration_ms}ms</td>
                    <td className="max-w-[400px] truncate" title={item.error || "-"}>
                      {item.error || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionBlock>
      ) : (
        <StatePanel tone="success">
          <StateIcon tone="success">OK</StateIcon>
          <p className="text-ink">{t("admin.ui.noFailedRequests", "No failed requests")}</p>
          <Muted>{t("admin.ui.systemHealthy", "System is running smoothly")}</Muted>
        </StatePanel>
      )}

      <SectionHead className="mt-6" title={t("admin.ui.recentCriticalErrors", "Recent Critical Errors")} />

      {recentErrors.length > 0 ? (
        <SectionBlock className="mt-4 gap-4">
          <TwoCol>
            <AdminBlock titleAs="h3" title={t("admin.ui.errorByLogger", "Errors by Logger")}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={loggerChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
                  <XAxis
                    dataKey="logger"
                    stroke={CHART_AXIS}
                    fontSize={10}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis stroke={CHART_AXIS} fontSize={11} />
                  <Tooltip contentStyle={CHART_TOOLTIP} />
                  <Bar dataKey="count" fill="var(--danger)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </AdminBlock>

            <AdminBlock titleAs="h3" title={t("admin.ui.errorSummary", "Error Summary")}>
              <KpiGrid cols={5} className="mb-0">
                <KpiCard label={t("admin.ui.totalErrors", "Total Errors")} value={recentErrors.length} tone="danger" />
                <KpiCard
                  label={t("admin.ui.uniqueLoggers", "Unique Loggers")}
                  value={Object.keys(errorsByLogger).length}
                />
              </KpiGrid>
            </AdminBlock>
          </TwoCol>

          <div className={ADMIN_TABLE_WRAP}>
            <table className={ADMIN_TABLE}>
              <thead>
                <tr>
                  <th className="w-36">{t("admin.ui.time", "Time")}</th>
                  <th className="w-40">Logger</th>
                  <th>{t("admin.ui.message", "Message")}</th>
                  <th className="w-64">{t("admin.ui.exception", "Exception")}</th>
                </tr>
              </thead>
              <tbody>
                {recentErrors.map((item, index) => (
                  <tr key={`${item.created_at}-${index}`}>
                    <td className={MONO_CELL}>{formatAuditTime(item.created_at)}</td>
                    <td className={MONO_CELL}>{item.logger || "-"}</td>
                    <td className="max-w-[300px] truncate" title={item.message || "-"}>
                      {item.message || "-"}
                    </td>
                    <td className="max-w-[250px] truncate font-mono" title={item.exception || "-"}>
                      {item.exception || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionBlock>
      ) : (
        <StatePanel tone="success">
          <StateIcon tone="success">OK</StateIcon>
          <p className="text-ink">{t("admin.ui.noCriticalErrors", "No critical errors")}</p>
          <Muted>{t("admin.ui.noErrorsDetected", "No errors detected in the system")}</Muted>
        </StatePanel>
      )}
    </>
  );
}
