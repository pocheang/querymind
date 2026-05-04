import type { OpsOverview } from "@/types/api";

type Props = {
  ops: OpsOverview;
  formatAuditTime: (ts?: string | null) => string;
};

export function AdminOpsDataTables({ ops, formatAuditTime }: Props) {
  const recentFailures = ops?.diagnostics?.recent_failures ?? [];
  const recentErrors = ops?.diagnostics?.recent_errors ?? [];

  return (
    <>
      {/* 最近失败请求 */}
      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>最近失败请求</strong>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>路径</th>
            <th>状态码</th>
            <th>耗时</th>
            <th>错误</th>
          </tr>
        </thead>
        <tbody>
          {(recentFailures.length > 0 ? recentFailures : []).map((x, idx) => (
            <tr key={`${x.ts}-${idx}`}>
              <td>{x.ts}</td>
              <td>{x.path}</td>
              <td>{x.status_code}</td>
              <td>{x.duration_ms}</td>
              <td>{x.error || "-"}</td>
            </tr>
          ))}
          {recentFailures.length === 0 && (
            <tr>
              <td colSpan={5}>暂无失败请求</td>
            </tr>
          )}
        </tbody>
      </table>

      {/* 最近严重错误 */}
      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>最近严重错误</strong>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>Logger</th>
            <th>消息</th>
            <th>异常</th>
          </tr>
        </thead>
        <tbody>
          {(recentErrors.length > 0 ? recentErrors : []).map((x, idx) => (
            <tr key={`${x.created_at}-${idx}`}>
              <td>{formatAuditTime(x.created_at)}</td>
              <td>{x.logger || "-"}</td>
              <td>{x.message || "-"}</td>
              <td title={x.exception || "-"}>{x.exception || "-"}</td>
            </tr>
          ))}
          {recentErrors.length === 0 && (
            <tr>
              <td colSpan={4}>暂无严重错误</td>
            </tr>
          )}
        </tbody>
      </table>

      {/* 慢请求列表 */}
      <div className="section-head" style={{ marginTop: 4 }}>
        <strong>慢请求列表</strong>
      </div>
      <p className="muted" style={{ marginTop: -2, marginBottom: 8 }}>
        展示当前时间窗口内耗时较高的接口请求，用于排查性能瓶颈。时间为服务器记录时间，耗时单位为毫秒（ms）。
      </p>
      <table className="table">
        <thead>
          <tr>
            <th>时间</th>
            <th>方法</th>
            <th>路径</th>
            <th>状态码</th>
            <th>耗时</th>
            <th>错误</th>
          </tr>
        </thead>
        <tbody>
          {ops.slow_requests.map((x, idx) => (
            <tr key={`${x.ts}-${idx}`}>
              <td>{x.ts}</td>
              <td>{x.method}</td>
              <td>{x.path}</td>
              <td>{x.status_code}</td>
              <td>{x.duration_ms}</td>
              <td>{x.error || "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
