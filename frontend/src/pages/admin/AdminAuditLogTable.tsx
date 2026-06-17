import type { AuditLogEntry } from "@/types/api";
import { useTranslation } from "react-i18next";

type Props = {
  logs: AuditLogEntry[];
  formatAuditTime: (ts?: string | null) => string;
};

export function AdminAuditLogTable({ logs, formatAuditTime }: Props) {
  const { t } = useTranslation();

  return (
    <div className="audit-table-wrap">
      <table className="table admin-audit-table">
        <thead>
          <tr>
            <th>{t("admin.ui.time")}</th>
            <th>{t("admin.ui.actor")}</th>
            <th>{t("admin.ui.action")}</th>
            <th>{t("admin.ui.category")}</th>
            <th>{t("admin.ui.severity")}</th>
            <th>{t("admin.ui.resource")}</th>
            <th>{t("admin.ui.result")}</th>
            <th>IP</th>
            <th>User-Agent</th>
            <th>{t("admin.ui.detail")}</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((x) => (
            <tr key={x.event_id}>
              <td className="audit-time">{formatAuditTime(x.created_at)}</td>
              <td className="audit-actor">
                <div className="audit-cell-stack">
                  <span className="audit-id" title={x.actor_user_id || "-"}>
                    {x.actor_user_id || "-"}
                  </span>
                  <span className="audit-sub">role: {x.actor_role || "-"}</span>
                </div>
              </td>
              <td className="audit-action">
                <span className="audit-code" title={x.action || "-"}>
                  {x.action || "-"}
                </span>
              </td>
              <td>
                <span className="audit-badge">{x.event_category || "-"}</span>
              </td>
              <td>
                <span className={`audit-badge audit-severity-${(x.severity || "none").toLowerCase()}`}>{x.severity || "-"}</span>
              </td>
              <td className="audit-resource">
                <div className="audit-cell-stack">
                  <span className="audit-code" title={x.resource_type || "-"}>
                    {x.resource_type || "-"}
                  </span>
                  <span className="audit-sub" title={x.resource_id || "-"}>
                    {x.resource_id || "-"}
                  </span>
                </div>
              </td>
              <td>
                <span className={`audit-badge audit-result-${(x.result || "none").toLowerCase()}`}>{x.result || "-"}</span>
              </td>
              <td className="audit-ip">{x.ip || "-"}</td>
              <td className="audit-user-agent" title={x.user_agent || "-"}>
                {x.user_agent || "-"}
              </td>
              <td className="audit-detail" title={x.detail || "-"}>
                {x.detail || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
