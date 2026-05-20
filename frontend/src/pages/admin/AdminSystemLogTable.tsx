import { AdminFormField, AdminFormSelect } from "@/components/AdminFormField";

type SystemLog = {
  created_at?: string | null;
  level?: string | null;
  logger?: string | null;
  module?: string | null;
  line?: number | null;
  message?: string | null;
  exception?: string | null;
};

type Props = {
  systemLogs: SystemLog[];
  loadingSystemLogs: boolean;
  systemLogLimit: number;
  systemLogLevel: string;
  systemLogLogger: string;
  systemLogKeyword: string;
  formatAuditTime: (ts?: string | null) => string;
  onSystemLogLimitChange: (value: number) => void;
  onSystemLogLevelChange: (value: string) => void;
  onSystemLogLoggerChange: (value: string) => void;
  onSystemLogKeywordChange: (value: string) => void;
  onRefresh: () => void;
  onClearFilters: () => void;
};

export function AdminSystemLogTable({
  systemLogs,
  loadingSystemLogs,
  systemLogLimit,
  systemLogLevel,
  systemLogLogger,
  systemLogKeyword,
  formatAuditTime,
  onSystemLogLimitChange,
  onSystemLogLevelChange,
  onSystemLogLoggerChange,
  onSystemLogKeywordChange,
  onRefresh,
  onClearFilters,
}: Props) {
  return (
    <main className="panel admin-audit-panel">
      <div className="section-head">
        <strong>系统日志</strong>
        <div className="row-actions admin-audit-head-actions">
          <select value={systemLogLimit} onChange={(e) => onSystemLogLimitChange(Number(e.target.value) || 200)}>
            <option value={100}>最近 100 条</option>
            <option value={200}>最近 200 条</option>
            <option value={500}>最近 500 条</option>
          </select>
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>刷新</button>
        </div>
      </div>
      <p className="muted admin-audit-hint">展示应用运行日志（含错误堆栈），用于管理层查看系统健康与异常。</p>
      <div className="ops-two-col admin-filter-grid">
        <AdminFormSelect
          label="级别"
          value={systemLogLevel}
          onChange={onSystemLogLevelChange}
          options={[
            { value: "", label: "全部级别" },
            { value: "INFO", label: "INFO" },
            { value: "WARNING", label: "WARNING" },
            { value: "ERROR", label: "ERROR" },
            { value: "CRITICAL", label: "CRITICAL" },
          ]}
        />
        <AdminFormField
          label="Logger"
          value={systemLogLogger}
          onChange={onSystemLogLoggerChange}
          placeholder="例如 app.graph.streaming"
        />
      </div>
      <div className="ops-two-col admin-filter-grid">
        <AdminFormField
          label="关键词"
          value={systemLogKeyword}
          onChange={onSystemLogKeywordChange}
          placeholder="关键字（message/exception）"
        />
        <div className="row-actions admin-audit-quick-actions">
          <button type="button" className="secondary tiny-btn" onClick={onClearFilters}>
            清空
          </button>
        </div>
      </div>
      {loadingSystemLogs && <div className="skeleton-list" />}
      {!loadingSystemLogs && systemLogs.length === 0 && <div className="status">未命中系统日志。</div>}
      {!loadingSystemLogs && systemLogs.length > 0 && (
        <div className="audit-table-wrap">
          <table className="table admin-audit-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>级别</th>
                <th>Logger</th>
                <th>位置</th>
                <th>消息</th>
                <th>异常</th>
              </tr>
            </thead>
            <tbody>
              {systemLogs.map((x, idx) => (
                <tr key={`${x.created_at}-${idx}`}>
                  <td className="audit-time">{formatAuditTime(x.created_at)}</td>
                  <td>
                    <span className={`audit-badge audit-severity-${String(x.level || "info").toLowerCase() === "error" ? "high" : "info"}`}>
                      {x.level || "-"}
                    </span>
                  </td>
                  <td className="audit-code" title={x.logger || "-"}>{x.logger || "-"}</td>
                  <td className="audit-code" title={`${x.module || "-"}:${x.line || 0}`}>
                    {(x.module || "-") + ":" + String(x.line || 0)}
                  </td>
                  <td className="audit-detail" title={x.message || "-"}>{x.message || "-"}</td>
                  <td className="audit-detail" title={x.exception || "-"}>{x.exception || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
