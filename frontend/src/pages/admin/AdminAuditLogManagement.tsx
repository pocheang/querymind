import type { AdminUserSummary, AuditLogEntry } from "@/types/api";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import { AdminAuditLogTable } from "@/pages/admin/AdminAuditLogTable";
import { AdminFormSelect } from "@/components/AdminFormField";
import { AdminPagination } from "@/components/AdminPagination";
import { ACTION_KEYWORD_OPTIONS } from "@/pages/admin/constants";
import { Button } from "@/components/ui/button";
import {
  AdminField,
  AdminSkeleton,
  FilterGrid,
  Hint,
  RowActions,
  SectionHead,
  StatePanel,
} from "./components/AdminPrimitives";
import { ADMIN_FIELD } from "./components/adminClasses";
import { LogLimitActions } from "./components/LogLimitActions";


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
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
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
  currentPage,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: Readonly<Props>) {
  const { t } = useTranslation();
  const hasExactActorMatch =
    !auditActorUserId.trim() ||
    users.some(
      (user) =>
        (user.username || "").toLowerCase() === auditActorUserId.trim().toLowerCase() ||
        user.user_id === auditActorUserId.trim(),
    );

  const paginatedLogs = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return logs.slice(start, end);
  }, [logs, currentPage, pageSize]);

  return (
    <main className="space-y-6">
      <SectionHead title={t("admin.auditLog")}>
        <LogLimitActions limit={auditLimit} onLimitChange={onAuditLimitChange} onRefresh={onRefresh} />
      </SectionHead>

      <Hint>{t("admin.ui.auditHint")}</Hint>

      {!hasExactActorMatch && (
        <Hint className="-mt-1.5 text-info">{t("admin.ui.actorFuzzyHint")}</Hint>
      )}

      <FilterGrid>
        <AdminField label={t("admin.ui.actor")}>
          <input
            className={ADMIN_FIELD}
            list="actor-user-options"
            placeholder={t("admin.ui.actorPlaceholder")}
            value={auditActorUserId}
            onChange={(e) => onAuditActorUserIdChange(e.target.value)}
          />
        </AdminField>
        <AdminFormSelect
          label={t("admin.ui.action")}
          value={auditActionKeyword}
          onChange={onAuditActionKeywordChange}
          options={[
            { value: "", label: t("admin.ui.allActions") },
            ...ACTION_KEYWORD_OPTIONS.map((action) => ({ value: action, label: action })),
          ]}
        />
      </FilterGrid>

      <FilterGrid>
        <AdminFormSelect
          label={t("admin.ui.category")}
          value={auditEventCategory}
          onChange={onAuditEventCategoryChange}
          options={[
            { value: "", label: t("admin.ui.allCategories") },
            { value: "auth", label: "auth" },
            { value: "admin", label: "admin" },
            { value: "data", label: "data" },
            { value: "prompt", label: "prompt" },
            { value: "system", label: "system" },
          ]}
        />
        <AdminFormSelect
          label={t("admin.ui.severity")}
          value={auditSeverity}
          onChange={onAuditSeverityChange}
          options={[
            { value: "", label: t("admin.ui.allSeverities") },
            { value: "info", label: "info" },
            { value: "medium", label: "medium" },
            { value: "high", label: "high" },
          ]}
        />
      </FilterGrid>

      <FilterGrid>
        <AdminFormSelect
          label={t("admin.ui.result")}
          value={auditResult}
          onChange={onAuditResultChange}
          options={[
            { value: "", label: t("admin.ui.allResults") },
            { value: "success", label: "success" },
            { value: "failed", label: "failed" },
            { value: "denied", label: "denied" },
          ]}
        />
        <RowActions className="self-end">
          <Button variant="secondary" size="xs" onClick={() => onAuditResultChange("failed")}>{t("admin.ui.failedOnly")}</Button>
          <Button variant="secondary" size="xs" onClick={() => onAuditSeverityChange("high")}>{t("admin.ui.highRiskOnly")}</Button>
          <Button variant="secondary" size="xs" onClick={onClearFilters}>
            {t("admin.ui.clear")}
          </Button>
        </RowActions>
      </FilterGrid>

      {loadingLogs && <AdminSkeleton />}
      {!loadingLogs && <Hint className="-mt-0.5 mb-0.5">{t("admin.ui.auditScrollHint")}</Hint>}
      {!loadingLogs && logs.length === 0 && <StatePanel>{t("admin.ui.auditEmpty")}</StatePanel>}
      {!loadingLogs && logs.length > 0 && (
        <>
          <AdminPagination
            currentPage={currentPage}
            pageSize={pageSize}
            totalItems={logs.length}
            onPageChange={onPageChange}
            onPageSizeChange={onPageSizeChange}
            pageSizeOptions={[20, 50, 100]}
          />
          <AdminAuditLogTable logs={paginatedLogs} formatAuditTime={formatAuditTime} />
        </>
      )}
    </main>
  );
}
