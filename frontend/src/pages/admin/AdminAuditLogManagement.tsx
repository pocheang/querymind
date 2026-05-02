import type { AdminUserSummary, AuditLogEntry } from "@/types/api";
import { AdminAuditLogTable } from "@/pages/admin/AdminAuditLogTable";

const ACTION_KEYWORD_OPTIONS = [
  "auth.login",
  "auth.logout",
  "session.create",
  "session.delete",
  "query.stream",
  "document.upload",
  "document.delete",
  "prompt.create",
  "prompt.update",
  "prompt.delete",
  "admin.user.create",
  "admin.user.role_update",
  "admin.user.status_update",
  "admin.user.classification_update",
  "admin.user.password_reset",
  "admin.user.approval_token_reset",
];

type Props = {
  logs: AuditLogEntry[];
  users: AdminUserSummary[];
  loadingLogs: boolean;
  auditLimit: number;
  auditActorUserId: string;
  auditActionKeyword: string;
  auditEventCategory: string;
  auditSeverity: string;
  auditResult: string;
  formatAuditTime: (ts?: string | null) => string;
  onAuditLimitChange: (value: number) => void;
  onAuditActorUserIdChange: (value: string) => void;
  onAuditActionKeywordChange: (value: string) => void;
  onAuditEventCategoryChange: (value: string) => void;
  onAuditSeverityChange: (value: string) => void;
  onAuditResultChange: (value: string) => void;
  onRefresh: () => void;
  onClearFilters: () => void;
};

export function AdminAuditLogManagement({
  logs,
  users,
  loadingLogs,
  auditLimit,
  auditActorUserId,
  auditActionKeyword,
  auditEventCategory,
  auditSeverity,
  auditResult,
  formatAuditTime,
  onAuditLimitChange,
  onAuditActorUserIdChange,
  onAuditActionKeywordChange,
  onAuditEventCategoryChange,
  onAuditSeverityChange,
  onAuditResultChange,
  onRefresh,
  onClearFilters,
}: Props) {
  const hasExactActorMatch =
    !auditActorUserId.trim() ||
    users.some(
      (user) =>
        (user.username || "").toLowerCase() === auditActorUserId.trim().toLowerCase() ||
        user.user_id === auditActorUserId.trim(),
    );

  return (
    <main className="panel admin-audit-panel">
      <div className="section-head">
        <strong>审计日志</strong>
        <div className="row-actions admin-audit-head-actions">
          <select value={auditLimit} onChange={(e) => onAuditLimitChange(Number(e.target.value) || 200)}>
            <option value={100}>最近 100 条</option>
            <option value={200}>最近 200 条</option>
            <option value={500}>最近 500 条</option>
          </select>
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>刷新</button>
        </div>
      </div>

      <p className="muted admin-audit-hint">可按执行者、动作、分类、级别和结果筛选日志，用于回溯操作行为与安全审计。</p>

      {!hasExactActorMatch && (
        <p className="muted admin-audit-hint admin-audit-match-hint">
          当前执行者未精确匹配用户，系统将按“用户名或用户 ID 包含关系”继续筛选。
        </p>
      )}

      <div className="ops-two-col admin-filter-grid">
        <label className="admin-field">
          <span>执行者</span>
          <input list="actor-user-options" placeholder="执行者用户ID或用户名" value={auditActorUserId} onChange={(e) => onAuditActorUserIdChange(e.target.value)} />
        </label>
        <label className="admin-field">
          <span>动作</span>
          <select value={auditActionKeyword} onChange={(e) => onAuditActionKeywordChange(e.target.value)}>
            <option value="">全部动作（可选）</option>
            {ACTION_KEYWORD_OPTIONS.map((action) => (
              <option key={`audit-${action}`} value={action}>{action}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="ops-two-col admin-filter-grid">
        <label className="admin-field">
          <span>分类</span>
          <select value={auditEventCategory} onChange={(e) => onAuditEventCategoryChange(e.target.value)}>
            <option value="">全部分类</option>
            <option value="auth">auth</option>
            <option value="admin">admin</option>
            <option value="data">data</option>
            <option value="prompt">prompt</option>
            <option value="system">system</option>
          </select>
        </label>
        <label className="admin-field">
          <span>级别</span>
          <select value={auditSeverity} onChange={(e) => onAuditSeverityChange(e.target.value)}>
            <option value="">全部级别</option>
            <option value="info">info</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
      </div>

      <div className="ops-two-col admin-filter-grid">
        <label className="admin-field">
          <span>结果</span>
          <select value={auditResult} onChange={(e) => onAuditResultChange(e.target.value)}>
            <option value="">全部结果</option>
            <option value="success">success</option>
            <option value="failed">failed</option>
            <option value="denied">denied</option>
          </select>
        </label>
        <div className="row-actions admin-audit-quick-actions">
          <button type="button" className="secondary tiny-btn" onClick={() => onAuditResultChange("failed")}>仅失败</button>
          <button type="button" className="secondary tiny-btn" onClick={() => onAuditSeverityChange("high")}>仅高危</button>
          <button type="button" className="secondary tiny-btn" onClick={onClearFilters}>清空</button>
        </div>
      </div>

      {loadingLogs && <div className="skeleton-list" />}
      {!loadingLogs && <p className="muted admin-audit-scroll-hint">表格支持左右滑动查看完整列，不必在一屏内展示全部内容。</p>}
      {!loadingLogs && logs.length === 0 && <div className="status">未命中审计数据。可尝试清空“执行者 / 动作 / 分类 / 级别 / 结果”中的一个或多个筛选条件。</div>}
      {!loadingLogs && logs.length > 0 && <AdminAuditLogTable logs={logs} formatAuditTime={formatAuditTime} />}
    </main>
  );
}
