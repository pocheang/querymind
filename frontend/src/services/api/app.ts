import { request, toUrl, authFetch, parseOrThrow } from "@/services/http/client";
import { sessionApi, queryApi, documentApi, promptApi } from "./chat";

export interface AnalyticsOverview {
  total_queries: number;
  success_rate: number;
  avg_retrieval_time_ms: number;
  avg_total_time_ms: number;
  avg_retrieved_count: number;
  agent_distribution: Record<string, number>;
  route_distribution: Record<string, number>;
}

export interface AgentStats {
  agent_class: string;
  query_count: number;
  success_rate: number;
  avg_retrieval_time_ms: number;
  avg_retrieved_count: number;
}

export interface DocumentStats {
  source: string;
  retrieval_count: number;
  avg_score: number;
}

export const analyticsApi = {
  overview() {
    return request<AnalyticsOverview>("/api/analytics/overview");
  },

  agents() {
    return request<AgentStats[]>("/api/analytics/agents");
  },

  documents(limit = 10) {
    return request<DocumentStats[]>(`/api/analytics/documents?limit=${limit}`);
  },

  exportUrl(format: "json" | "csv") {
    return toUrl(`/api/analytics/export?format=${format}`);
  },
};

export const userSettingsApi = {
  /**
   * What model is answering, for a reader who cannot change it.
   *
   * Read-only by design: models are configured by an administrator and applied
   * to every user. This replaced three `/user/api-settings` endpoints that let
   * any signed-in user save a provider, key and model -- and were never once
   * consulted when answering their questions.
   */
  async getActiveModel() {
    const res = await authFetch("/user/active-model", { method: "GET" });
    return parseOrThrow<{
      ok: boolean;
      managed_by_admin: boolean;
      provider: string;
      model: string;
    }>(res);
  },
};

export const appApi = {
  ...sessionApi,
  ...queryApi,
  ...documentApi,
  ...promptApi,
  ...userSettingsApi,
};
