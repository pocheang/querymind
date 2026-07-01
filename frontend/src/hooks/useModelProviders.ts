/**
 * React hooks for model provider data and monitoring.
 */

import { useQuery } from '@tanstack/react-query';
import { fetchProviderList, fetchModelMonitorStats } from '../lib/model-provider-api';
import type { ProviderInfo, ModelMonitorStats } from '../types/model-providers';

/**
 * Hook to fetch and cache the provider catalog.
 */
export function useProviderList() {
  return useQuery({
    queryKey: ['providerList'],
    queryFn: fetchProviderList,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes (catalog is immutable)
    select: (data) => data.providers,
  });
}

/**
 * Hook to fetch and cache model monitoring statistics.
 *
 * @param hours - Time window in hours
 * @param enabled - Whether to enable the query
 */
export function useModelMonitorStats(hours: number = 24, enabled: boolean = true) {
  return useQuery({
    queryKey: ['modelMonitorStats', hours],
    queryFn: () => fetchModelMonitorStats(hours),
    staleTime: 30 * 1000, // Cache for 30 seconds
    refetchInterval: 60 * 1000, // Auto-refresh every minute
    enabled,
    select: (data) => data.stats,
  });
}

/**
 * Helper function to get provider by name from the catalog.
 */
export function getProviderByName(
  providers: ProviderInfo[] | undefined,
  name: string
): ProviderInfo | undefined {
  return providers?.find((p) => p.name === name);
}

/**
 * Helper function to check if a provider supports embeddings.
 */
export function providerSupportsEmbeddings(
  providers: ProviderInfo[] | undefined,
  providerName: string
): boolean {
  const provider = getProviderByName(providers, providerName);
  return provider?.supports_embeddings ?? false;
}
