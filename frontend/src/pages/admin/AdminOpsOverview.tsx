import type { OpsOverview } from "@/types/api";
import { AdminOpsKpiCards } from "./AdminOpsKpiCards";
import { AdminOpsDiagnostics } from "./AdminOpsDiagnostics";
import { AdminOpsTrendCharts } from "./AdminOpsTrendCharts";
import { AdminOpsDataTables } from "./AdminOpsDataTables";

type Props = {
  ops: OpsOverview | null;
  loading: boolean;
  opsHours: number;
  opsAutoRefresh: boolean;
  opsActorUserId: string;
  opsActionKeyword: string;
  actionKeywordOptions: string[];
  actionMax: number;
  resourceMax: number;
  errorMax: number;
  hourlyMax: number;
  formatAuditTime: (ts?: string | null) => string;
  onRefresh: () => void;
  onExportCsv: () => void;
  onOpsHoursChange: (hours: number) => void;
  onOpsAutoRefreshChange: (enabled: boolean) => void;
  onOpsActorUserIdChange: (userId: string) => void;
  onOpsActionKeywordChange: (keyword: string) => void;
};

export function AdminOpsOverview({
  ops,
  loading,
  opsHours,
  opsAutoRefresh,
  opsActorUserId,
  opsActionKeyword,
  actionKeywordOptions,
  actionMax,
  resourceMax,
  errorMax,
  hourlyMax,
  formatAuditTime,
  onRefresh,
  onExportCsv,
  onOpsHoursChange,
  onOpsAutoRefreshChange,
  onOpsActorUserIdChange,
  onOpsActionKeywordChange,
}: Props) {
  return (
    <main className="panel ops-wrap">
      <div className="section-head">
        <strong>系统监控</strong>
        <div className="row-actions">
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>
            刷新
          </button>
          <button type="button" className="secondary tiny-btn" onClick={onExportCsv}>
            导出 CSV
          </button>
        </div>
      </div>
      <div className="ops-two-col ops-controls-row">
        <select value={opsHours} onChange={(e) => onOpsHoursChange(Number(e.target.value) || 24)}>
          <option value={1}>1小时</option>
          <option value={6}>6小时</option>
          <option value={24}>24小时</option>
          <option value={72}>72小时</option>
          <option value={168}>7天</option>
        </select>
        <label className="ops-auto-refresh">
          <input type="checkbox" checked={opsAutoRefresh} onChange={(e) => onOpsAutoRefreshChange(e.target.checked)} />
          <span>每 30 秒自动刷新</span>
        </label>
      </div>
      <div className="ops-two-col ops-filter-row">
        <input
          list="actor-user-options"
          placeholder="执行者用户ID或用户名（可选）"
          value={opsActorUserId}
          onChange={(e) => onOpsActorUserIdChange(e.target.value)}
        />
        <select value={opsActionKeyword} onChange={(e) => onOpsActionKeywordChange(e.target.value)}>
          <option value="">全部动作（可选）</option>
          {actionKeywordOptions.map((x) => (
            <option key={`ops-${x}`} value={x}>
              {x}
            </option>
          ))}
        </select>
      </div>
      <p className="muted" style={{ marginTop: -2 }}>
        筛选说明：`执行者` 支持填用户ID或用户名（系统会自动换算为用户ID）；`动作关键字` 用于筛选动作名。两个都不填表示查看全部。
      </p>
      {loading && <div className="skeleton-list" />}
      {!loading && ops && (
        <>
          <AdminOpsKpiCards ops={ops} />
          <AdminOpsTrendCharts
            ops={ops}
            actionMax={actionMax}
            resourceMax={resourceMax}
            errorMax={errorMax}
            hourlyMax={hourlyMax}
          />
          <AdminOpsDiagnostics ops={ops} />
          <AdminOpsDataTables ops={ops} formatAuditTime={formatAuditTime} />
        </>
      )}
    </main>
  );
}
