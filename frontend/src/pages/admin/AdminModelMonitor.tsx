/**
 * Admin Model Monitor Dashboard
 *
 * Displays real-time model usage statistics and provider information.
 */

import React, { useState } from 'react';
import { useProviderList, useModelMonitorStats } from '../../hooks/useModelProviders';
import type { ProviderInfo } from '../../types/model-providers';

export default function AdminModelMonitor() {
  const [timeWindow, setTimeWindow] = useState(24);

  const { data: providers, isLoading: providersLoading, error: providersError } = useProviderList();
  const { data: stats, isLoading: statsLoading, error: statsError } = useModelMonitorStats(timeWindow);

  if (providersLoading || statsLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-gray-500">Loading model monitoring data...</div>
      </div>
    );
  }

  if (providersError || statsError) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-700">
          Failed to load monitoring data: {(providersError || statsError)?.toString()}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Model Monitor</h2>
          <p className="text-sm text-gray-600 mt-1">
            Real-time model usage and provider status
          </p>
        </div>

        {/* Time Window Selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-700">Time Window:</label>
          <select
            value={timeWindow}
            onChange={(e) => setTimeWindow(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm"
          >
            <option value={1}>Last Hour</option>
            <option value={6}>Last 6 Hours</option>
            <option value={24}>Last 24 Hours</option>
            <option value={168}>Last Week</option>
          </select>
        </div>
      </div>

      {/* Provider Catalog */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Providers</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {providers?.map((provider) => (
            <ProviderCard key={provider.name} provider={provider} />
          ))}
        </div>
      </div>

      {/* Usage Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Requests */}
        <StatCard
          title="Total Requests"
          value={stats?.total_requests ?? 0}
          subtitle={`Last ${timeWindow} hours`}
        />

        {/* Provider Count */}
        <StatCard
          title="Active Providers"
          value={Object.keys(stats?.by_provider ?? {}).length}
          subtitle="With recent activity"
        />

        {/* Error Count */}
        <StatCard
          title="Recent Errors"
          value={stats?.recent_errors?.length ?? 0}
          subtitle="Requiring attention"
          isError={stats?.recent_errors && stats.recent_errors.length > 0}
        />
      </div>

      {/* Usage by Provider */}
      {stats?.by_provider && Object.keys(stats.by_provider).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage by Provider</h3>
          <div className="space-y-3">
            {Object.entries(stats.by_provider)
              .sort(([, a], [, b]) => b - a)
              .map(([provider, count]) => (
                <UsageBar key={provider} label={provider} count={count} total={stats.total_requests} />
              ))}
          </div>
        </div>
      )}

      {/* Usage by Model */}
      {stats?.by_model && Object.keys(stats.by_model).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage by Model</h3>
          <div className="space-y-3">
            {Object.entries(stats.by_model)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 10)
              .map(([model, count]) => (
                <UsageBar key={model} label={model} count={count} total={stats.total_requests} />
              ))}
          </div>
        </div>
      )}

      {/* Recent Errors */}
      {stats?.recent_errors && stats.recent_errors.length > 0 && (
        <div className="bg-white rounded-lg border border-red-200 p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-4">Recent Errors</h3>
          <div className="space-y-2">
            {stats.recent_errors.map((error, idx) => (
              <div key={idx} className="p-3 bg-red-50 rounded-md text-sm">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-red-900">
                    {error.provider} / {error.model}
                  </span>
                  {error.timestamp && (
                    <span className="text-red-600 text-xs">
                      {new Date(error.timestamp).toLocaleString()}
                    </span>
                  )}
                </div>
                <p className="text-red-700">{error.error}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Provider Card Component
function ProviderCard({ provider }: { provider: ProviderInfo }) {
  return (
    <div className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-gray-900">{provider.display_name}</h4>
        {provider.requires_api_key && (
          <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
            API Key
          </span>
        )}
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex items-center gap-2">
          <span className={provider.supports_chat ? 'text-green-600' : 'text-gray-400'}>
            {provider.supports_chat ? '✓' : '✗'}
          </span>
          <span className="text-gray-700">Chat</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={provider.supports_embeddings ? 'text-green-600' : 'text-gray-400'}>
            {provider.supports_embeddings ? '✓' : '✗'}
          </span>
          <span className="text-gray-700">Embeddings</span>
        </div>
      </div>
      {provider.default_chat_model && (
        <p className="mt-2 text-xs text-gray-500 truncate" title={provider.default_chat_model}>
          Default: {provider.default_chat_model}
        </p>
      )}
    </div>
  );
}

// Stat Card Component
function StatCard({
  title,
  value,
  subtitle,
  isError = false,
}: {
  title: string;
  value: number;
  subtitle: string;
  isError?: boolean;
}) {
  return (
    <div className={`p-6 rounded-lg border ${isError ? 'bg-red-50 border-red-200' : 'bg-white border-gray-200'}`}>
      <h4 className={`text-sm font-medium ${isError ? 'text-red-700' : 'text-gray-600'}`}>
        {title}
      </h4>
      <p className={`text-3xl font-bold mt-2 ${isError ? 'text-red-900' : 'text-gray-900'}`}>
        {value.toLocaleString()}
      </p>
      <p className={`text-sm mt-1 ${isError ? 'text-red-600' : 'text-gray-500'}`}>
        {subtitle}
      </p>
    </div>
  );
}

// Usage Bar Component
function UsageBar({ label, count, total }: { label: string; count: number; total: number }) {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm text-gray-600">{count.toLocaleString()} ({percentage.toFixed(1)}%)</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
