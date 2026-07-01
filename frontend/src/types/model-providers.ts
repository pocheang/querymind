/**
 * Shared TypeScript types for model provider configuration and monitoring.
 *
 * These types match the backend provider catalog and API responses.
 */

/**
 * Model provider information from the provider catalog.
 */
export interface ProviderInfo {
  name: string;
  display_name: string;
  supports_chat: boolean;
  supports_embeddings: boolean;
  default_chat_model: string | null;
  default_embedding_model: string | null;
  requires_api_key: boolean;
}

/**
 * Response from /admin/model-providers/list endpoint.
 */
export interface ListProvidersResponse {
  ok: boolean;
  providers: ProviderInfo[];
}

/**
 * Model usage statistics.
 */
export interface ModelMonitorStats {
  total_requests: number;
  by_provider: Record<string, number>;
  by_model: Record<string, number>;
  recent_errors: ModelError[];
  time_window_hours: number;
  metrics_snapshot?: Record<string, any>;
}

/**
 * Model error information.
 */
export interface ModelError {
  provider: string;
  model: string;
  error: string;
  timestamp?: string;
}

/**
 * Response from /admin/model-monitor/stats endpoint.
 */
export interface ModelMonitorStatsResponse {
  ok: boolean;
  stats: ModelMonitorStats;
}

/**
 * User API settings for model configuration.
 */
export interface UserModelSettings {
  provider: string;
  api_key?: string;
  base_url?: string;
  model?: string;
  chat_model?: string;
  reasoning_model?: string;
  embedding_model?: string;
  temperature?: number;
  max_tokens?: number;
}

/**
 * Admin global model settings.
 */
export interface AdminModelSettings extends UserModelSettings {
  enabled: boolean;
  api_key_masked?: string;
}
