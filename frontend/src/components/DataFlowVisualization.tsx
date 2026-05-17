import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import '../styles/components/data-flow.css';

const initialNodes: Node[] = [
  // Layer 1: Browser
  {
    id: '1',
    type: 'default',
    data: { label: '🌐 Browser UI\n用户界面' },
    position: { x: 600, y: 0 },
    className: 'node-browser',
  },

  // Layer 2: Auth
  {
    id: '2',
    type: 'default',
    data: { label: '🔐 认证层 /auth/login\nJWT + HttpOnly Cookie\nPBKDF2 哈希 + Salt' },
    position: { x: 550, y: 120 },
    className: 'node-auth',
  },

  // Layer 3: Query Entry
  {
    id: '3',
    type: 'default',
    data: { label: '📡 查询入口 /query/stream\nBearer Token + RBAC\n用户/管理员角色隔离' },
    position: { x: 500, y: 260 },
    className: 'node-query',
  },

  // Layer 4: Security & Validation
  {
    id: '4',
    type: 'default',
    data: { label: '✅ 安全检查\n输入规范化\n危险指令拦截\nSQL注入防护' },
    position: { x: 450, y: 400 },
    className: 'node-validation',
  },

  {
    id: '5',
    type: 'default',
    data: { label: '⏱️ 速率限制\n管理员 1-5 req/hour\n查询配额控制' },
    position: { x: 750, y: 400 },
    className: 'node-validation',
  },

  // Layer 5: NLP Processing
  {
    id: '6',
    type: 'default',
    data: { label: '🔤 中文NLP预处理\n分词 + 同义词扩展\n查询重写去重优化' },
    position: { x: 550, y: 540 },
    className: 'node-nlp',
  },

  // Layer 6: Advanced RAG
  {
    id: '7',
    type: 'default',
    data: { label: '🧠 高级RAG处理\n查询分解\nSelf-RAG 评估' },
    position: { x: 550, y: 680 },
    className: 'node-nlp',
  },

  // Layer 7: Router Agent
  {
    id: '8',
    type: 'default',
    data: { label: '🎯 Router Agent\nLangGraph 工作流\n条件路由 + 分层执行\nFast/Balanced/Deep' },
    position: { x: 550, y: 820 },
    className: 'node-router',
  },

  // Layer 8: Multi-Agent System
  {
    id: '9',
    type: 'default',
    data: { label: '🔍 Vector RAG Agent\n混合检索 Vector+BM25\nRRF 融合\nBGE-reranker-v2-m3' },
    position: { x: 100, y: 980 },
    className: 'node-agent',
  },
  {
    id: '10',
    type: 'default',
    data: { label: '🕸️ Graph RAG Agent\nNeo4j 实体匹配\n邻居关系查询\nAPOC 插件' },
    position: { x: 350, y: 980 },
    className: 'node-agent',
  },
  {
    id: '11',
    type: 'default',
    data: { label: '🌍 Web Research Agent\n外部搜索引擎\n实时信息获取' },
    position: { x: 600, y: 980 },
    className: 'node-agent',
  },
  {
    id: '12',
    type: 'default',
    data: { label: '✨ Synthesis Agent\n答案生成 + 引用\n上下文整合' },
    position: { x: 850, y: 980 },
    className: 'node-agent',
  },

  // Layer 9: Retrieval & Storage
  {
    id: '13',
    type: 'default',
    data: { label: '💾 ChromaDB\n向量索引\n父子分块策略\nparent 1500 / child 600' },
    position: { x: 50, y: 1180 },
    className: 'node-retrieval',
  },
  {
    id: '14',
    type: 'default',
    data: { label: '📊 BM25 + JSONL\nchunks.jsonl\nparents.jsonl\n稀疏检索' },
    position: { x: 280, y: 1180 },
    className: 'node-retrieval',
  },
  {
    id: '15',
    type: 'default',
    data: { label: '🗄️ Neo4j 5.26\n关系图谱\nAPOC 插件\n实体关系' },
    position: { x: 510, y: 1180 },
    className: 'node-retrieval',
  },
  {
    id: '16',
    type: 'default',
    data: { label: '📄 文档处理\n流式PDF (70%内存优化)\nOCR (Tesseract)\n图像字幕' },
    position: { x: 740, y: 1180 },
    className: 'node-retrieval',
  },

  // Layer 10: Response Generation
  {
    id: '17',
    type: 'default',
    data: { label: '📤 SSE 流式返回\nchunk 返回\n心跳保活\nAgent 执行追踪' },
    position: { x: 300, y: 1360 },
    className: 'node-output',
  },

  // Layer 11: Persistence
  {
    id: '18',
    type: 'default',
    data: { label: '💿 SQLite 持久化\n用户 + 会话\n审计日志\nPrompt版本 + API设置' },
    position: { x: 150, y: 1500 },
    className: 'node-output',
  },
  {
    id: '19',
    type: 'default',
    data: { label: '📁 会话历史\nsessions/user_*/*.json\n按用户隔离\n多会话管理' },
    position: { x: 450, y: 1500 },
    className: 'node-output',
  },
  {
    id: '20',
    type: 'default',
    data: { label: '📂 文件存储\nuploads/user_*/\nOCR 缓存\n文档管理' },
    position: { x: 750, y: 1500 },
    className: 'node-output',
  },

  // Layer 12: Monitoring & Ops
  {
    id: '21',
    type: 'default',
    data: { label: '📊 运维监控\n金丝雀路由\n配置回滚\n基准测试 + 查询重放' },
    position: { x: 1100, y: 1180 },
    className: 'node-validation',
  },
  {
    id: '22',
    type: 'default',
    data: { label: '🔧 Prompt 管理\n版本控制\n审批流 + 回滚\n性能对比' },
    position: { x: 1100, y: 820 },
    className: 'node-validation',
  },

  // Layer 13: Resilience & Cache
  {
    id: '23',
    type: 'default',
    data: { label: '🛡️ 熔断器\n故障隔离\n舱壁模式\n重试逻辑' },
    position: { x: 1100, y: 540 },
    className: 'node-validation',
  },
  {
    id: '24',
    type: 'default',
    data: { label: '⚡ 负载降级\n高负载检测 (>80%)\n自动降档\nFast/Balanced/Deep' },
    position: { x: 1100, y: 680 },
    className: 'node-validation',
  },
  {
    id: '25',
    type: 'default',
    data: { label: '💨 内存缓存\n检索配置缓存\n运行时状态\n热数据加速' },
    position: { x: 1100, y: 980 },
    className: 'node-retrieval',
  },

  // Layer 14: Security & Encryption
  {
    id: '26',
    type: 'default',
    data: { label: '🔒 API密钥加密\nAES加密存储\n白名单URL验证\n安全配置管理' },
    position: { x: 1100, y: 260 },
    className: 'node-auth',
  },

  // Layer 15: CI/CD & Quality
  {
    id: '27',
    type: 'default',
    data: { label: '🚀 CI/CD 质门\n自动化RAG评估\n性能基准测试\n回归测试' },
    position: { x: 1100, y: 1360 },
    className: 'node-validation',
  },

  // Layer 16: Advanced Processing
  {
    id: '28',
    type: 'default',
    data: { label: '📈 批量图表提取\n并行处理\n吞吐量优化\n图像分析' },
    position: { x: 970, y: 1180 },
    className: 'node-retrieval',
  },
];

const initialEdges: Edge[] = [
  // Main flow
  { id: 'e1-2', source: '1', target: '2', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e2-3', source: '2', target: '3', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e3-4', source: '3', target: '4', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e3-5', source: '3', target: '5', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e4-6', source: '4', target: '6', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e5-6', source: '5', target: '6', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e6-7', source: '6', target: '7', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e7-8', source: '7', target: '8', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },

  // Router to Agents
  { id: 'e8-9', source: '8', target: '9', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e8-10', source: '8', target: '10', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e8-11', source: '8', target: '11', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e8-12', source: '8', target: '12', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },

  // Agents to Storage
  { id: 'e9-13', source: '9', target: '13', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e9-14', source: '9', target: '14', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e10-15', source: '10', target: '15', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e11-16', source: '11', target: '16', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },

  // Storage to Response
  { id: 'e13-17', source: '13', target: '17', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e14-17', source: '14', target: '17', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e15-17', source: '15', target: '17', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e16-17', source: '16', target: '17', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e12-17', source: '12', target: '17', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },

  // Response to Persistence
  { id: 'e17-18', source: '17', target: '18', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e17-19', source: '17', target: '19', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },
  { id: 'e17-20', source: '17', target: '20', animated: true, markerEnd: { type: MarkerType.ArrowClosed } },

  // Side connections - Management & Monitoring
  { id: 'e8-22', source: '8', target: '22', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ed8936' } },
  { id: 'e17-21', source: '17', target: '21', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ed8936' } },

  // Resilience & Cache connections
  { id: 'e6-23', source: '6', target: '23', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#4a5568', strokeDasharray: '5,5' } },
  { id: 'e8-24', source: '8', target: '24', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#4a5568', strokeDasharray: '5,5' } },
  { id: 'e13-25', source: '13', target: '25', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#48bb78', strokeDasharray: '5,5' } },
  { id: 'e14-25', source: '14', target: '25', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#48bb78', strokeDasharray: '5,5' } },
  { id: 'e15-25', source: '15', target: '25', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#48bb78', strokeDasharray: '5,5' } },

  // Security connections
  { id: 'e3-26', source: '3', target: '26', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#5a67d8', strokeDasharray: '5,5' } },

  // CI/CD connections
  { id: 'e17-27', source: '17', target: '27', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#ed8936', strokeDasharray: '5,5' } },

  // Advanced processing
  { id: 'e16-28', source: '16', target: '28', animated: false, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#48bb78', strokeDasharray: '5,5' } },
];

export function DataFlowVisualization() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="reactflow-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.2}
        maxZoom={1.5}
      >
        <Background color="#667eea" gap={16} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            if (node.className?.includes('browser')) return '#4a5568';
            if (node.className?.includes('auth')) return '#5a67d8';
            if (node.className?.includes('query')) return '#667eea';
            if (node.className?.includes('validation')) return '#4a5568';
            if (node.className?.includes('nlp')) return '#48bb78';
            if (node.className?.includes('router')) return '#5a67d8';
            if (node.className?.includes('agent')) return '#667eea';
            if (node.className?.includes('retrieval')) return '#48bb78';
            if (node.className?.includes('output')) return '#ed8936';
            return '#ccc';
          }}
          maskColor="rgba(0, 0, 0, 0.6)"
        />
      </ReactFlow>
    </div>
  );
}
