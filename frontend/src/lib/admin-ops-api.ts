import type { OpsOverview, RetrievalProfileState, BenchmarkTrendItem } from "@/types/api";
import { request, authFetch, parseOrThrow, ApiError, safeParsePayload } from "./api-client";

export const adminOpsApi = {
  adminOpsOverview(input: { hours?: number; actorUserId?: string; actionKeyword?: string } = {}) {
    const qs = new URLSearchParams();
    qs.set("hours", String(input.hours ?? 24));
    if (input.actorUserId) qs.set("actor_user_id", input.actorUserId);
    if (input.actionKeyword) qs.set("action_keyword", input.actionKeyword);
    return request<OpsOverview>(`/admin/ops/overview?${qs.toString()}`);
  },
  async adminOpsExportCsv(input: { hours?: number; actorUserId?: string; actionKeyword?: string } = {}) {
    const qs = new URLSearchParams();
    qs.set("hours", String(input.hours ?? 24));
    if (input.actorUserId) qs.set("actor_user_id", input.actorUserId);
    if (input.actionKeyword) qs.set("action_keyword", input.actionKeyword);
    const res = await authFetch(`/admin/ops/export.csv?${qs.toString()}`, { method: "GET" });
    if (!res.ok) {
      const text = await res.text();
      const payload = safeParsePayload(text);
      throw new ApiError(res.status, String(payload?.detail || "request failed"));
    }
    return res.text();
  },
  adminOpsRetrievalProfile() {
    return request<RetrievalProfileState>("/admin/ops/retrieval-profile");
  },
  async adminOpsSetRetrievalProfile(input: { profile: string; followConfigDefault?: boolean }) {
    const res = await authFetch("/admin/ops/retrieval-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profile: input.profile,
        follow_config_default: Boolean(input.followConfigDefault),
      }),
    });
    return parseOrThrow<RetrievalProfileState>(res);
  },
  async adminOpsSetCanary(input: { enabled: boolean; baselinePercent: number; safePercent: number; seed?: string }) {
    const res = await authFetch("/admin/ops/canary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        enabled: input.enabled,
        baseline_percent: input.baselinePercent,
        safe_percent: input.safePercent,
        seed: input.seed || "default",
      }),
    });
    return parseOrThrow<RetrievalProfileState>(res);
  },
  async adminOpsRollback() {
    const res = await authFetch("/admin/ops/rollback", { method: "POST" });
    return parseOrThrow<{ ok: boolean; state: RetrievalProfileState }>(res);
  },
  async adminOpsExportAuditReportMd(input: { hours?: number } = {}) {
    const qs = new URLSearchParams();
    qs.set("hours", String(input.hours ?? 24));
    const res = await authFetch(`/admin/ops/audit-report.md?${qs.toString()}`, { method: "GET" });
    if (!res.ok) {
      throw new ApiError(res.status, "request failed");
    }
    return res.text();
  },
  adminBenchmarkTrends(input: { limit?: number } = {}) {
    const qs = new URLSearchParams();
    qs.set("limit", String(input.limit ?? 30));
    return request<{ items: BenchmarkTrendItem[]; count: number }>(`/admin/ops/benchmark/trends?${qs.toString()}`);
  },
  async adminRunBenchmark(input: { maxQueries?: number; strategy?: string } = {}) {
    const qs = new URLSearchParams();
    qs.set("max_queries", String(input.maxQueries ?? 20));
    if (input.strategy) qs.set("strategy", input.strategy);
    const res = await authFetch(`/admin/ops/benchmark/run?${qs.toString()}`, { method: "POST" });
    return parseOrThrow<{ ok: boolean; result: BenchmarkTrendItem }>(res);
  },
};
