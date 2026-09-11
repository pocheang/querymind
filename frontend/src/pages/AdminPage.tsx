import { useEffect, useMemo, useState } from "react";
import { BarChart3 } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/layout/AppShell";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import type { AuthUser } from "@/types/api";
import type { Section } from "@/stores/useAdminStore";
import { AdminAgentQualityDashboard } from "@/pages/admin/AdminAgentQualityDashboard";
import { AdminAuditLogManagement } from "@/pages/admin/AdminAuditLogManagement";
import { AdminCreateForm } from "@/pages/admin/AdminCreateForm";
import { AdminModelSettings } from "@/pages/admin/AdminModelSettings";
import { AdminOpsOverview } from "@/pages/admin/AdminOpsOverview";
import { AdminRagSettings } from "@/pages/admin/AdminRagSettings";
import { AdminSystemLogTable } from "@/pages/admin/AdminSystemLogTable";
import { AdminSystemMonitor } from "@/pages/admin/AdminSystemMonitor";
import { AdminUserManagement } from "@/pages/admin/AdminUserManagement";
import { AdminWebActivityDashboard } from "@/pages/admin/AdminWebActivityDashboard";
import { useAdminActions } from "@/pages/admin/useAdminActions";
import { useAdminState } from "@/pages/admin/useAdminState";
import { formatAuditTime } from "@/pages/admin/utils";
import { ROLE_OPTIONS, STATUS_OPTIONS, ACTION_KEYWORD_OPTIONS } from "@/pages/admin/constants";
import { PromptDialog } from "@/components/PromptDialog";
import { usePromptDialog } from "@/hooks/usePromptDialog";

// Route-specific CSS (code-split by Vite)
import { StatePanel } from "@/pages/admin/components/AdminPrimitives";

type Props = {
  user: AuthUser | null;
  onLogout: () => Promise<void>;
};

/* The console's ten sections, in the order they are shown. A table rather
   than ten near-identical buttons: the previous form encoded "selected" as an
   EMPTY className and "not selected" as "secondary", which only reads
   correctly if you already know the convention. */
const ADMIN_SECTIONS: ReadonlyArray<{ key: Section; labelKey: string; fallback?: string }> = [
  { key: "ops", labelKey: "pages.admin.sections.ops" },
  { key: "monitor", labelKey: "pages.admin.sections.monitor", fallback: "Runtime Monitor" },
  { key: "rag", labelKey: "pages.admin.sections.rag" },
  { key: "models", labelKey: "pages.admin.sections.models" },
  { key: "webactivity", labelKey: "pages.admin.sections.webactivity", fallback: "Web Activity" },
  { key: "agentquality", labelKey: "pages.admin.sections.agentquality", fallback: "Agent Quality" },
  { key: "admins", labelKey: "pages.admin.sections.admins" },
  { key: "users", labelKey: "pages.admin.sections.users" },
  { key: "audit", labelKey: "pages.admin.sections.audit" },
  { key: "syslog", labelKey: "pages.admin.sections.syslog" },
];

export function AdminPage({ user, onLogout }: Readonly<Props>) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const state = useAdminState();
  const isAdmin = useMemo(() => (user?.role || "").toLowerCase() === "admin", [user?.role]);
  const promptDialog = usePromptDialog();
  // Pagination state for audit logs
  const [auditPage, setAuditPage] = useState(1);
  const [auditPageSize, setAuditPageSize] = useState(20);

  // Pagination state for system logs
  const [systemLogCurrentPage, setSystemLogCurrentPage] = useState(1);
  const [systemLogPageSize, setSystemLogPageSize] = useState(20);

  const actions = useAdminActions({
    ...state,
    isAdmin,
    onLogout,
    promptInput: promptDialog.promptInput,
  });

  const actionMax = useMemo(() => Math.max(1, ...(state.ops?.top_actions || []).map((x) => x.count)), [state.ops]);
  const resourceMax = useMemo(
    () => Math.max(1, ...(state.ops?.top_resource_types || []).map((x) => x.count)),
    [state.ops]
  );
  const errorMax = useMemo(() => Math.max(1, ...(state.ops?.top_error_reasons || []).map((x) => x.count)), [state.ops]);
  const hourlyMax = useMemo(() => Math.max(1, ...(state.ops?.hourly || []).map((x) => x.count)), [state.ops]);

  const openClassEditor = (u: (typeof state.users)[0]) => {
    state.setEditingUser(u);
    state.setEditBu(u.business_unit || "");
    state.setEditDept(u.department || "");
    state.setEditType(u.user_type || "");
    state.setEditScope(u.data_scope || "");
  };

  useEffect(() => {
    void actions.loadUsers();
    void actions.loadLogs();
    void actions.loadSystemLogs();
    void actions.loadOps();
    void actions.loadRagOps();
    void actions.loadModelSettings();
    // Fires on the filter values, not on the action identity. The rule is
    // named rather than left bare: a bare disable turns off every rule on
    // the line, which is how a real finding hides behind an intended one.
    // The directive has to be the last line of this comment, or it points
    // at the comment instead of the code.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  useEffect(() => {
    if (isAdmin) void actions.loadLogs();
    // Fires on the filter values, not on the action identity. The rule is
    // named rather than left bare: a bare disable turns off every rule on
    // the line, which is how a real finding hides behind an intended one.
    // The directive has to be the last line of this comment, or it points
    // at the comment instead of the code.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    state.auditLimit,
    state.auditActorUserId,
    state.auditActionKeyword,
    state.auditEventCategory,
    state.auditSeverity,
    state.auditResult,
    state.users.length,
  ]);

  useEffect(() => {
    if (isAdmin) void actions.loadOps();
    // Fires on the filter values, not on the action identity. The rule is
    // named rather than left bare: a bare disable turns off every rule on
    // the line, which is how a real finding hides behind an intended one.
    // The directive has to be the last line of this comment, or it points
    // at the comment instead of the code.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.opsHours, state.opsActorUserId, state.opsActionKeyword]);

  useEffect(() => {
    if (isAdmin) void actions.loadSystemLogs();
    // Fires on the filter values, not on the action identity. The rule is
    // named rather than left bare: a bare disable turns off every rule on
    // the line, which is how a real finding hides behind an intended one.
    // The directive has to be the last line of this comment, or it points
    // at the comment instead of the code.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.systemLogLimit, state.systemLogLevel, state.systemLogLogger, state.systemLogKeyword]);

  useEffect(() => {
    if (!isAdmin || state.section !== "ops" || !state.opsAutoRefresh) return;
    const t = window.setInterval(() => void actions.loadOps(), 30000);
    return () => window.clearInterval(t);
    // Fires on the filter values, not on the action identity. The rule is
    // named rather than left bare: a bare disable turns off every rule on
    // the line, which is how a real finding hides behind an intended one.
    // The directive has to be the last line of this comment, or it points
    // at the comment instead of the code.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, state.section, state.opsAutoRefresh, state.opsHours, state.opsActorUserId, state.opsActionKeyword]);

  // Reset audit pagination when filters change
  useEffect(() => {
    setAuditPage(1);
  }, [
    state.auditLimit,
    state.auditActorUserId,
    state.auditActionKeyword,
    state.auditEventCategory,
    state.auditSeverity,
    state.auditResult,
  ]);

  // Reset system log pagination when filters change
  useEffect(() => {
    setSystemLogCurrentPage(1);
  }, [state.systemLogLevel, state.systemLogLogger, state.systemLogKeyword]);

  return (
    <AppShell user={user} onLogout={onLogout} scroll>
      <PromptDialog
        isOpen={promptDialog.isOpen}
        title={promptDialog.options?.title || ""}
        message={promptDialog.options?.message || ""}
        defaultValue={promptDialog.options?.defaultValue}
        inputType={promptDialog.options?.inputType}
        onConfirm={promptDialog.handleConfirm}
        onCancel={promptDialog.handleCancel}
      />
      {/* Title, subtitle and the section rail share one glass bar, which is
          how the design prototype builds this view: the tabs are the page's
          primary navigation, not a control strip under a heading. */}
      <div className="glass-panel flex shrink-0 flex-col gap-2 border-x-0 border-t-0 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-base font-bold tracking-tight text-ink sm:text-lg">{t("pages.admin.console")}</h1>
          <p className="text-xs sm:text-sm text-ink/75">{t("pages.admin.subtitle")}</p>
        </div>

        <div className="flex items-center gap-2">
          {isAdmin && (
            <div
              className="no-scrollbar flex items-center gap-1 overflow-x-auto pb-1 sm:pb-0"
              role="tablist"
              aria-label={t("pages.admin.console")}
            >
              {ADMIN_SECTIONS.map(({ key, labelKey, fallback }) => {
                const active = state.section === key;
                return (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    className={cn(
                      "whitespace-nowrap rounded-control px-3 py-1.5 text-xs sm:text-sm transition-all",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                      active
                        ? "bg-[image:var(--brand-gradient)] font-semibold text-white shadow-elev-1"
                        : "font-medium text-ink-muted hover:bg-brand-surface hover:text-brand-text"
                    )}
                    onClick={() => state.setSection(key)}
                  >
                    {fallback ? t(labelKey, fallback) : t(labelKey)}
                  </button>
                );
              })}
            </div>
          )}
          <Button
            className="shrink-0 text-xs sm:text-sm font-semibold"
            variant="secondary"
            size="sm"
            onClick={() => navigate("/app/analytics")}
          >
            <BarChart3 className="size-3.5" aria-hidden="true" />
            {t("pages.admin.viewAnalytics")}
          </Button>
        </div>
      </div>

      {!isAdmin && (
        <div className="p-4 sm:p-6">
          <p
            className="rounded-control border border-danger-border bg-danger-surface px-3 py-2 text-xs sm:text-sm font-medium text-danger"
            role="alert"
          >
            {t("pages.admin.noPermission")}
          </p>
        </div>
      )}

      {isAdmin && (
        <div className="space-y-6 p-4 sm:p-6">
          {state.section === "admins" && (
            <AdminCreateForm
              adminUsername={state.adminUsername}
              adminPassword={state.adminPassword}
              adminPassword2={state.adminPassword2}
              adminApprovalToken={state.adminApprovalToken}
              newAdminApprovalToken={state.newAdminApprovalToken}
              adminTicketId={state.adminTicketId}
              adminReason={state.adminReason}
              creatingAdmin={state.creatingAdmin}
              onAdminUsernameChange={state.setAdminUsername}
              onAdminPasswordChange={state.setAdminPassword}
              onAdminPassword2Change={state.setAdminPassword2}
              onAdminApprovalTokenChange={state.setAdminApprovalToken}
              onNewAdminApprovalTokenChange={state.setNewAdminApprovalToken}
              onAdminTicketIdChange={state.setAdminTicketId}
              onAdminReasonChange={state.setAdminReason}
              onCreateAdmin={() => void actions.createAdmin()}
            />
          )}

          {state.section === "monitor" && <AdminSystemMonitor />}
          {state.section === "ops" && (
            <AdminOpsOverview
              ops={state.ops}
              loading={state.loadingOps}
              opsHours={state.opsHours}
              opsAutoRefresh={state.opsAutoRefresh}
              opsActorUserId={state.opsActorUserId}
              opsActionKeyword={state.opsActionKeyword}
              actionKeywordOptions={ACTION_KEYWORD_OPTIONS}
              actionMax={actionMax}
              resourceMax={resourceMax}
              errorMax={errorMax}
              hourlyMax={hourlyMax}
              formatAuditTime={formatAuditTime}
              onRefresh={() => void actions.loadOps()}
              onExportCsv={() => void actions.exportOpsCsv()}
              onOpsHoursChange={state.setOpsHours}
              onOpsAutoRefreshChange={state.setOpsAutoRefresh}
              onOpsActorUserIdChange={state.setOpsActorUserId}
              onOpsActionKeywordChange={state.setOpsActionKeyword}
            />
          )}

          {state.section === "models" && (
            <AdminModelSettings
              modelSettings={state.modelSettings}
              modelLoading={state.modelLoading}
              modelSaving={state.modelSaving}
              modelTesting={state.modelTesting}
              modelTestResult={state.modelTestResult}
              onRefresh={() => void actions.loadModelSettings()}
              onSave={() => void actions.saveModelSettings()}
              onTest={() => void actions.testModelSettings()}
              onPatch={actions.patchModelSettings}
              modelApiKey={state.modelApiKey}
              onApiKeyChange={state.setModelApiKey}
            />
          )}

          {state.section === "rag" && (
            <AdminRagSettings
              benchmarkTrends={state.benchmarkTrends}
              benchmarkRunning={state.benchmarkRunning}
              onRefresh={() => void actions.loadRagOps()}
              onReloadConfig={() => void actions.reloadConfig()}
              onExportAuditReport={() => void actions.exportAuditReportMd()}
              onRunBenchmark={() => void actions.runBenchmark()}
              formatAuditTime={formatAuditTime}
            />
          )}

          {state.section === "users" && (
            <AdminUserManagement
              users={state.users}
              loadingUsers={state.loadingUsers}
              kw={state.kw}
              fRole={state.fRole}
              fStatus={state.fStatus}
              fOnline={state.fOnline}
              editingUser={state.editingUser}
              editBu={state.editBu}
              editDept={state.editDept}
              editType={state.editType}
              editScope={state.editScope}
              savingClass={state.savingClass}
              roleOptions={ROLE_OPTIONS}
              statusOptions={STATUS_OPTIONS}
              onKwChange={state.setKw}
              onFRoleChange={state.setFRole}
              onFStatusChange={state.setFStatus}
              onFOnlineChange={state.setFOnline}
              onEditingUserChange={state.setEditingUser}
              onEditBuChange={state.setEditBu}
              onEditDeptChange={state.setEditDept}
              onEditTypeChange={state.setEditType}
              onEditScopeChange={state.setEditScope}
              onLoadUsers={() => void actions.loadUsers()}
              onSaveClass={() => void actions.saveClass()}
              onUpdateRole={actions.updateRole}
              onUpdateStatus={actions.updateStatus}
              onAddCredits={actions.addUserCredits}
              onOpenClassEditor={openClassEditor}
              onResetPassword={actions.resetUserPassword}
              onResetApprovalToken={actions.resetAdminApprovalToken}
            />
          )}

          {state.section === "audit" && (
            <AdminAuditLogManagement
              logs={state.logs}
              users={state.users}
              loadingLogs={state.loadingLogs}
              auditLimit={state.auditLimit}
              auditActorUserId={state.auditActorUserId}
              auditActionKeyword={state.auditActionKeyword}
              auditEventCategory={state.auditEventCategory}
              auditSeverity={state.auditSeverity}
              auditResult={state.auditResult}
              formatAuditTime={formatAuditTime}
              onAuditLimitChange={state.setAuditLimit}
              onAuditActorUserIdChange={state.setAuditActorUserId}
              onAuditActionKeywordChange={state.setAuditActionKeyword}
              onAuditEventCategoryChange={state.setAuditEventCategory}
              onAuditSeverityChange={state.setAuditSeverity}
              onAuditResultChange={state.setAuditResult}
              onRefresh={() => void actions.loadLogs()}
              onClearFilters={() => {
                state.setAuditActorUserId("");
                state.setAuditActionKeyword("");
                state.setAuditEventCategory("");
                state.setAuditSeverity("");
                state.setAuditResult("");
              }}
              currentPage={auditPage}
              pageSize={auditPageSize}
              onPageChange={setAuditPage}
              onPageSizeChange={setAuditPageSize}
            />
          )}

          {state.section === "syslog" && (
            <AdminSystemLogTable
              systemLogs={state.systemLogs}
              loadingSystemLogs={state.loadingSystemLogs}
              systemLogLimit={state.systemLogLimit}
              systemLogLevel={state.systemLogLevel}
              systemLogLogger={state.systemLogLogger}
              systemLogKeyword={state.systemLogKeyword}
              formatAuditTime={formatAuditTime}
              onSystemLogLimitChange={state.setSystemLogLimit}
              onSystemLogLevelChange={state.setSystemLogLevel}
              onSystemLogLoggerChange={state.setSystemLogLogger}
              onSystemLogKeywordChange={state.setSystemLogKeyword}
              onRefresh={() => void actions.loadSystemLogs()}
              onClearFilters={() => {
                state.setSystemLogLevel("");
                state.setSystemLogLogger("");
                state.setSystemLogKeyword("");
              }}
              systemLogCurrentPage={systemLogCurrentPage}
              systemLogPageSize={systemLogPageSize}
              onSystemLogPageChange={setSystemLogCurrentPage}
              onSystemLogPageSizeChange={setSystemLogPageSize}
            />
          )}

          {state.section === "webactivity" && <AdminWebActivityDashboard />}

          {state.section === "agentquality" && <AdminAgentQualityDashboard />}

          <datalist id="actor-user-options">
            {state.users.map((u) => (
              <option key={`actor-user-${u.user_id}`} value={u.username}>
                {`${u.username} (${u.user_id})`}
              </option>
            ))}
            {state.users.map((u) => (
              <option key={`actor-id-${u.user_id}`} value={u.user_id}>
                {`${u.username} (${u.user_id})`}
              </option>
            ))}
          </datalist>
        </div>
      )}

      {state.statusText && (
        <StatePanel className="mx-4 mb-4 font-mono sm:mx-6">{state.statusText}</StatePanel>
      )}
      {state.error && (
        <StatePanel tone="error" className="mx-4 mb-4 font-mono sm:mx-6">
          {state.error}
        </StatePanel>
      )}
    </AppShell>
  );
}
