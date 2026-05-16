import { useState, useEffect, useCallback } from 'react';
import { AgentFlowData, AgentNode } from '../components/AgentFlowVisualization';

interface UseAgentFlowTrackerOptions {
  sessionId?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface AgentFlowTracker {
  flowData: AgentFlowData;
  isLoading: boolean;
  error: string | null;
  updateNode: (nodeId: string, updates: Partial<AgentNode>) => void;
  addNode: (node: AgentNode) => void;
  reset: () => void;
  refresh: () => Promise<void>;
}

export const useAgentFlowTracker = (
  options: UseAgentFlowTrackerOptions = {}
): AgentFlowTracker => {
  const { sessionId, autoRefresh = false, refreshInterval = 1000 } = options;

  const [flowData, setFlowData] = useState<AgentFlowData>({
    nodes: [],
    edges: [],
    currentNode: undefined
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateNode = useCallback((nodeId: string, updates: Partial<AgentNode>) => {
    setFlowData(prev => ({
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId ? { ...node, ...updates } : node
      )
    }));
  }, []);

  const addNode = useCallback((node: AgentNode) => {
    setFlowData(prev => ({
      ...prev,
      nodes: [...prev.nodes, node],
      currentNode: node.id
    }));
  }, []);

  const reset = useCallback(() => {
    setFlowData({
      nodes: [],
      edges: [],
      currentNode: undefined
    });
    setError(null);
  }, []);

  const refresh = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/agent-flow/${sessionId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch flow data: ${response.statusText}`);
      }

      const data = await response.json();
      setFlowData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Failed to refresh agent flow:', err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !sessionId) return;

    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, sessionId, refreshInterval, refresh]);

  // Initial load
  useEffect(() => {
    if (sessionId) {
      refresh();
    }
  }, [sessionId, refresh]);

  return {
    flowData,
    isLoading,
    error,
    updateNode,
    addNode,
    reset,
    refresh
  };
};

// Hook for WebSocket-based real-time updates
export const useAgentFlowWebSocket = (sessionId?: string) => {
  const [flowData, setFlowData] = useState<AgentFlowData>({
    nodes: [],
    edges: [],
    currentNode: undefined
  });

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/agent-flow/${sessionId}`;

    let ws: WebSocket;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log('WebSocket connected for agent flow tracking');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case 'flow_init':
              setFlowData(message.data);
              break;

            case 'node_update':
              setFlowData(prev => ({
                ...prev,
                nodes: prev.nodes.map(node =>
                  node.id === message.data.id
                    ? { ...node, ...message.data }
                    : node
                ),
                currentNode: message.data.status === 'running' ? message.data.id : prev.currentNode
              }));
              break;

            case 'node_add':
              setFlowData(prev => ({
                ...prev,
                nodes: [...prev.nodes, message.data],
                currentNode: message.data.id
              }));
              break;

            case 'edge_add':
              setFlowData(prev => ({
                ...prev,
                edges: [...prev.edges, message.data]
              }));
              break;

            case 'flow_complete':
              setFlowData(prev => ({
                ...prev,
                currentNode: undefined
              }));
              break;

            default:
              console.warn('Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        setError('WebSocket error occurred');
        console.error('WebSocket error:', event);
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
      console.error('Failed to create WebSocket:', err);
    }

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId]);

  return {
    flowData,
    isConnected,
    error
  };
};

export default useAgentFlowTracker;
