import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import type { AuthUser } from "@/types/api";
import { AdminAuditLogManagement } from "@/pages/admin/AdminAuditLogManagement";
import { AdminCreateForm } from "@/pages/admin/AdminCreateForm";
import { AdminModelSettings } from "@/pages/admin/AdminModelSettings";
import { AdminOpsOverview } from "@/pages/admin/AdminOpsOverview";
import { AdminRagSettings } from "@/pages/admin/AdminRagSettings";
import { AdminSystemLogTable } from "@/pages/admin/AdminSystemLogTable";
import { AdminUserManagement } from "@/pages/admin/AdminUserManagement";
import { useAdminActions } from "@/pages/admin/useAdminActions";
import { useAdminState } from "@/pages/admin/useAdminState";
import { formatAuditTime } from "@/pages/admin/utils";
import { ROLE_OPTIONS, STATUS_OPTIONS, ACTION_KEYWORD_OPTIONS } from "@/pages/admin/constants";

type Props = {
  user: AuthUser | null;
  onLogout: () => Promise<void>;
  themeLabel: string;
  onThemeToggle: () => void;
};

export function AdminPage({ user, onLogout, themeLabel, onThemeToggle }: Props) {
  const state = useAdminState();
  const isAdmin = useMemo(() => (user?.role || "").toLowerCase() === "admin", [user?.role]);

  const actions = useAdminActions({
    ...state,
    isAdmin,
    onLogout,
  });

  const actionMax = useMemo(() => Math.max(1, ...(state.ops?.top_actions || []).map((x) => x.count)), [state.ops]);
  const resourceMax = useMemo(() => Math.max(1, ...(state.ops?.top_resource_types || []).map((x) => x.count)), [state.ops]);
  const errorMax = useMemo(() => Math.max(1, ...(state.ops?.top_error_reasons || []).map((x) => x.count)), [state.ops]);
  const hourlyMax = useMemo(() => Math.max(1, ...(state.ops?.hourly || []).map((x) => x.count)), [state.ops]);

  const openClassEditor = (u: typeof state.users[0]) => {
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
    // eslint-disable-next-line
  }, [isAdmin]);

  useEffect(() => {
    if (isAdmin) void actions.loadLogs();
    // eslint-disable-next-line
  }, [state.auditLimit, state.auditActorUserId, state.auditActionKeyword, state.auditEventCategory, state.auditSeverity, state.auditResult, state.users.length]);

  useEffect(() => {
    if (isAdmin) void actions.loadOps();
    // eslint-disable-next-line
  }, [state.opsHours, state.opsActorUserId, state.opsActionKeyword]);

  useEffect(() => {
    if (isAdmin) void actions.loadSystemLogs();
    // eslint-disable-next-line
  }, [state.systemLogLimit, state.systemLogLevel, state.systemLogLogger, state.systemLogKeyword]);

  useEffect(() => {
    if (!isAdmin || state.section !== "ops" || !state.opsAutoRefresh) return;
    const t = window.setInterval(() => void actions.loadOps(), 30000);
    return () => window.clearInterval(t);
    // eslint-disable-next-line
  }, [isAdmin, state.section, state.opsAutoRefresh, state.opsHours, state.opsActorUserId, state.opsActionKeyword]);

  return (
    <div className="admin-shell">
      <header className="topbar">
        <div>
          <h2>管理控制台</h2>
          <p className="muted">企业级管理工作台</p>
        </div>
        <div className="top-actions">
          <button className="secondary" type="button" onClick={onThemeToggle}>{themeLabel}</button>
          <Link className="secondary link-btn" to="/app">返回聊天</Link>
          <button type="button" onClick={() => void onLogout()}>退出登录</button>
        </div>
      </header>

      {!isAdmin && (
        <main className="panel">
          <div className="status error">当前账号没有管理员权限。</div>
        </main>
      )}

      {isAdmin && (
        <>
          <main className="panel">
            <div className="row-actions wrap admin-section-tabs">
              <button type="button" className={state.section === "ops" ? "" : "secondary"} onClick={() => state.setSection("ops")}>系统运维</button>
              <button type="button" className={state.section === "rag" ? "" : "secondary"} onClick={() => state.setSection("rag")}>RAG/Agent 运维</button>
              <button type="button" className={state.section === "models" ? "" : "secondary"} onClick={() => state.setSection("models")}>模型配置</button>
              <button type="button" className={state.section === "admins" ? "" : "secondary"} onClick={() => state.setSection("admins")}>创建管理员</button>
              <button type="button" className={state.section === "users" ? "" : "secondary"} onClick={() => state.setSection("users")}>用户管理</button>
              <button type="button" className={state.section === "audit" ? "" : "secondary"} onClick={() => state.setSection("audit")}>审计日志</button>
              <button type="button" className={state.section === "syslog" ? "" : "secondary"} onClick={() => state.setSection("syslog")}>系统日志</button>
            </div>
          </main>

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
              profileState={state.profileState}
              benchmarkTrends={state.benchmarkTrends}
              benchmarkRunning={state.benchmarkRunning}
              canaryEnabled={state.canaryEnabled}
              canaryBaseline={state.canaryBaseline}
              canarySafe={state.canarySafe}
              canarySeed={state.canarySeed}
              onCanaryEnabledChange={state.setCanaryEnabled}
              onCanaryBaselineChange={state.setCanaryBaseline}
              onCanarySafeChange={state.setCanarySafe}
              onCanarySeedChange={state.setCanarySeed}
              onRefresh={() => void actions.loadRagOps()}
              onReloadConfig={() => void actions.reloadConfig()}
              onRollback={() => void actions.rollbackRuntime()}
              onExportAuditReport={() => void actions.exportAuditReportMd()}
              onSetProfile={actions.setRetrievalProfile}
              onSaveCanary={() => void actions.saveCanary()}
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
            />
          )}

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
        </>
      )}

      {state.statusText && <div className="status">{state.statusText}</div>}
      {state.error && <div className="status error">{state.error}</div>}
    </div>
  );
}
