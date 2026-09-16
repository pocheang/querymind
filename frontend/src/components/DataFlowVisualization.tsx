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

// Node translations
const nodeTranslations: Record<string, { zh: string; en: string }> = (
  [
    ["1", "🌐 Browser UI\n用户界面", "🌐 Browser UI\nUser Interface"],
    [
      "2",
      "🔐 认证层 /auth/login\nJWT + HttpOnly Cookie\nPBKDF2 哈希 + Salt",
      "🔐 Auth Layer /auth/login\nJWT + HttpOnly Cookie\nPBKDF2 Hash + Salt",
    ],
    [
      "3",
      "📡 查询入口 /query/stream\nBearer Token + RBAC\n用户/管理员角色隔离",
      "📡 Query Entry /query/stream\nBearer Token + RBAC\nUser/Admin Role Isolation",
    ],
    [
      "4",
      "✅ 安全检查\n输入规范化\n危险指令拦截\nSQL注入防护",
      "✅ Security Check\nInput Normalization\nDangerous Command Block\nSQL Injection Protection",
    ],
    ["5", "⏱️ 速率限制\n管理员 1-5 req/hour\n查询配额控制", "⏱️ Rate Limit\nAdmin 1-5 req/hour\nQuery Quota Control"],
    [
      "6",
      "🔤 中文NLP预处理\n分词 + 同义词扩展\n查询重写去重优化",
      "🔤 Chinese NLP\nTokenization + Synonyms\nQuery Rewrite & Dedup",
    ],
    ["7", "🧠 高级RAG处理\n查询分解\nSelf-RAG 评估", "🧠 Advanced RAG\nQuery Decomposition\nSelf-RAG Evaluation"],
    [
      "8",
      "🎯 Router Agent\nLangGraph 工作流\n条件路由 + 分层执行\nFast/Balanced/Deep",
      "🎯 Router Agent\nLangGraph Workflow\nConditional Routing\nFast/Balanced/Deep",
    ],
    [
      "9",
      "🔍 Vector RAG Agent\n混合检索 Vector+BM25\nRRF 融合\nBGE-reranker-v2-m3",
      "🔍 Vector RAG Agent\nHybrid Retrieval Vector+BM25\nRRF Fusion\nBGE-reranker-v2-m3",
    ],
    [
      "10",
      "🕸️ Graph RAG Agent\nNeo4j 实体匹配\n邻居关系查询\nAPOC 插件",
      "🕸️ Graph RAG Agent\nNeo4j Entity Matching\nNeighbor Relations\nAPOC Plugin",
    ],
    [
      "11",
      "🌍 Web Research Agent\n外部搜索引擎\n实时信息获取",
      "🌍 Web Research Agent\nExternal Search Engine\nReal-time Info",
    ],
    [
      "12",
      "🤖 ReAct Agent\nReasoning + Acting\n迭代工具调用 (最多5轮)",
      "🤖 ReAct Agent\nReasoning + Acting\nIterative Tool Use (max 5 cycles)",
    ],
    [
      "13",
      "✨ Synthesis Agent\n答案生成 + 引用\n上下文整合",
      "✨ Synthesis Agent\nAnswer Generation + Citations\nContext Integration",
    ],
    [
      "30",
      "🎯 Route Validator Agent\n路由验证代理\n3层验证 (95%+准确率)\n规则+置信度+LLM",
      "🎯 Route Validator Agent\nRoute Validation Agent\n3-Layer Validation (95%+)\nRule+Confidence+LLM",
    ],
    [
      "31",
      "📊 Retrieval Quality Agent\n检索质量代理\n多维度指标评估\nPrecision+Recall+F1",
      "📊 Retrieval Quality Agent\nRetrieval Quality Agent\nMulti-dimensional Metrics\nPrecision+Recall+F1",
    ],
    [
      "32",
      "🛡️ Answer Validator Agent\n答案验证代理\nNLI幻觉检测 (92%+)\n3层验证流水线",
      "🛡️ Answer Validator Agent\nAnswer Validation Agent\nNLI Hallucination (92%+)\n3-Level Pipeline",
    ],
    [
      "33",
      "💭 Context Tracker Agent\n上下文跟踪代理\n多轮对话追踪 (50轮)\n线程安全LRU缓存",
      "💭 Context Tracker Agent\nContext Tracking Agent\nMulti-turn Tracking (50)\nThread-safe LRU Cache",
    ],
    [
      "34",
      "⚖️ Quality Orchestrator Agent\n质量编排代理\n分数融合 + 决策逻辑\n接受/优化/拒绝",
      "⚖️ Quality Orchestrator Agent\nQuality Orchestration Agent\nScore Fusion + Decision\nAccept/Refine/Reject",
    ],
    [
      "14",
      "💾 ChromaDB\n向量索引\n父子分块策略\nparent 1500 / child 600",
      "💾 ChromaDB\nVector Index\nParent-Child Chunks\nparent 1500 / child 600",
    ],
    [
      "15",
      "📊 BM25 + JSONL\nchunks.jsonl\nparents.jsonl\n稀疏检索",
      "📊 BM25 + JSONL\nchunks.jsonl\nparents.jsonl\nSparse Retrieval",
    ],
    [
      "16",
      "🗄️ Neo4j 5.26\n关系图谱\nAPOC 插件\n实体关系",
      "🗄️ Neo4j 5.26\nKnowledge Graph\nAPOC Plugin\nEntity Relations",
    ],
    [
      "17",
      "📄 文档处理\n流式PDF (70%内存优化)\nOCR (Tesseract)\n图像字幕",
      "📄 Document Processing\nStreaming PDF (70% Memory)\nOCR (Tesseract)\nImage Captions",
    ],
    [
      "18",
      "📤 SSE 流式返回\nchunk 返回\n心跳保活\nAgent 执行追踪",
      "📤 SSE Streaming\nChunk Response\nHeartbeat Keepalive\nAgent Execution Tracking",
    ],
    [
      "19",
      "💿 SQLite 持久化\n用户 + 会话\n审计日志\nPrompt版本 + API设置",
      "💿 SQLite Persistence\nUsers + Sessions\nAudit Log\nPrompt Version + API Config",
    ],
    [
      "20",
      "📁 会话历史\nsessions/user_*/*.json\n按用户隔离\n多会话管理",
      "📁 Session History\nsessions/user_*/*.json\nUser Isolation\nMulti-Session Management",
    ],
    [
      "21",
      "📂 文件存储\nuploads/user_*/\nOCR 缓存\n文档管理",
      "📂 File Storage\nuploads/user_*/\nOCR Cache\nDocument Management",
    ],
    [
      "22",
      "📊 运维监控\n金丝雀路由\n配置回滚\n基准测试 + 查询重放",
      "📊 Ops Monitoring\nCanary Routing\nConfig Rollback\nBenchmark + Query Replay",
    ],
    [
      "23",
      "🔧 Prompt 管理\n版本控制\n审批流 + 回滚\n性能对比",
      "🔧 Prompt Management\nVersion Control\nApproval + Rollback\nPerformance Comparison",
    ],
    [
      "24",
      "🛡️ 熔断器\n故障隔离\n舱壁模式\n重试逻辑",
      "🛡️ Circuit Breaker\nFault Isolation\nBulkhead Pattern\nRetry Logic",
    ],
    [
      "25",
      "⚡ 负载降级\n高负载检测 (>80%)\n自动降档\nFast/Balanced/Deep",
      "⚡ Load Degradation\nHigh Load Detection (>80%)\nAuto Downgrade\nFast/Balanced/Deep",
    ],
    [
      "26",
      "💨 内存缓存\n检索配置缓存\n运行时状态\n热数据加速",
      "💨 Memory Cache\nRetrieval Config Cache\nRuntime State\nHot Data Acceleration",
    ],
    [
      "27",
      "🔒 API密钥加密\nAES加密存储\n白名单URL验证\n安全配置管理",
      "🔒 API Key Encryption\nAES Encrypted Storage\nURL Whitelist\nSecure Config Management",
    ],
    [
      "28",
      "🚀 CI/CD 质门\n自动化RAG评估\n性能基准测试\n回归测试",
      "🚀 CI/CD Quality Gate\nAutomated RAG Evaluation\nPerformance Benchmarks\nRegression Testing",
    ],
    [
      "29",
      "📈 批量图表提取\n并行处理\n吞吐量优化\n图像分析",
      "📈 Batch Chart Extraction\nParallel Processing\nThroughput Optimization\nImage Analysis",
    ],
  ] as const
).reduce<Record<string, { zh: string; en: string }>>((acc, [id, zh, en]) => {
  acc[id] = { zh, en };
  return acc;
}, {});

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
  // Layer 7: Retrieval Quality Check (y: 1550)
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
