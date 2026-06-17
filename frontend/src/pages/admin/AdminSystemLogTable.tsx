import { useMemo } from "react";
import { AdminFormField, AdminFormSelect } from "@/components/AdminFormField";
import { AdminPagination } from "@/components/AdminPagination";
import { useTranslation } from "react-i18next";
import type { SystemLogEntry } from "@/types/api";

type Props = {
  systemLogs: SystemLogEntry[];
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
  systemLogCurrentPage: number;
  systemLogPageSize: number;
  onSystemLogPageChange: (page: number) => void;
  onSystemLogPageSizeChange: (size: number) => void;
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
  systemLogCurrentPage,
  systemLogPageSize,
  onSystemLogPageChange,
  onSystemLogPageSizeChange,
}: Props) {
  const { t } = useTranslation();

  const getSeverityTone = (level?: string | null) => {
    const normalized = String(level || "").toLowerCase();
    if (normalized === "critical" || normalized === "error") return "high";
    if (normalized === "warning" || normalized === "warn") return "warning";
    return "info";
  };

  const formatLocation = (entry: SystemLogEntry) => {
    const parts = [entry.module, entry.func ? `${entry.func}()` : null, entry.line ? `L${entry.line}` : null].filter(Boolean);
    return parts.length > 0 ? parts.join(" / ") : "-";
  };

  // Client-side pagination
  const paginatedSystemLogs = useMemo(() => {
    const start = (systemLogCurrentPage - 1) * systemLogPageSize;
    const end = start + systemLogPageSize;
    return systemLogs.slice(start, end);
  }, [systemLogs, systemLogCurrentPage, systemLogPageSize]);

  return (
    <main className="panel admin-audit-panel">
      <div className="section-head">
        <strong>{t("admin.ui.systemLogs")}</strong>
        <div className="row-actions admin-audit-head-actions">
          <select value={systemLogLimit} onChange={(e) => onSystemLogLimitChange(Number(e.target.value) || 200)}>
            <option value={100}>{t("admin.ui.last100")}</option>
            <option value={200}>{t("admin.ui.last200")}</option>
            <option value={500}>{t("admin.ui.last500")}</option>
          </select>
          <button type="button" className="secondary tiny-btn" onClick={onRefresh}>{t("common.refresh")}</button>
        </div>
      </div>
      <p className="muted admin-audit-hint">{t("admin.ui.systemLogHint")}</p>
      <div className="ops-two-col admin-filter-grid">
        <AdminFormSelect
          label={t("admin.ui.severity")}
          value={systemLogLevel}
          onChange={onSystemLogLevelChange}
          options={[
            { value: "", label: t("admin.ui.allSeverities") },
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
          placeholder={t("admin.ui.loggerExample")}
        />
      </div>
      <div className="ops-two-col admin-filter-grid">
        <AdminFormField
          label={t("admin.ui.keyword")}
          value={systemLogKeyword}
          onChange={onSystemLogKeywordChange}
          placeholder={t("admin.ui.keywordPlaceholder")}
        />
        <div className="row-actions admin-audit-quick-actions">
          <button type="button" className="secondary tiny-btn" onClick={onClearFilters}>
            {t("admin.ui.clear")}
          </button>
        </div>
      </div>
      {loadingSystemLogs && <div className="skeleton-list" />}
      {!loadingSystemLogs && systemLogs.length === 0 && <div className="status">{t("admin.ui.systemLogEmpty")}</div>}
      {!loadingSystemLogs && systemLogs.length > 0 && (
        <>
          <AdminPagination
            currentPage={systemLogCurrentPage}
            pageSize={systemLogPageSize}
            totalItems={systemLogs.length}
            onPageChange={onSystemLogPageChange}
            onPageSizeChange={onSystemLogPageSizeChange}
            pageSizeOptions={[20, 50, 100]}
          />
          <div className="audit-table-wrap">
            <table className="table admin-audit-table admin-system-log-table">
              <thead>
                <tr>
                  <th>{t("admin.ui.time")}</th>
                  <th>{t("admin.ui.severity")}</th>
                  <th>Logger</th>
                  <th>{t("admin.ui.location")}</th>
                  <th>{t("admin.ui.message")}</th>
                  <th>{t("admin.ui.exception")}</th>
                </tr>
              </thead>
              <tbody>
                {paginatedSystemLogs.map((x, idx) => (
                  <tr key={`${x.created_at}-${idx}`}>
                    <td>
                      <div className="audit-cell-stack">
                        <span className="audit-time">{formatAuditTime(x.created_at)}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`audit-badge audit-severity-${getSeverityTone(x.level)}`}>
                        {x.level || "-"}
                      </span>
                    </td>
                    <td>
                      <div className="audit-cell-stack">
                        <span className="system-log-code" title={x.logger || "-"}>{x.logger || "-"}</span>
                        {x.thread ? <span className="audit-sub" title={x.thread}>thread: {x.thread}</span> : null}
                      </div>
                    </td>
                    <td>
                      <div className="audit-cell-stack">
                        <span className="system-log-code" title={formatLocation(x)}>{formatLocation(x)}</span>
                      </div>
                    </td>
                    <td>
                      <div className="system-log-text system-log-message" title={x.message || "-"}>
                        {x.message || "-"}
                      </div>
                    </td>
                    <td>
                      <div className={`system-log-text system-log-exception ${x.exception ? "has-exception" : "is-empty"}`} title={x.exception || "-"}>
                        {x.exception || "-"}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
