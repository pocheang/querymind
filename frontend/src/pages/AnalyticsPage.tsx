import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { AuthUser } from '@/types/api';
import { getThemeIcon } from '@/lib/theme';
import '../styles/pages/analytics.css';

interface AnalyticsOverview {
  total_queries: number;
  success_rate: number;
  avg_retrieval_time_ms: number;
  avg_total_time_ms: number;
  avg_retrieved_count: number;
  agent_distribution: Record<string, number>;
  route_distribution: Record<string, number>;
}

interface AgentStats {
  agent_class: string;
  query_count: number;
  success_rate: number;
  avg_retrieval_time_ms: number;
  avg_retrieved_count: number;
}

interface DocumentStats {
  source: string;
  retrieval_count: number;
  avg_score: number;
}

type Props = {
  user: AuthUser | null;
  onLogout: () => Promise<void>;
  themeLabel: string;
  onThemeToggle: () => void;
};

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export function AnalyticsPage({ onLogout, themeLabel, onThemeToggle }: Props) {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [agents, setAgents] = useState<AgentStats[]>([]);
  const [documents, setDocuments] = useState<DocumentStats[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch overview
      const overviewRes = await fetch('/api/analytics/overview');
      const overviewData = await overviewRes.json();
      setOverview(overviewData);

      // Fetch agent stats
      const agentsRes = await fetch('/api/analytics/agents');
      const agentsData = await agentsRes.json();
      setAgents(agentsData);

      // Fetch document stats
      const docsRes = await fetch('/api/analytics/documents?limit=10');
      const docsData = await docsRes.json();
      setDocuments(docsData);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(); // Initial load
    const interval = setInterval(fetchData, 10000); // 10 seconds
    return () => clearInterval(interval);
  }, []);

  const handleExport = (format: 'json' | 'csv') => {
    window.open(`/api/analytics/export?format=${format}`, '_blank');
  };

  const themeIcon = getThemeIcon(themeLabel);

  if (loading && !overview) {
    return (
      <div className="analytics-loading">
        <p>Loading analytics...</p>
      </div>
    );
  }

  // Prepare chart data
  const agentDistributionData = overview?.agent_distribution
    ? Object.entries(overview.agent_distribution).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const agentPerformanceData = agents.map(agent => ({
    name: agent.agent_class,
    queries: agent.query_count,
    success_rate: agent.success_rate,
    avg_time: agent.avg_retrieval_time_ms,
  }));

  const documentHeatmapData = documents.map(doc => ({
    name: doc.source.length > 30 ? doc.source.substring(0, 27) + '...' : doc.source,
    retrievals: doc.retrieval_count,
    avg_score: doc.avg_score,
  }));

  return (
    <div className="analytics-page">
      {/* Header */}
      <header className="analytics-header">
        <div className="analytics-header-content">
          <h2>监控分析</h2>
          <p>系统性能和使用情况分析</p>
        </div>
        <div className="analytics-header-actions">
          <button onClick={onThemeToggle} className="theme-btn">
            {themeIcon} {themeLabel}
          </button>
          <Link to="/app/admin" className="back-btn">
            ← 返回管理
          </Link>
          <button
            onClick={() => void onLogout()}
            className="logout-btn"
          >
            退出登录
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="analytics-content">
      {/* Refresh Button */}
      <div className="analytics-title-bar">
        <h1>Analytics Dashboard</h1>
        <button
          onClick={fetchData}
          className="refresh-btn"
        >
          Refresh
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="analytics-stats-grid">
        <div className="stat-card-analytics blue">
          <h3>Total Queries</h3>
          <p>{overview?.total_queries || 0}</p>
        </div>

        <div className="stat-card-analytics green">
          <h3>Success Rate</h3>
          <p>{overview?.success_rate ? `${overview.success_rate.toFixed(1)}%` : '0%'}</p>
        </div>

        <div className="stat-card-analytics yellow">
          <h3>Avg Response Time</h3>
          <p>{overview?.avg_total_time_ms ? `${overview.avg_total_time_ms.toFixed(0)}ms` : '0ms'}</p>
        </div>

        <div className="stat-card-analytics orange">
          <h3>Avg Docs Retrieved</h3>
          <p>{overview?.avg_retrieved_count ? overview.avg_retrieved_count.toFixed(1) : '0'}</p>
        </div>
      </div>

      {/* Charts Section */}
      <div className="analytics-charts-grid">
        {/* Agent Distribution Pie Chart */}
        <div className="chart-card">
          <h2>Agent Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={agentDistributionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {agentDistributionData.map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Agent Performance Bar Chart */}
        <div className="chart-card">
          <h2>Agent Performance</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={agentPerformanceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="queries" fill="#0088FE" name="Query Count" />
              <Bar dataKey="success_rate" fill="#00C49F" name="Success Rate (%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Document Heatmap - Full Width */}
      <div className="chart-card-full">
        <h2>Top 10 Retrieved Documents</h2>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={documentHeatmapData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" width={200} />
            <Tooltip />
            <Legend />
            <Bar dataKey="retrievals" fill="#0088FE" name="Retrieval Count" />
            <Bar dataKey="avg_score" fill="#FFBB28" name="Avg Score" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Export Buttons */}
      <div className="analytics-export-actions">
        <button
          onClick={() => handleExport('json')}
          className="export-btn json"
        >
          Export JSON
        </button>
        <button
          onClick={() => handleExport('csv')}
          className="export-btn csv"
        >
          Export CSV
        </button>
      </div>
      </div>
    </div>
  );
}
