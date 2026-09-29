import type {
  AdminModelSettingsPayload,
  AdminModelSettingsView,
  AdminRuntimeSnapshot,
  AdminUserSummary,
  AuditLogEntry,
  BenchmarkTrendItem,
  ConfigSaveResponse,
  ConfigSchemaResponse,
  EffectiveModelConfigResponse,
  ModelCatalogResponse,
  OpsOverview,
  SystemLogEntry,
  ThreatIntelSource,
  ThreatIntelSourceStatus,
  WorkerScope,
} from "@/types/api";
import { request, ApiError, safeParsePayload, authFetch, parseOrThrow } from "@/services/http/client";
import {
  buildPatchRequest,
  buildPostRequest,
  buildGetRequest,
  buildQueryString,
  encodePathParam,
} from "@/services/http/requests";

export const adminUserApi = {
  adminUsers() {
    return request<AdminUserSummary[]>("/api/v1/admin/users");
  },
  adminUpdateRole(userId: string, role: string) {
    return buildPatchRequest<AdminUserSummary>(`/api/v1/admin/users/${encodePathParam(userId)}/role`, { role });
  },
  adminUpdateStatus(userId: string, statusValue: string) {
    return buildPatchRequest<AdminUserSummary>(`/api/v1/admin/users/${encodePathParam(userId)}/status`, {
      status: statusValue,
    });
  },
  adminAddCredits(userId: string, amount: number) {
    return buildPostRequest<AdminUserSummary>(`/api/v1/admin/users/${encodePathParam(userId)}/credits/add`, { amount });
  },
  adminUpdateClassification(
    userId: string,
    input: { businessUnit?: string; department?: string; userType?: string; dataScope?: string }
  ) {
    return buildPatchRequest<AdminUserSummary>(`/api/v1/admin/users/${encodePathParam(userId)}/classification`, {
      business_unit: input.businessUnit || null,
      department: input.department || null,
      user_type: input.userType || null,
      data_scope: input.dataScope || null,
    });
  },
  adminCreateAdmin(input: {
    username: string;
    password: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newAdminApprovalToken: string;
  }) {
    return buildPostRequest<AdminUserSummary>("/api/v1/admin/users/create-admin", {
      username: input.username,
      password: input.password,
      approval_token: input.approvalToken,
      ticket_id: input.ticketId,
      reason: input.reason,
      new_admin_approval_token: input.newAdminApprovalToken,
    });
  },
  adminResetApprovalToken(input: {
    userId: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newAdminApprovalToken: string;
  }) {
    return buildPostRequest<AdminUserSummary>(
      `/api/v1/admin/users/${encodePathParam(input.userId)}/reset-approval-token`,
      {
        approval_token: input.approvalToken,
        ticket_id: input.ticketId,
        reason: input.reason,
        new_admin_approval_token: input.newAdminApprovalToken,
      }
    );
  },
  adminResetPassword(input: {
    userId: string;
    approvalToken: string;
    ticketId: string;
    reason: string;
    newPassword: string;
  }) {
    return buildPostRequest<AdminUserSummary>(`/api/v1/admin/users/${encodePathParam(input.userId)}/reset-password`, {
      approval_token: input.approvalToken,
      ticket_id: input.ticketId,
      reason: input.reason,
      new_password: input.newPassword,
    });
  },
};

export const adminOpsApi = {
  adminRuntimeSnapshot() {
    return request<AdminRuntimeSnapshot>("/api/v1/admin/ops/runtime");
  },
  adminOpsOverview(input: { hours?: number; actorUserId?: string; actionKeyword?: string } = {}) {
    return buildGetRequest<OpsOverview>("/api/v1/admin/ops/overview", {
      hours: input.hours ?? 24,
      actor_user_id: input.actorUserId,
      action_keyword: input.actionKeyword,
    });
  },
  async adminOpsExportCsv(input: { hours?: number; actorUserId?: string; actionKeyword?: string } = {}) {
    const qs = buildQueryString({
      hours: input.hours ?? 24,
      actor_user_id: input.actorUserId,
      action_keyword: input.actionKeyword,
    });
    const res = await authFetch(`/api/v1/admin/ops/export.csv?${qs}`, { method: "GET" });
    if (!res.ok) {
      const text = await res.text();
      const payload = safeParsePayload(text);
      const detail =
        payload && typeof payload === "object" && !Array.isArray(payload)
          ? (payload as Record<string, unknown>).detail
          : undefined;
      throw new ApiError(res.status, typeof detail === "string" ? detail : "request failed");
    }
    return res.text();
  },
  async adminOpsExportAuditReportMd(input: { hours?: number } = {}) {
    const qs = buildQueryString({ hours: input.hours ?? 24 });
    const res = await authFetch(`/api/v1/admin/ops/audit-report.md?${qs}`, { method: "GET" });
    if (!res.ok) {
      throw new ApiError(res.status, "request failed");
    }
    return res.text();
  },
  adminBenchmarkTrends(input: { limit?: number } = {}) {
    return buildGetRequest<{ items: BenchmarkTrendItem[]; count: number }>("/api/v1/admin/ops/benchmark/trends", {
      limit: input.limit ?? 30,
    });
  },
  /**
   * Queues a benchmark run. The backend answers 202 immediately and executes
   * the (multi-minute) run in its background queue; poll adminBenchmarkTrends
   * afterwards to see the result.
   */
  adminRunBenchmark(input: { maxQueries?: number } = {}) {
    return buildPostRequest<{ ok: boolean; status: string; max_queries: number }>("/api/v1/admin/ops/benchmark/run", {
      max_queries: input.maxQueries ?? 20,
    });
  },
  adminThreatIntelStatus() {
    return buildGetRequest<{ sources: ThreatIntelSourceStatus[] }>("/api/v1/admin/threat-intel/status", {});
  },
  /** Queues a sync; 202 at once. NVD's first full sync takes hours without an API key -- use the CLI for that. */
  adminThreatIntelSync(source: ThreatIntelSource | "all") {
    return buildPostRequest<{ ok: boolean; status: string; sources: ThreatIntelSource[] }>(
      "/api/v1/admin/threat-intel/sync",
      {
        source,
      }
    );
  },
};

export const adminModelApi = {
  async modelCatalog() {
    const res = await authFetch("/api/v1/model-catalog", { method: "GET" });
    return parseOrThrow<ModelCatalogResponse>(res);
  },
  async adminModelSettings() {
    const res = await authFetch("/api/v1/admin/model-settings", { method: "GET" });
    return parseOrThrow<{ ok: boolean; settings: AdminModelSettingsView }>(res);
  },
  async adminEffectiveModelConfig() {
    const res = await authFetch("/api/v1/admin/model-settings/effective", { method: "GET" });
    return parseOrThrow<EffectiveModelConfigResponse>(res);
  },
  async adminSaveModelSettings(settings: AdminModelSettingsPayload) {
    const res = await authFetch("/api/v1/admin/model-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return parseOrThrow<{ ok: boolean; settings: AdminModelSettingsView }>(res);
  },
  async adminTestModelSettings(settings: AdminModelSettingsPayload) {
    const res = await authFetch("/api/v1/admin/model-settings/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    return parseOrThrow<{
      ok: boolean;
      reachable: boolean;
      provider: string;
      model: string;
      latency_ms: number;
      message: string;
      preview: string;
    }>(res);
  },
};

export const adminAuditApi = {
  adminAudit(input: {
    limit: number;
    actorUserId?: string;
    actionKeyword?: string;
    eventCategory?: string;
    severity?: string;
    result?: string;
  }) {
    const qs = buildQueryString({
      limit: input.limit,
      actor_user_id: input.actorUserId,
      action_keyword: input.actionKeyword,
      event_category: input.eventCategory,
      severity: input.severity,
      result: input.result,
    });
    return request<AuditLogEntry[]>(`/api/v1/admin/audit-logs?${qs}`);
  },
};

export const adminSystemLogApi = {
  adminSystemLogs(input: { limit?: number; level?: string; logger?: string; keyword?: string } = {}) {
    const qs = buildQueryString({
      limit: input.limit ?? 200,
      level: input.level,
      logger: input.logger,
      keyword: input.keyword,
    });
    return request<{ items: SystemLogEntry[]; count: number; worker?: WorkerScope }>(`/api/v1/admin/system-logs?${qs}`);
  },
};

export const adminConfigApi = {
  async adminReloadConfig() {
    const res = await authFetch("/api/v1/admin/config/reload", { method: "POST" });
    return parseOrThrow<{
      ok: boolean;
      reloaded_at: string;
      snapshot: Record<string, unknown>;
    }>(res);
  },
  /** Every editable field, its current value, and which layer supplied it. */
  configSchema() {
    return request<ConfigSchemaResponse>("/api/v1/admin/config/schema");
  },
  /** Only the fields that were actually edited; the server merges the rest into
   *  the document it already holds, so an untouched key keeps its value. */
  saveConfig(values: Record<string, string>, dataId?: string) {
    return buildPostRequest<ConfigSaveResponse>("/api/v1/admin/config/values", { values, data_id: dataId ?? null });
  },
};

export const adminApi = {
  ...adminUserApi,
  ...adminAuditApi,
  ...adminOpsApi,
  ...adminModelApi,
  ...adminSystemLogApi,
  ...adminConfigApi,
};
