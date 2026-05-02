import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
  actionMax: number;
  resourceMax: number;
  errorMax: number;
  hourlyMax: number;
};

export function AdminOpsTrendCharts({
  ops,
  actionMax,
  resourceMax,
  errorMax,
  hourlyMax,
}: Props) {
  return (
    <>
      {/* 高频动作 & 资源类型排行 */}
      <div className="ops-two-col">
        <div className="ops-trend-list">
          <strong>高频动作</strong>
          {ops.top_actions.map((x) => (
            <div key={x.action} className="ops-trend-row">
              <span>{x.action}</span>
              <div className="ops-trend-bar">
                <div className="ops-trend-fill" style={{ width: `${Math.max(4, (x.count / actionMax) * 100)}%` }} />
              </div>
              <strong>{x.count}</strong>
            </div>
          ))}
        </div>
        <div className="ops-trend-list">
          <strong>资源类型排行</strong>
          {ops.top_resource_types.map((x) => (
            <div key={x.resource_type} className="ops-trend-row">
              <span>{x.resource_type}</span>
              <div className="ops-trend-bar">
                <div className="ops-trend-fill" style={{ width: `${Math.max(4, (x.count / resourceMax) * 100)}%` }} />
              </div>
              <strong>{x.count}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* 高频错误原因 & 服务健康状态 */}
      <div className="ops-two-col">
        <div className="ops-trend-list">
          <strong>高频错误原因</strong>
          {ops.top_error_reasons.map((x) => (
            <div key={x.reason} className="ops-trend-row">
              <span title={x.reason}>{x.reason.slice(0, 18)}</span>
              <div className="ops-trend-bar">
                <div className="ops-trend-fill" style={{ width: `${Math.max(4, (x.count / errorMax) * 100)}%` }} />
              </div>
              <strong>{x.count}</strong>
            </div>
          ))}
        </div>
        <div className="ops-trend-list">
          <strong>服务健康状态</strong>
          {Object.entries(ops.services || {}).map(([name, svc]) => (
            <div key={name} className="ops-trend-row">
              <span>{name}</span>
              <strong>{svc.ok ? `正常（${svc.latency_ms ?? 0}ms）` : `异常：${svc.error || "unknown"}`}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* 按小时趋势 */}
      <div className="ops-trend-list">
        <strong>按小时趋势</strong>
        {ops.hourly.map((x) => (
          <div key={x.bucket} className="ops-trend-row">
            <span>{x.bucket.slice(11, 16)}</span>
            <div className="ops-trend-bar">
              <div className="ops-trend-fill" style={{ width: `${Math.max(4, (x.count / hourlyMax) * 100)}%` }} />
            </div>
            <strong>
              {x.count}/{x.errors}
            </strong>
          </div>
        ))}
      </div>
    </>
  );
}
