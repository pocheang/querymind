import { useEffect, useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function AnalyticsPage() {
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

  if (loading && !overview) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
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
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 600 }}>Analytics Dashboard</h1>
        <button
          onClick={fetchData}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#0088FE',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          Refresh
        </button>
      </div>

      {/* Statistics Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        <div
          style={{
            backgroundColor: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#666' }}>Total Queries</h3>
          <p style={{ margin: 0, fontSize: '2rem', fontWeight: 600, color: '#0088FE' }}>
            {overview?.total_queries || 0}
          </p>
        </div>

        <div
          style={{
            backgroundColor: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#666' }}>Success Rate</h3>
          <p style={{ margin: 0, fontSize: '2rem', fontWeight: 600, color: '#00C49F' }}>
            {overview?.success_rate ? `${overview.success_rate.toFixed(1)}%` : '0%'}
          </p>
        </div>

        <div
          style={{
            backgroundColor: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#666' }}>Avg Response Time</h3>
          <p style={{ margin: 0, fontSize: '2rem', fontWeight: 600, color: '#FFBB28' }}>
            {overview?.avg_total_time_ms ? `${overview.avg_total_time_ms.toFixed(0)}ms` : '0ms'}
          </p>
        </div>

        <div
          style={{
            backgroundColor: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#666' }}>Avg Docs Retrieved</h3>
          <p style={{ margin: 0, fontSize: '2rem', fontWeight: 600, color: '#FF8042' }}>
            {overview?.avg_retrieved_count ? overview.avg_retrieved_count.toFixed(1) : '0'}
          </p>
        </div>
      </div>

      {/* Charts Section */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        {/* Agent Distribution Pie Chart */}
        <div
          style={{
            backgroundColor: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', fontWeight: 600 }}>Agent Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={agentDistributionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {agentDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Agent Performance Bar Chart */}
        <div
          style={{
            backgroundColor: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', fontWeight: 600 }}>Agent Performance</h2>
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
      <div
        style={{
          backgroundColor: 'white',
          padding: '1.5rem',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          marginBottom: '2rem',
        }}
      >
        <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.2rem', fontWeight: 600 }}>
          Top 10 Retrieved Documents
        </h2>
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
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        <button
          onClick={() => handleExport('json')}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#0088FE',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: 500,
          }}
        >
          Export JSON
        </button>
        <button
          onClick={() => handleExport('csv')}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#00C49F',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem',
            fontWeight: 500,
          }}
        >
          Export CSV
        </button>
      </div>
    </div>
  );
}
