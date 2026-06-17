import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
};

export function AdminOpsKpiCards({ ops }: Props) {
  const { t } = useTranslation();

  const primary = [
    [t("admin.ui.totalRequests"), ops.kpi.requests_total],
    [t("admin.ui.successfulRequests"), ops.kpi.requests_success],
    [t("admin.ui.failedRequests"), ops.kpi.requests_error],
    [t("admin.ui.errorRate"), `${ops.kpi.error_rate_percent}%`],
    [t("admin.ui.activeSessions"), ops.kpi.active_sessions],
    [t("admin.ui.activeUsers"), ops.kpi.active_users],
    [t("admin.ui.queryRequests"), ops.kpi.queries],
    [t("admin.ui.uploads"), ops.kpi.uploads],
    [t("admin.ui.loginSuccess"), ops.kpi.login_success],
    [t("admin.ui.loginFailed"), ops.kpi.login_failed],
  ];
  const secondary = [
    [t("admin.ui.totalUsers"), ops.users.total],
    [t("admin.ui.enabledUsers"), ops.users.active],
    [t("admin.ui.disabledUsers"), ops.users.disabled],
    [t("admin.ui.adminCount"), ops.users.admin],
  ];

  return (
    <>
      <div className="ops-kpi-grid ops-kpi-grid-primary">
        {primary.map(([label, value]) => (
          <div className="ops-kpi-card" key={String(label)}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="ops-kpi-grid ops-kpi-grid-secondary">
        {secondary.map(([label, value]) => (
          <div className="ops-kpi-card" key={String(label)}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </>
  );
}
