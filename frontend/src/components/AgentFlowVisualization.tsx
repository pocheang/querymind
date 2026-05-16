import React, { useState, useEffect } from 'react';
import './AgentFlowVisualization.css';

export interface AgentNode {
  id: string;
  name: string;
  type: 'router' | 'retriever' | 'generator' | 'evaluator' | 'tool';
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime?: number;
  endTime?: number;
  input?: any;
  output?: any;
  error?: string;
}

export interface AgentEdge {
  from: string;
  to: string;
  label?: string;
  condition?: string;
}

export interface AgentFlowData {
  nodes: AgentNode[];
  edges: AgentEdge[];
  currentNode?: string;
}

interface AgentFlowVisualizationProps {
  flowData: AgentFlowData;
  onNodeClick?: (node: AgentNode) => void;
  showTimeline?: boolean;
  compact?: boolean;
}

export const AgentFlowVisualization: React.FC<AgentFlowVisualizationProps> = ({
  flowData,
  onNodeClick,
  showTimeline = true,
  compact = false
}) => {
  const [selectedNode, setSelectedNode] = useState<AgentNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const handleNodeClick = (node: AgentNode) => {
    setSelectedNode(node);
    onNodeClick?.(node);
  };

  const getNodeColor = (node: AgentNode): string => {
    if (node.status === 'failed') return '#ef4444';
    if (node.status === 'completed') return '#10b981';
    if (node.status === 'running') return '#3b82f6';
    return '#6b7280';
  };

  const getNodeIcon = (type: string): string => {
    switch (type) {
      case 'router': return '🔀';
      case 'retriever': return '🔍';
      case 'generator': return '✨';
      case 'evaluator': return '📊';
      case 'tool': return '🔧';
      default: return '⚙️';
    }
  };

  const calculateDuration = (node: AgentNode): string => {
    if (!node.startTime || !node.endTime) return '-';
    const duration = node.endTime - node.startTime;
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(2)}s`;
  };

  const renderNode = (node: AgentNode) => {
    const isActive = node.id === flowData.currentNode;
    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoveredNode === node.id;

    return (
      <div
        key={node.id}
        className={`agent-node ${node.status} ${isActive ? 'active' : ''} ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
        onClick={() => handleNodeClick(node)}
        onMouseEnter={() => setHoveredNode(node.id)}
        onMouseLeave={() => setHoveredNode(null)}
        style={{ borderColor: getNodeColor(node) }}
      >
        <div className="node-header">
          <span className="node-icon">{getNodeIcon(node.type)}</span>
          <span className="node-name">{node.name}</span>
        </div>

        {!compact && (
          <div className="node-body">
            <div className="node-type">{node.type}</div>
            <div className="node-status" style={{ color: getNodeColor(node) }}>
              {node.status}
            </div>
            {node.status === 'completed' && (
              <div className="node-duration">{calculateDuration(node)}</div>
            )}
          </div>
        )}

        {node.status === 'running' && (
          <div className="node-spinner">
            <div className="spinner"></div>
          </div>
        )}
      </div>
    );
  };

  const renderEdge = (edge: AgentEdge, index: number) => {
    const fromNode = flowData.nodes.find(n => n.id === edge.from);
    const toNode = flowData.nodes.find(n => n.id === edge.to);

    if (!fromNode || !toNode) return null;

    const isActive =
      fromNode.status === 'completed' &&
      (toNode.status === 'running' || toNode.status === 'completed');

    return (
      <div key={`edge-${index}`} className={`agent-edge ${isActive ? 'active' : ''}`}>
        <div className="edge-line"></div>
        {edge.label && (
          <div className="edge-label">{edge.label}</div>
        )}
        {edge.condition && (
          <div className="edge-condition">{edge.condition}</div>
        )}
      </div>
    );
  };

  const renderTimeline = () => {
    if (!showTimeline) return null;

    const completedNodes = flowData.nodes.filter(n => n.startTime && n.endTime);
    if (completedNodes.length === 0) return null;

    const minTime = Math.min(...completedNodes.map(n => n.startTime!));
    const maxTime = Math.max(...completedNodes.map(n => n.endTime!));
    const totalDuration = maxTime - minTime;

    return (
      <div className="agent-timeline">
        <h3>Execution Timeline</h3>
        <div className="timeline-container">
          {completedNodes.map(node => {
            const start = ((node.startTime! - minTime) / totalDuration) * 100;
            const width = ((node.endTime! - node.startTime!) / totalDuration) * 100;

            return (
              <div
                key={`timeline-${node.id}`}
                className="timeline-bar"
                style={{
                  left: `${start}%`,
                  width: `${width}%`,
                  backgroundColor: getNodeColor(node)
                }}
                title={`${node.name}: ${calculateDuration(node)}`}
              >
                <span className="timeline-label">{node.name}</span>
              </div>
            );
          })}
        </div>
        <div className="timeline-axis">
          <span>0ms</span>
          <span>{totalDuration}ms</span>
        </div>
      </div>
    );
  };

  const renderNodeDetails = () => {
    if (!selectedNode) return null;

    return (
      <div className="node-details">
        <div className="details-header">
          <h3>
            {getNodeIcon(selectedNode.type)} {selectedNode.name}
          </h3>
          <button
            className="close-button"
            onClick={() => setSelectedNode(null)}
          >
            ×
          </button>
        </div>

        <div className="details-body">
          <div className="detail-row">
            <span className="detail-label">Type:</span>
            <span className="detail-value">{selectedNode.type}</span>
          </div>

          <div className="detail-row">
            <span className="detail-label">Status:</span>
            <span
              className="detail-value"
              style={{ color: getNodeColor(selectedNode) }}
            >
              {selectedNode.status}
            </span>
          </div>

          {selectedNode.startTime && (
            <div className="detail-row">
              <span className="detail-label">Start Time:</span>
              <span className="detail-value">
                {new Date(selectedNode.startTime).toLocaleTimeString()}
              </span>
            </div>
          )}

          {selectedNode.endTime && (
            <div className="detail-row">
              <span className="detail-label">Duration:</span>
              <span className="detail-value">{calculateDuration(selectedNode)}</span>
            </div>
          )}

          {selectedNode.input && (
            <div className="detail-section">
              <h4>Input</h4>
              <pre className="detail-code">
                {JSON.stringify(selectedNode.input, null, 2)}
              </pre>
            </div>
          )}

          {selectedNode.output && (
            <div className="detail-section">
              <h4>Output</h4>
              <pre className="detail-code">
                {JSON.stringify(selectedNode.output, null, 2)}
              </pre>
            </div>
          )}

          {selectedNode.error && (
            <div className="detail-section error">
              <h4>Error</h4>
              <pre className="detail-code">{selectedNode.error}</pre>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`agent-flow-visualization ${compact ? 'compact' : ''}`}>
      <div className="flow-header">
        <h2>Agent Execution Flow</h2>
        <div className="flow-stats">
          <span className="stat">
            Total: {flowData.nodes.length}
          </span>
          <span className="stat completed">
            Completed: {flowData.nodes.filter(n => n.status === 'completed').length}
          </span>
          <span className="stat running">
            Running: {flowData.nodes.filter(n => n.status === 'running').length}
          </span>
          <span className="stat failed">
            Failed: {flowData.nodes.filter(n => n.status === 'failed').length}
          </span>
        </div>
      </div>

      <div className="flow-content">
        <div className="flow-graph">
          {flowData.nodes.map(renderNode)}
          {flowData.edges.map(renderEdge)}
        </div>

        {selectedNode && renderNodeDetails()}
      </div>

      {renderTimeline()}
    </div>
  );
};

export default AgentFlowVisualization;
