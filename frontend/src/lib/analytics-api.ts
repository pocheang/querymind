import { request, toUrl } from "./api-client";

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
