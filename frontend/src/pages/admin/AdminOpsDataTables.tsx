import { useTranslation } from "react-i18next";
import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
  formatAuditTime: (ts?: string | null) => string;
};

export function AdminOpsDataTables({ ops, formatAuditTime }: Props) {
  const { t } = useTranslation();
  const recentFailures = ops?.diagnostics?.recent_failures ?? [];
  const recentErrors = ops?.diagnostics?.recent_errors ?? [];

  return (
    <>
      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>{t("admin.ui.recentFailedRequests")}</strong>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>{t("admin.ui.time")}</th>
            <th>{t("admin.ui.path")}</th>
            <th>{t("admin.ui.statusCode")}</th>
            <th>{t("admin.ui.duration")}</th>
            <th>{t("admin.ui.error")}</th>
          </tr>
        </thead>
        <tbody>
          {recentFailures.map((item, index) => (
            <tr key={`${item.ts}-${index}`}>
              <td>{item.ts}</td>
              <td>{item.path}</td>
              <td>{item.status_code}</td>
              <td>{item.duration_ms}</td>
              <td>{item.error || "-"}</td>
            </tr>
          ))}
          {recentFailures.length === 0 && (
            <tr>
              <td colSpan={5}>{t("admin.ui.noFailedRequests")}</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>{t("admin.ui.recentCriticalErrors")}</strong>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>{t("admin.ui.time")}</th>
            <th>Logger</th>
            <th>{t("admin.ui.message")}</th>
            <th>{t("admin.ui.exception")}</th>
          </tr>
        </thead>
        <tbody>
          {recentErrors.map((item, index) => (
            <tr key={`${item.created_at}-${index}`}>
              <td>{formatAuditTime(item.created_at)}</td>
              <td>{item.logger || "-"}</td>
              <td>{item.message || "-"}</td>
              <td title={item.exception || "-"}>{item.exception || "-"}</td>
            </tr>
          ))}
          {recentErrors.length === 0 && (
            <tr>
              <td colSpan={4}>{t("admin.ui.noCriticalErrors")}</td>
            </tr>
          )}
        </tbody>
      </table>

      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>{t("admin.ui.slowRequests")}</strong>
      </div>
      <p className="muted" style={{ marginTop: -2, marginBottom: 8 }}>
        {t("admin.ui.slowRequestsHint")}
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>{t("admin.ui.time")}</th>
            <th>{t("admin.ui.method")}</th>
            <th>{t("admin.ui.path")}</th>
            <th>{t("admin.ui.statusCode")}</th>
            <th>{t("admin.ui.duration")}</th>
            <th>{t("admin.ui.error")}</th>
          </tr>
        </thead>
        <tbody>
          {ops.slow_requests.map((item, index) => (
            <tr key={`${item.ts}-${index}`}>
              <td>{item.ts}</td>
              <td>{item.method}</td>
              <td>{item.path}</td>
              <td>{item.status_code}</td>
              <td>{item.duration_ms}</td>
              <td>{item.error || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
