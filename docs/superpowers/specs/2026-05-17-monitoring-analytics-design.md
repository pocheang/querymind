# RAG 系统监控和分析功能设计文档

**日期：** 2026-05-17  
**版本：** 1.0  
**状态：** 设计阶段

## 1. 概述

### 1.1 目标

为多智能体 RAG 系统添加监控和分析功能，实时追踪检索性能、Agent 使用情况和文档热度，帮助优化系统配置和文档分类策略。

### 1.2 核心需求

- 记录每次检索的详细日志（问题、Agent、检索结果、性能指标）
- 提供实时统计分析（总查询数、成功率、平均响应时间）
- 分析 Agent 性能（使用频率、成功率、响应时间）
- 分析文档热度（最常被检索的文档 Top 10）
- 提供可视化监控仪表板
- 支持数据导出（CSV/JSON）

### 1.3 非目标

- 不实现长期历史数据存储（使用内存存储）
- 不实现告警功能
- 不实现实时推送（使用轮询）
- 不实现用户级别的监控（全局统计）

## 2. 技术选型

### 2.1 存储方案

**选择：内存存储 + 可选文件导出**

- 使用 Python `collections.deque(maxlen=1000)` 存储最近 1000 条记录
- 系统重启后数据丢失（符合实时监控定位）
- 提供 API 导出为 CSV/JSON 用于离线分析

**理由：**
- 与现有 `agent_execution_tracker` 保持一致
- 实现简单，无需额外数据库
- 性能最优，适合实时监控
- 满足核心需求（最近一段时间的数据分析）

### 2.2 前端图表库

**选择：Recharts**

- React 原生图表库，声明式 API
- 体积适中（~400KB）
- 支持柱状图、折线图、饼图
- 与项目技术栈（React + TypeScript）完美集成

### 2.3 数据更新机制

**选择：定时轮询（每 10 秒）**

- 前端使用 `setInterval` 每 10 秒请求最新数据
- 实现简单，兼容性好
- 10 秒延迟对监控场景完全可接受

## 3. 系统架构

### 3.1 整体架构

```
用户查询 → stream_processor → 检索节点 → RetrievalLogger.log()
                                              ↓
                                         内存存储 (最近1000条)
                                              ↓
前端轮询 → Analytics API → 聚合统计 → 返回 JSON → Recharts 渲染
```

### 3.2 核心组件

#### 3.2.1 RetrievalLogger 服务

**文件：** `app/services/retrieval_logger.py`

**职责：**
- 记录检索日志
- 提供统计聚合方法
- 导出数据

**特性：**
- 单例模式，全局唯一实例
- 线程安全（使用 `threading.Lock()`）
- 自动限制内存（`deque(maxlen=1000)`）

#### 3.2.2 Analytics API

**文件：** `app/api/routes/analytics.py`

**端点：**
- `GET /api/analytics/overview` - 总览统计
- `GET /api/analytics/agents` - Agent 性能分析
- `GET /api/analytics/documents` - 文档热度分析
- `GET /api/analytics/export?format=json|csv` - 导出数据

#### 3.2.3 前端监控页面

**文件：** `frontend/src/pages/AnalyticsPage.tsx`

**组件结构：**
- Header（标题 + 刷新按钮）
- StatCards（统计卡片：总查询数、成功率、平均时间、平均文档数）
- ChartsSection（图表区域）
  - AgentDistributionChart（饼图 - Agent 分布）
  - AgentPerformanceChart（柱状图 - Agent 性能对比）
  - DocumentHeatmapChart（柱状图 - 文档热度 Top 10）
- ExportButton（导出按钮）

#### 3.2.4 日志注入点

**位置：**
- `app/graph/streaming/stream_processor.py` - 在检索节点完成后记录
- `app/graph/nodes/safe_wrappers.py` - 在 `safe_vector_result()` 和 `safe_graph_result()` 中记录

**注入方式：**
```python
from app.services.retrieval_logger import RetrievalLogger

logger = RetrievalLogger.get_instance()
logger.log_retrieval(RetrievalLog(...))
```

## 4. 数据模型

### 4.1 RetrievalLog（检索日志）

```python
class RetrievalLog(BaseModel):
    log_id: str                          # 唯一ID (UUID)
    timestamp: datetime                  # 时间戳
    question: str                        # 用户问题
    agent_class: str                     # Agent类别 (cybersecurity, artificial_intelligence, general)
    route: str                           # 路由 (vector, graph, web, hybrid)
    
    # 检索指标
    filtered_docs_count: int             # 过滤后的文档数（应用 agent filter 后）
    retrieved_count: int                 # 实际检索到的文档数
    effective_hit_count: int             # 有效命中数（相关性分数 > 阈值）
    top_scores: list[float]              # Top 3 相关性分数
    
    # 性能指标
    retrieval_time_ms: float             # 检索耗时（毫秒）
    total_time_ms: float                 # 总耗时（毫秒）
    
    # 文档信息
    retrieved_sources: list[str]         # 检索到的文档列表（文件名）
    
    # 结果状态
    has_result: bool                     # 是否有结果
    error: Optional[str] = None          # 错误信息（如果失败）
```

### 4.2 AnalyticsOverview（总览统计）

```python
class AnalyticsOverview(BaseModel):
    total_queries: int                   # 总查询数
    success_rate: float                  # 成功率（0-100）
    avg_retrieval_time_ms: float         # 平均检索时间
    avg_total_time_ms: float             # 平均总耗时
    avg_retrieved_count: float           # 平均检索文档数
    avg_effective_hit_count: float       # 平均有效命中数
    
    # 分布统计
    agent_distribution: dict[str, int]   # Agent分布 {"cybersecurity": 50, "ai": 30, "general": 20}
    route_distribution: dict[str, int]   # 路由分布 {"vector": 60, "graph": 30, "web": 10}
    
    # 时间范围
    time_range_start: datetime           # 最早记录时间
    time_range_end: datetime             # 最新记录时间
```

### 4.3 AgentStats（Agent 性能统计）

```python
class AgentStats(BaseModel):
    agent_class: str                     # Agent类别
    query_count: int                     # 查询次数
    success_rate: float                  # 成功率（0-100）
    avg_retrieval_time_ms: float         # 平均检索时间
    avg_total_time_ms: float             # 平均总耗时
    avg_retrieved_count: float           # 平均检索文档数
    avg_effective_hit_count: float       # 平均有效命中数
    avg_top_score: float                 # 平均最高相关性分数
```

### 4.4 DocumentStats（文档热度统计）

```python
class DocumentStats(BaseModel):
    source: str                          # 文档名称
    retrieval_count: int                 # 被检索次数
    avg_score: float                     # 平均相关性分数
    agent_usage: dict[str, int]          # 各 Agent 的使用次数
```

## 5. API 设计

### 5.1 GET /api/analytics/overview

**描述：** 获取总览统计

**响应：**
```json
{
  "total_queries": 150,
  "success_rate": 94.67,
  "avg_retrieval_time_ms": 245.3,
  "avg_total_time_ms": 1823.5,
  "avg_retrieved_count": 5.2,
  "avg_effective_hit_count": 3.8,
  "agent_distribution": {
    "cybersecurity": 85,
    "artificial_intelligence": 45,
    "general": 20
  },
  "route_distribution": {
    "vector": 90,
    "graph": 45,
    "web": 15
  },
  "time_range_start": "2026-05-17T10:00:00Z",
  "time_range_end": "2026-05-17T14:30:00Z"
}
```

### 5.2 GET /api/analytics/agents

**描述：** 获取 Agent 性能分析

**响应：**
```json
[
  {
    "agent_class": "cybersecurity",
    "query_count": 85,
    "success_rate": 96.47,
    "avg_retrieval_time_ms": 230.5,
    "avg_total_time_ms": 1750.2,
    "avg_retrieved_count": 6.1,
    "avg_effective_hit_count": 4.5,
    "avg_top_score": 0.82
  },
  {
    "agent_class": "artificial_intelligence",
    "query_count": 45,
    "success_rate": 91.11,
    "avg_retrieval_time_ms": 180.3,
    "avg_total_time_ms": 1650.8,
    "avg_retrieved_count": 3.8,
    "avg_effective_hit_count": 2.9,
    "avg_top_score": 0.75
  }
]
```

### 5.3 GET /api/analytics/documents

**描述：** 获取文档热度分析

**参数：**
- `limit` (可选): 返回 Top N 文档，默认 20

**响应：**
```json
[
  {
    "source": "security_best_practices.md",
    "retrieval_count": 45,
    "avg_score": 0.85,
    "agent_usage": {
      "cybersecurity": 42,
      "general": 3
    }
  },
  {
    "source": "attack_analysis.md",
    "retrieval_count": 38,
    "avg_score": 0.79,
    "agent_usage": {
      "cybersecurity": 38
    }
  }
]
```

### 5.4 GET /api/analytics/export

**描述：** 导出检索日志

**参数：**
- `format`: `json` 或 `csv`

**响应：**
- JSON 格式：返回 JSON 数组
- CSV 格式：返回 CSV 文件（Content-Type: text/csv）

## 6. 实现细节

### 6.1 RetrievalLogger 服务实现

**核心方法：**

```python
class RetrievalLogger:
    _instance: Optional["RetrievalLogger"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._logs: deque[RetrievalLog] = deque(maxlen=1000)
        self._logs_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> "RetrievalLogger":
        """单例模式获取实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def log_retrieval(self, log: RetrievalLog) -> None:
        """记录检索日志（线程安全）"""
        with self._logs_lock:
            self._logs.append(log)
    
    def get_overview(self) -> AnalyticsOverview:
        """计算总览统计"""
        with self._logs_lock:
            logs = list(self._logs)
        
        if not logs:
            return self._empty_overview()
        
        # 计算各项统计指标
        total_queries = len(logs)
        success_count = sum(1 for log in logs if log.has_result)
        success_rate = (success_count / total_queries) * 100
        
        # ... 其他计算
        
        return AnalyticsOverview(...)
    
    def get_agent_stats(self) -> list[AgentStats]:
        """按 Agent 聚合统计"""
        with self._logs_lock:
            logs = list(self._logs)
        
        # 按 agent_class 分组
        agent_groups = {}
        for log in logs:
            if log.agent_class not in agent_groups:
                agent_groups[log.agent_class] = []
            agent_groups[log.agent_class].append(log)
        
        # 计算每个 Agent 的统计
        stats = []
        for agent_class, agent_logs in agent_groups.items():
            stats.append(self._calculate_agent_stats(agent_class, agent_logs))
        
        return sorted(stats, key=lambda x: x.query_count, reverse=True)
    
    def get_document_stats(self, limit: int = 20) -> list[DocumentStats]:
        """文档热度排行"""
        with self._logs_lock:
            logs = list(self._logs)
        
        # 统计每个文档的检索次数和分数
        doc_stats = {}
        for log in logs:
            for source in log.retrieved_sources:
                if source not in doc_stats:
                    doc_stats[source] = {
                        "count": 0,
                        "scores": [],
                        "agent_usage": {}
                    }
                doc_stats[source]["count"] += 1
                if log.top_scores:
                    doc_stats[source]["scores"].append(log.top_scores[0])
                
                agent = log.agent_class
                doc_stats[source]["agent_usage"][agent] = \
                    doc_stats[source]["agent_usage"].get(agent, 0) + 1
        
        # 转换为 DocumentStats 列表并排序
        stats = []
        for source, data in doc_stats.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0
            stats.append(DocumentStats(
                source=source,
                retrieval_count=data["count"],
                avg_score=avg_score,
                agent_usage=data["agent_usage"]
            ))
        
        return sorted(stats, key=lambda x: x.retrieval_count, reverse=True)[:limit]
    
    def export_logs(self, format: str = "json") -> str:
        """导出日志"""
        with self._logs_lock:
            logs = list(self._logs)
        
        if format == "json":
            return json.dumps([log.model_dump() for log in logs], default=str, indent=2)
        elif format == "csv":
            # 转换为 CSV 格式
            return self._to_csv(logs)
        else:
            raise ValueError(f"Unsupported format: {format}")
```

### 6.2 日志记录注入

**在 safe_wrappers.py 中注入：**

```python
# app/graph/nodes/safe_wrappers.py

from app.services.retrieval_logger import RetrievalLogger, RetrievalLog
import time
import uuid

def safe_vector_result(state: dict) -> dict:
    start_time = time.time()
    
    try:
        # 原有的检索逻辑
        result = run_vector_rag(
            question=state["question"],
            allowed_sources=state.get("allowed_sources"),
            retrieval_strategy=state.get("retrieval_strategy"),
            agent_class=state.get("agent_class"),
        )
        
        retrieval_time = (time.time() - start_time) * 1000
        
        # 记录日志
        try:
            logger = RetrievalLogger.get_instance()
            logger.log_retrieval(RetrievalLog(
                log_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                question=state["question"],
                agent_class=state.get("agent_class", "general"),
                route="vector",
                filtered_docs_count=len(state.get("allowed_sources", [])) if state.get("allowed_sources") else 0,
                retrieved_count=result.get("retrieved_count", 0),
                effective_hit_count=result.get("effective_hit_count", 0),
                top_scores=[c["metadata"].get("hybrid_score", 0.0) for c in result.get("citations", [])[:3]],
                retrieval_time_ms=retrieval_time,
                total_time_ms=retrieval_time,
                retrieved_sources=[c["source"] for c in result.get("citations", [])],
                has_result=result.get("retrieved_count", 0) > 0,
                error=None
            ))
        except Exception as e:
            # 日志记录失败不影响主流程
            logging.warning(f"Failed to log retrieval: {e}")
        
        return {"vector_result": result}
    
    except Exception as e:
        # 记录失败日志
        try:
            logger = RetrievalLogger.get_instance()
            logger.log_retrieval(RetrievalLog(
                log_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                question=state["question"],
                agent_class=state.get("agent_class", "general"),
                route="vector",
                filtered_docs_count=0,
                retrieved_count=0,
                effective_hit_count=0,
                top_scores=[],
                retrieval_time_ms=(time.time() - start_time) * 1000,
                total_time_ms=(time.time() - start_time) * 1000,
                retrieved_sources=[],
                has_result=False,
                error=str(e)
            ))
        except:
            pass
        
        # 原有的错误处理
        return {"vector_result": {...}}
```

**类似的逻辑应用到 `safe_graph_result()`**

### 6.3 前端实现

**AnalyticsPage 组件结构：**

```typescript
// frontend/src/pages/AnalyticsPage.tsx

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

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [agents, setAgents] = useState<AgentStats[]>([]);
  const [documents, setDocuments] = useState<DocumentStats[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [overviewRes, agentsRes, docsRes] = await Promise.all([
        fetch('/api/analytics/overview'),
        fetch('/api/analytics/agents'),
        fetch('/api/analytics/documents?limit=10')
      ]);
      
      setOverview(await overviewRes.json());
      setAgents(await agentsRes.json());
      setDocuments(await docsRes.json());
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(); // 初始加载
    const interval = setInterval(fetchData, 10000); // 每10秒刷新
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>加载中...</div>;
  if (!overview) return <div>暂无数据</div>;

  return (
    <div className="analytics-page">
      <header>
        <h1>📊 监控分析</h1>
        <button onClick={fetchData}>刷新</button>
      </header>

      {/* 统计卡片 */}
      <div className="stat-cards">
        <StatCard title="总查询数" value={overview.total_queries} />
        <StatCard title="成功率" value={`${overview.success_rate.toFixed(1)}%`} />
        <StatCard title="平均检索时间" value={`${overview.avg_retrieval_time_ms.toFixed(0)}ms`} />
        <StatCard title="平均文档数" value={overview.avg_retrieved_count.toFixed(1)} />
      </div>

      {/* 图表区域 */}
      <div className="charts-section">
        {/* Agent 分布饼图 */}
        <div className="chart-container">
          <h3>Agent 使用分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={Object.entries(overview.agent_distribution).map(([name, value]) => ({ name, value }))}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {Object.keys(overview.agent_distribution).map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Agent 性能对比柱状图 */}
        <div className="chart-container">
          <h3>Agent 性能对比</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={agents}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="agent_class" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="query_count" fill="#8884d8" name="查询次数" />
              <Bar dataKey="success_rate" fill="#82ca9d" name="成功率(%)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* 文档热度 Top 10 */}
        <div className="chart-container full-width">
          <h3>文档热度 Top 10</h3>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={documents} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="source" type="category" width={200} />
              <Tooltip />
              <Bar dataKey="retrieval_count" fill="#ffc658" name="检索次数" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 导出按钮 */}
      <div className="export-section">
        <button onClick={() => window.open('/api/analytics/export?format=json')}>
          导出 JSON
        </button>
        <button onClick={() => window.open('/api/analytics/export?format=csv')}>
          导出 CSV
        </button>
      </div>
    </div>
  );
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="stat-card">
      <div className="stat-title">{title}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
```

**样式文件（AnalyticsPage.css）：**

```css
.analytics-page {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.analytics-page header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-title {
  font-size: 0.875rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #333;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.chart-container {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.chart-container.full-width {
  grid-column: 1 / -1;
}

.export-section {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

button {
  padding: 0.5rem 1rem;
  background: #0088FE;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #0066CC;
}
```

### 6.4 路由和导航集成

**在 App.tsx 添加路由：**

```typescript
// frontend/src/App.tsx

import AnalyticsPage from './pages/AnalyticsPage';

// 在路由配置中添加
<Route path="/app/analytics" element={<AnalyticsPage />} />
```

**在 AdminPage.tsx 添加导航按钮：**

```typescript
// frontend/src/pages/AdminPage.tsx

<button onClick={() => navigate('/app/analytics')}>
  📊 查看监控分析
</button>
```

### 6.5 API 路由注册

**在 main.py 注册路由：**

```python
# app/api/main.py

from app.api.routes import analytics

app.include_router(analytics.router)
```

## 7. 错误处理和边界情况

### 7.1 错误处理策略

**1. 日志记录失败不影响主流程**

```python
try:
    logger.log_retrieval(log)
except Exception as e:
    logging.warning(f"Failed to log retrieval: {e}")
    # 不抛出异常，继续执行
```

**2. 内存溢出保护**

- 使用 `deque(maxlen=1000)` 自动限制大小
- 超过 1000 条自动丢弃最旧记录

**3. 并发安全**

- 所有读写操作使用 `threading.Lock()` 保护
- 统计计算时先复制数据，避免长时间持锁

**4. API 降级**

```python
def get_overview(self) -> AnalyticsOverview:
    with self._logs_lock:
        logs = list(self._logs)
    
    if not logs:
        # 返回空统计，不抛异常
        return AnalyticsOverview(
            total_queries=0,
            success_rate=0.0,
            avg_retrieval_time_ms=0.0,
            # ...
        )
```

**5. 前端错误处理**

```typescript
try {
  const data = await fetch('/api/analytics/overview');
  setOverview(data);
} catch (error) {
  console.error('Failed to fetch analytics:', error);
  // 显示错误提示，但不崩溃
  setError('加载失败，请稍后重试');
}
```

### 7.2 边界情况处理

**1. 系统刚启动，没有历史数据**
- API 返回空统计（total_queries=0）
- 前端显示"暂无数据"提示

**2. 某个 Agent 从未使用**
- 在 agent_distribution 中不出现
- 或显示为 0

**3. 检索失败的查询**
- 记录 `has_result=False` 和 `error` 信息
- 计入总查询数，影响成功率统计

**4. 文档名称过长**
- 前端使用 CSS `text-overflow: ellipsis` 截断
- Tooltip 显示完整名称

**5. 相关性分数缺失**
- 使用 0.0 作为默认值
- 在统计时过滤掉无效分数

**6. 并发大量请求**
- deque 线程安全，自动处理
- 统计计算时复制数据，不阻塞写入

**7. 导出大量数据**
- 限制最多导出 1000 条（内存限制）
- CSV 格式使用流式写入（如果需要）

## 8. 测试策略

### 8.1 单元测试

**RetrievalLogger 测试：**

```python
# tests/services/test_retrieval_logger.py

def test_log_retrieval():
    logger = RetrievalLogger.get_instance()
    log = RetrievalLog(...)
    logger.log_retrieval(log)
    
    overview = logger.get_overview()
    assert overview.total_queries == 1

def test_agent_stats():
    logger = RetrievalLogger.get_instance()
    # 记录多条不同 Agent 的日志
    # 验证统计结果

def test_document_stats():
    # 验证文档热度排序正确

def test_export_json():
    # 验证 JSON 导出格式

def test_export_csv():
    # 验证 CSV 导出格式

def test_thread_safety():
    # 多线程并发写入测试
```

### 8.2 集成测试

**API 测试：**

```python
# tests/api/test_analytics.py

def test_get_overview(client):
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data

def test_get_agents(client):
    response = client.get("/api/analytics/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_export_json(client):
    response = client.get("/api/analytics/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
```

### 8.3 前端测试

**组件测试：**

```typescript
// tests/pages/AnalyticsPage.test.tsx

test('renders analytics page', () => {
  render(<AnalyticsPage />);
  expect(screen.getByText('监控分析')).toBeInTheDocument();
});

test('fetches data on mount', async () => {
  // Mock API 响应
  // 验证数据加载
});

test('refreshes data every 10 seconds', () => {
  // 验证定时刷新
});
```

### 8.4 手动测试清单

- [ ] 启动系统，访问 `/app/analytics`，验证显示"暂无数据"
- [ ] 执行几次查询，刷新监控页面，验证数据更新
- [ ] 等待 10 秒，验证自动刷新
- [ ] 点击"刷新"按钮，验证手动刷新
- [ ] 测试不同 Agent 的查询，验证分布统计
- [ ] 导出 JSON 和 CSV，验证格式正确
- [ ] 在 AdminPage 点击按钮，验证跳转到监控页面
- [ ] 模拟检索失败，验证错误记录
- [ ] 长时间运行，验证内存不溢出（最多 1000 条）

## 9. 实现计划

### 9.1 开发阶段

**阶段 1：后端核心服务（第 1 天）**
- [ ] 创建 `app/services/retrieval_logger.py`
- [ ] 实现 RetrievalLog 数据模型
- [ ] 实现 RetrievalLogger 单例服务
- [ ] 实现统计聚合方法
- [ ] 编写单元测试

**阶段 2：API 端点（第 1 天）**
- [ ] 创建 `app/api/routes/analytics.py`
- [ ] 实现 4 个 API 端点
- [ ] 在 main.py 注册路由
- [ ] 编写 API 集成测试

**阶段 3：日志注入（第 2 天）**
- [ ] 在 `safe_wrappers.py` 注入日志记录
- [ ] 在 `safe_vector_result()` 添加日志
- [ ] 在 `safe_graph_result()` 添加日志
- [ ] 测试日志记录功能

**阶段 4：前端页面（第 2-3 天）**
- [ ] 安装 Recharts 依赖
- [ ] 创建 `AnalyticsPage.tsx`
- [ ] 实现统计卡片组件
- [ ] 实现图表组件
- [ ] 实现自动刷新
- [ ] 添加样式

**阶段 5：集成和测试（第 3 天）**
- [ ] 在 App.tsx 添加路由
- [ ] 在 AdminPage 添加导航按钮
- [ ] 端到端测试
- [ ] 性能测试
- [ ] Bug 修复

### 9.2 文件清单

**新建文件：**
- `app/services/retrieval_logger.py` - 检索日志服务
- `app/api/routes/analytics.py` - 分析 API
- `frontend/src/pages/AnalyticsPage.tsx` - 监控页面
- `frontend/src/pages/AnalyticsPage.css` - 样式文件
- `tests/services/test_retrieval_logger.py` - 单元测试
- `tests/api/test_analytics.py` - API 测试

**修改文件：**
- `app/graph/nodes/safe_wrappers.py` - 添加日志注入
- `app/api/main.py` - 注册路由
- `frontend/src/App.tsx` - 添加路由
- `frontend/src/pages/AdminPage.tsx` - 添加导航按钮
- `frontend/package.json` - 添加 Recharts 依赖

### 9.3 依赖安装

**前端依赖：**

```bash
cd frontend
npm install recharts
```

**后端依赖：**

无需额外依赖，使用 Python 标准库。

## 10. 未来扩展

### 10.1 短期扩展（1-2 周）

- **时间趋势分析**：按小时/天统计查询量
- **用户级别监控**：区分不同用户的使用情况
- **告警功能**：成功率低于阈值时发送通知
- **更多图表**：折线图显示时间趋势

### 10.2 长期扩展（1-2 月）

- **持久化存储**：使用 SQLite 或 PostgreSQL
- **高级分析**：查询意图分析、失败原因分类
- **A/B 测试**：对比不同检索策略的效果
- **实时推送**：使用 WebSocket 替代轮询

### 10.3 可选功能

- **慢查询分析**：识别响应时间超过阈值的查询
- **文档推荐**：基于热度推荐需要优化的文档
- **Agent 路由优化建议**：分析误分类的查询

## 11. 总结

本设计文档详细描述了 RAG 系统监控和分析功能的完整实现方案，包括：

- **独立的监控服务**：RetrievalLogger 负责日志记录和统计
- **完整的 API**：4 个端点提供全面的分析数据
- **可视化仪表板**：使用 Recharts 展示统计图表
- **实时更新**：10 秒自动刷新
- **数据导出**：支持 JSON 和 CSV 格式

**核心优势：**
- 职责清晰，易于维护
- 实现简单，开发周期短（2-3 天）
- 性能优秀，内存占用可控
- 扩展性好，便于后续迭代

**下一步：** 进入实现阶段，按照开发计划逐步完成各个模块。

