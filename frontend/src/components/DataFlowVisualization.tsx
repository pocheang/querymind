import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  type ReactFlowInstance,
} from "reactflow";
import "reactflow/dist/style.css";
import "@/styles/components/data-flow.css";
import nodeTranslationsJson from "./dataFlowTranslations.json";

// Node translations
const nodeTranslations: Record<string, { zh: string; en: string }> = nodeTranslationsJson;

type NodeDef = [id: string, x: number, y: number, className: string];

const NODE_DEFINITIONS: NodeDef[] = [
  // Layer 0: User Interface (y: 0-100)
  ["1", 600, 0, "node-browser"],
  // Layer 1: Authentication & Security (y: 200-300)
  ["2", 600, 200, "node-auth"],
  ["27", 1000, 200, "node-auth"],
  // Layer 2: Query Entry & Validation (y: 400-500)
  ["3", 600, 400, "node-query"],
  ["4", 400, 500, "node-validation"],
  ["5", 800, 500, "node-validation"],
  // Layer 3: NLP Preprocessing (y: 700-800)
  ["6", 600, 700, "node-nlp"],
  ["7", 600, 850, "node-nlp"],
  ["24", 1000, 700, "node-validation"],
  ["25", 1000, 850, "node-validation"],
  // Layer 4: Router & Route Validation (y: 1000-1050)
  ["8", 600, 1000, "node-router"],
  ["30", 200, 1000, "node-validation"],
  ["23", 1000, 1000, "node-validation"],
  // Layer 5: AI Agents (y: 1200)
  ["9", 100, 1200, "node-agent"],
  ["10", 300, 1200, "node-agent"],
  ["11", 500, 1200, "node-agent"],
  ["12", 700, 1200, "node-agent"],
  ["13", 900, 1200, "node-agent"],
  ["26", 1100, 1200, "node-retrieval"],
  // Layer 6: Data Retrieval (y: 1400)
  ["14", 100, 1400, "node-retrieval"],
  ["15", 300, 1400, "node-retrieval"],
  ["16", 500, 1400, "node-retrieval"],
  ["17", 700, 1400, "node-retrieval"],
  ["29", 900, 1400, "node-retrieval"],
  // Layer 7: Offline Retrieval Evaluation (y: 1550)
  ["31", 400, 1550, "node-validation"],
  // Layer 8: Synthesis & Answer Generation (y: 1700)
  ["18", 600, 1700, "node-output"],
  ["22", 1000, 1700, "node-validation"],
  // Layer 9: Quality Assurance (y: 1900-2000)
  ["32", 400, 1900, "node-validation"],
  ["33", 800, 1900, "node-validation"],
  ["34", 600, 2050, "node-validation"],
  ["28", 1000, 2000, "node-validation"],
  // Layer 10: Final Output (y: 2250)
  ["19", 400, 2250, "node-output"],
  ["20", 600, 2250, "node-output"],
  ["21", 800, 2250, "node-output"],
];

const initialNodes: Node[] = NODE_DEFINITIONS.map(([id, x, y, className]) => ({
  id,
  type: "default",
  data: { label: "" },
  position: { x, y },
  className,
}));

type EdgeDef = [source: string, target: string, stroke?: string, dashed?: boolean, animated?: boolean];

const EDGE_DEFINITIONS: EdgeDef[] = [
  ["1", "2"],
  ["2", "3"],
  ["3", "4"],
  ["3", "5"],
  ["4", "6"],
  ["5", "6"],
  ["6", "7"],
  ["7", "8"],
  // Quality Assurance Flow - New in v0.5.0
  ["8", "30", "#10b981"],
  ["30", "9", "#10b981"],
  ["30", "10", "#10b981"],
  ["30", "11", "#10b981"],
  ["30", "12", "#10b981"],
  ["30", "13", "#10b981"],
  ["14", "31", "#10b981"],
  ["15", "31", "#10b981"],
  ["16", "31", "#10b981"],
  ["17", "31", "#10b981"],
  ["18", "32", "#10b981"],
  ["18", "33", "#10b981"],
  ["32", "34", "#10b981"],
  ["33", "34", "#10b981"],
  ["31", "34", "#10b981"],
  ["30", "34", "#10b981"],
  ["34", "19", "#10b981"],
  // Original Flow
  ["8", "9"],
  ["8", "10"],
  ["8", "11"],
  ["8", "12"],
  ["8", "13"],
  ["9", "14"],
  ["9", "15"],
  ["10", "16"],
  ["11", "17"],
  ["12", "14", "#9333ea"],
  ["12", "15", "#9333ea"],
  ["12", "16", "#9333ea"],
  ["12", "17", "#9333ea"],
  ["14", "18"],
  ["15", "18"],
  ["16", "18"],
  ["17", "18"],
  ["13", "18"],
  ["18", "19"],
  ["18", "20"],
  ["18", "21"],
  ["8", "23", "#ed8936", false, false],
  ["18", "22", "#ed8936", false, false],
  ["6", "24", "#4a5568", true, false],
  ["8", "25", "#4a5568", true, false],
  ["14", "26", "#48bb78", true, false],
  ["15", "26", "#48bb78", true, false],
  ["16", "26", "#48bb78", true, false],
  ["3", "27", "#5a67d8", true, false],
  ["18", "28", "#ed8936", true, false],
  ["17", "29", "#48bb78", true, false],
];

const initialEdges: Edge[] = EDGE_DEFINITIONS.map(([source, target, stroke, dashed, animated = true]) => {
  const edge: Edge = {
    id: `e${source}-${target}`,
    source,
    target,
    animated,
    markerEnd: { type: MarkerType.ArrowClosed },
  };
  if (stroke || dashed) {
    edge.style = {
      ...(stroke ? { stroke } : {}),
      ...(dashed ? { strokeDasharray: "5,5" } : {}),
    };
  }
  return edge;
});

export function DataFlowVisualization() {
  const { i18n } = useTranslation();
  const flowRef = useRef<ReactFlowInstance | null>(null);

  const translatedNodes = useMemo(() => {
    const lang = i18n.language === "zh" ? "zh" : "en";
    return initialNodes.map((node) => ({
      ...node,
      data: { label: nodeTranslations[node.id][lang] },
    }));
  }, [i18n.language]);

  const [nodes, setNodes, onNodesChange] = useNodesState(translatedNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const fitGraph = useMemo(
    () => () => {
      if (typeof window === "undefined") {
        return;
      }

      const padding = window.innerWidth <= 768 ? 0.2 : 0.14;
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          flowRef.current?.fitView({ padding, duration: 300 });
        });
      });
    },
    []
  );

  useEffect(() => {
    const lang = i18n.language?.startsWith("zh") ? "zh" : "en";
    const updatedNodes = initialNodes.map((node) => ({
      ...node,
      data: { label: nodeTranslations[node.id][lang] },
    }));
    setNodes(updatedNodes);
    fitGraph();
  }, [fitGraph, i18n.language, setNodes]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    const handleResize = () => {
      fitGraph();
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [fitGraph]);

  return (
    <div className="reactflow-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.14 }}
        minZoom={0.15}
        maxZoom={1.5}
        onInit={(instance) => {
          flowRef.current = instance;
          fitGraph();
        }}
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
