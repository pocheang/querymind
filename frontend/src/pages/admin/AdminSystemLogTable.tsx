import { useMemo } from "react";
import { AdminFormField, AdminFormSelect } from "@/components/AdminFormField";
import { AdminPagination } from "@/components/AdminPagination";
import { useTranslation } from "react-i18next";
import type { SystemLogEntry } from "@/types/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  AdminSkeleton,
  AuditBadge,
  CellStack,
  FilterGrid,
  Hint,
  RowActions,
  SectionHead,
  StatePanel,
} from "./components/AdminPrimitives";
import { ADMIN_FIELD, ADMIN_TABLE, ADMIN_TABLE_WIDE, ADMIN_TABLE_WRAP } from "./components/adminClasses";

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

/** A logger name or a source location: one mono line in a warm chip. */
const LOG_CODE =
  "inline-flex min-h-[26px] max-w-full items-center overflow-hidden text-ellipsis whitespace-nowrap " +
  "rounded-control border border-brand-border bg-brand-surface px-2.5 font-mono text-xs leading-tight text-ink";

/**
 * A message or a stack trace. These are the two cells in this table that WRAP
 * -- `ADMIN_TABLE_WIDE` elides everything to one line, which is right for an
 * id and useless for a traceback -- clamped to three lines.
 */
const LOG_TEXT = "line-clamp-3 whitespace-normal break-words text-xs leading-relaxed [overflow-wrap:anywhere]";

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
}: Readonly<Props>) {
  const { t } = useTranslation();

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
    <main className="space-y-6">
      <SectionHead title={t("admin.ui.systemLogs")}>
<RowActions className="flex-nowrap justify-end gap-1.5 rounded-card border border-line bg-brand-surface-hover p-1">
          <select
            className={ADMIN_FIELD + " w-auto min-w-32 shrink-0 font-mono font-semibold"}
            value={systemLogLimit}
            onChange={(e) => onSystemLogLimitChange(Number(e.target.value) || 200)}
          >
            <option value={100}>{t("admin.ui.last100")}</option>
            <option value={200}>{t("admin.ui.last200")}</option>
            <option value={500}>{t("admin.ui.last500")}</option>
          </select>
          <Button variant="secondary" size="xs" onClick={onRefresh}>
            {t("common.refresh")}
          </Button>
        </RowActions>
      </SectionHead>
      <Hint>{t("admin.ui.systemLogHint")}</Hint>
      <FilterGrid>
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
      </FilterGrid>
      <FilterGrid>
        <AdminFormField
          label={t("admin.ui.keyword")}
          value={systemLogKeyword}
          onChange={onSystemLogKeywordChange}
          placeholder={t("admin.ui.keywordPlaceholder")}
        />
        <RowActions className="self-end">
          <Button variant="secondary" size="xs" onClick={onClearFilters}>
            {t("admin.ui.clear")}
          </Button>
        </RowActions>
      </FilterGrid>
      {loadingSystemLogs && <AdminSkeleton />}
      {!loadingSystemLogs && systemLogs.length === 0 && <StatePanel>{t("admin.ui.systemLogEmpty")}</StatePanel>}
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
          <div className={ADMIN_TABLE_WRAP}>
            <table className={cn(ADMIN_TABLE, ADMIN_TABLE_WIDE, "min-w-[1360px]")}>
              <thead>
                <tr>
                  <th className="w-[170px]">{t("admin.ui.time")}</th>
                  <th className="w-[110px]">{t("admin.ui.severity")}</th>
                  <th className="w-[220px]">Logger</th>
                  <th className="w-[240px]">{t("admin.ui.location")}</th>
                  <th className="w-[320px]">{t("admin.ui.message")}</th>
                  <th className="w-[320px]">{t("admin.ui.exception")}</th>
                </tr>
              </thead>
              <tbody>
                {paginatedSystemLogs.map((x, idx) => (
                  <tr key={`${x.created_at}-${idx}`}>
                    <td>
                      <span className="font-mono text-xs text-ink/75">{formatAuditTime(x.created_at)}</span>
                    </td>
                    <td>
                      <AuditBadge value={x.level} kind="severity" />
                    </td>
                    <td>
                      <CellStack>
                        <span className={LOG_CODE} title={x.logger || "-"}>
                          {x.logger || "-"}
                        </span>
                        {x.thread ? (
                          <span className="truncate font-mono text-xs text-ink/75" title={x.thread}>
                            thread: {x.thread}
                          </span>
                        ) : null}
                      </CellStack>
                    </td>
                    <td>
                      <span className={LOG_CODE} title={formatLocation(x)}>
                        {formatLocation(x)}
                      </span>
                    </td>
                    <td>
                      <div className={cn(LOG_TEXT, "text-ink")} title={x.message || "-"}>
                        {x.message || "-"}
                      </div>
                    </td>
                    <td>
                      <div
                        className={cn(
                          LOG_TEXT,
                          x.exception
                            ? "rounded-control border border-danger-border bg-danger-surface px-2.5 py-2 text-ink-muted"
                            : "text-ink-muted",
                        )}
                        title={x.exception || "-"}
                      >
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
