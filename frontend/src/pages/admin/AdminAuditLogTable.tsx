import type { AuditLogEntry } from "@/types/api";

type Props = {
  logs: AuditLogEntry[];
  formatAuditTime: (ts?: string | null) => string;
};

export function AdminAuditLogTable({ logs, formatAuditTime }: Props) {
  return (
    <div className="audit-table-wrap">
      <table className="table admin-audit-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>执行者</th>
            <th>动作</th>
            <th>分类</th>
            <th>级别</th>
            <th>资源</th>
            <th>结果</th>
            <th>IP</th>
            <th>User-Agent</th>
            <th>详情</th>
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
