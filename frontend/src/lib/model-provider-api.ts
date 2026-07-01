/**
 * API client functions for model provider management and monitoring.
 */

import type {
  ListProvidersResponse,
  ModelMonitorStatsResponse,
} from '../types/model-providers';

/**
 * Fetch the list of available model providers from the catalog.
 */
export async function fetchProviderList(): Promise<ListProvidersResponse> {
  const response = await fetch('/admin/model-providers/list', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch provider list: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch model usage statistics and monitoring data.
 *
 * @param hours - Time window in hours (default: 24)
 */
export async function fetchModelMonitorStats(
  hours: number = 24
): Promise<ModelMonitorStatsResponse> {
  const response = await fetch(`/admin/model-monitor/stats?hours=${hours}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch model monitor stats: ${response.statusText}`);
  }

  return response.json();
}
