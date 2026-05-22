# 监控和分析系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 RAG 系统添加监控和分析功能，追踪检索性能、Agent 使用情况和文档热度

**Architecture:** 独立的 RetrievalLogger 服务记录检索日志到内存（deque），Analytics API 提供统计聚合，前端使用 Recharts 展示可视化仪表板，10 秒轮询更新

**Tech Stack:** Python (FastAPI, Pydantic), TypeScript (React, Recharts), 内存存储 (collections.deque)

**参考文档:** `docs/superpowers/specs/2026-05-17-monitoring-analytics-design.md`

---

## 文件结构

**新建文件:**
- `app/services/retrieval_logger.py` - 检索日志服务（单例，线程安全，包含所有数据模型和统计方法）
- `app/api/routes/analytics.py` - 分析 API 路由（4 个端点）
- `frontend/src/pages/AnalyticsPage.tsx` - 监控仪表板页面
- `tests/services/test_retrieval_logger.py` - 日志服务单元测试
- `tests/api/test_analytics.py` - API 集成测试

**修改文件:**
- `app/graph/nodes/safe_wrappers.py` - 注入日志记录
- `app/api/main.py` - 注册 analytics 路由
- `frontend/src/App.tsx` - 添加路由
- `frontend/src/pages/AdminPage.tsx` - 添加导航按钮
- `frontend/package.json` - 添加 recharts 依赖

---

## Task 1: 创建完整的 RetrievalLogger 服务

**Files:**
- Create: `app/services/retrieval_logger.py`
- Create: `tests/services/test_retrieval_logger.py`

这个任务创建完整的日志服务，包括数据模型、单例服务、统计方法和导出功能。

- [ ] **Step 1: 创建完整的 retrieval_logger.py**

创建文件 `app/services/retrieval_logger.py`，包含以下内容：

1. 导入必要的库
2. 定义 4 个数据模型：RetrievalLog, AnalyticsOverview, AgentStats, DocumentStats
3. 实现 RetrievalLogger 类，包含：
   - 单例模式（get_instance）
   - log_retrieval 方法
   - get_overview 方法
   - get_agent_stats 方法
   - get_document_stats 方法
   - export_logs 方法（支持 JSON 和 CSV）

参考设计文档第 4 节（数据模型）和第 6.1 节（实现细节）。

- [ ] **Step 2: 创建单元测试文件**

创建文件 `tests/services/test_retrieval_logger.py`，包含测试：
- test_retrieval_log_creation
- test_retrieval_logger_singleton
- test_log_retrieval
- test_get_overview_empty
- test_get_overview_with_data
- test_get_agent_stats
- test_get_document_stats
- test_export_logs_json

- [ ] **Step 3: 运行测试验证**

```bash
conda activate rag-local
pytest tests/services/test_retrieval_logger.py -v
```

Expected: PASS (所有测试)

- [ ] **Step 4: 提交 RetrievalLogger 服务**

```bash
git add app/services/retrieval_logger.py tests/services/test_retrieval_logger.py
git commit -m "feat: implement RetrievalLogger service with statistics and export"
```

---

## Task 2: 创建 Analytics API 路由

**Files:**
- Create: `app/api/routes/analytics.py`
- Create: `tests/api/test_analytics.py`
- Modify: `app/api/main.py`

- [ ] **Step 1: 创建 analytics.py API 路由**

创建文件 `app/api/routes/analytics.py`，实现 4 个端点：

```python
from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.services.retrieval_logger import RetrievalLogger

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/overview")
async def get_analytics_overview():
    """获取总览统计"""
    logger = RetrievalLogger.get_instance()
    return logger.get_overview()

@router.get("/agents")
async def get_agent_stats():
    """获取 Agent 性能分析"""
    logger = RetrievalLogger.get_instance()
    return logger.get_agent_stats()

@router.get("/documents")
async def get_document_stats(limit: int = Query(default=20, ge=1, le=100)):
    """获取文档热度分析"""
    logger = RetrievalLogger.get_instance()
    return logger.get_document_stats(limit=limit)

@router.get("/export")
async def export_logs(format: str = Query(default="json", regex="^(json|csv)$")):
    """导出检索日志"""
    logger = RetrievalLogger.get_instance()
    data = logger.export_logs(format=format)
    
    if format == "csv":
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=retrieval_logs.csv"}
        )
    else:
        return Response(content=data, media_type="application/json")
```

- [ ] **Step 2: 在 main.py 注册路由**

在 `app/api/main.py` 中：

```python
# 在导入部分添加
from app.api.routes import analytics

# 在路由注册部分添加
app.include_router(analytics.router)
```

- [ ] **Step 3: 创建 API 集成测试**

创建文件 `tests/api/test_analytics.py`：

```python
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.services.retrieval_logger import RetrievalLogger, RetrievalLog
import uuid
from datetime import datetime, timezone

client = TestClient(app)

def test_get_overview():
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data
    assert "success_rate" in data

def test_get_agents():
    response = client.get("/api/analytics/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_documents():
    response = client.get("/api/analytics/documents?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_export_json():
    response = client.get("/api/analytics/export?format=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

def test_export_csv():
    response = client.get("/api/analytics/export?format=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
```

- [ ] **Step 4: 运行 API 测试**

```bash
pytest tests/api/test_analytics.py -v
```

Expected: PASS (所有测试)

- [ ] **Step 5: 手动测试 API 端点**

启动服务器并测试：

```bash
# 启动服务器（在另一个终端）
conda activate rag-local
python -m uvicorn app.api.main:app --reload

# 测试端点
curl http://localhost:8000/api/analytics/overview
curl http://localhost:8000/api/analytics/agents
curl http://localhost:8000/api/analytics/documents
```

- [ ] **Step 6: 提交 Analytics API**

```bash
git add app/api/routes/analytics.py app/api/main.py tests/api/test_analytics.py
git commit -m "feat: implement Analytics API with 4 endpoints"
```

---

## Task 3: 注入日志记录到检索节点

**Files:**
- Modify: `app/graph/nodes/safe_wrappers.py`

- [ ] **Step 1: 在 safe_vector_result 注入日志记录**

修改 `app/graph/nodes/safe_wrappers.py`，在 `safe_vector_result` 函数中添加日志记录：

```python
# 在文件顶部添加导入
import time
import uuid
from datetime import datetime, timezone
from app.services.retrieval_logger import RetrievalLogger, RetrievalLog

# 修改 safe_vector_result 函数
def safe_vector_result(
    question: str,
    allowed_sources: list[str] | None = None,
    retrieval_strategy: str | None = None,
    agent_class: str | None = None,
) -> dict[str, Any]:
    start_time = time.time()
    
    try:
        with traced_span("workflow.vector_retrieval", {"component": "vector_rag"}):
            with bulkhead("llm"):
                result = call_with_retry(
                    "workflow.vector_rag",
                    lambda: call_with_circuit_breaker(
                        "vector_rag.run",
                        lambda: run_vector_rag(
                            question,
                            allowed_sources=allowed_sources,
                            retrieval_strategy=retrieval_strategy,
                            agent_class=agent_class,
                        )
                        if retrieval_strategy
                        else run_vector_rag(question, allowed_sources=allowed_sources, agent_class=agent_class),
                    ),
                )
        
        retrieval_time = (time.time() - start_time) * 1000
        
        # 记录日志
        try:
            logger = RetrievalLogger.get_instance()
            citations = result.get("citations", [])
            top_scores = []
            for c in citations[:3]:
                metadata = c.get("metadata", {})
                score = metadata.get("hybrid_score") or metadata.get("rerank_score") or metadata.get("dense_score") or 0.0
                top_scores.append(float(score))
            
            logger.log_retrieval(RetrievalLog(
                log_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                question=question,
                agent_class=agent_class or "general",
                route="vector",
                filtered_docs_count=len(allowed_sources) if allowed_sources else 0,
                retrieved_count=result.get("retrieved_count", 0),
                effective_hit_count=result.get("effective_hit_count", 0),
                top_scores=top_scores,
                retrieval_time_ms=retrieval_time,
                total_time_ms=retrieval_time,
                retrieved_sources=[c.get("source", "") for c in citations],
                has_result=result.get("retrieved_count", 0) > 0,
                error=None
            ))
        except Exception as e:
            logger.warning(f"Failed to log retrieval: {e}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Vector RAG failed for question: {question}")
        
        # 记录失败日志
        try:
            retrieval_logger = RetrievalLogger.get_instance()
            retrieval_logger.log_retrieval(RetrievalLog(
                log_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                question=question,
                agent_class=agent_class or "general",
                route="vector",
                filtered_docs_count=len(allowed_sources) if allowed_sources else 0,
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
        
        return {"context": "", "citations": [], "retrieved_count": 0, "error": f"vector_error:{type(e).__name__}"}
```

- [ ] **Step 2: 在 safe_graph_result 注入日志记录**

类似地修改 `safe_graph_result` 函数，添加日志记录逻辑。

- [ ] **Step 3: 测试日志注入**

启动服务器并执行几次查询，然后检查日志是否被记录：

```bash
curl http://localhost:8000/api/analytics/overview
```

应该看到 total_queries > 0

- [ ] **Step 4: 提交日志注入**

```bash
git add app/graph/nodes/safe_wrappers.py
git commit -m "feat: inject retrieval logging into safe_vector_result and safe_graph_result"
```

---

## Task 4: 安装前端依赖并创建监控页面

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/pages/AnalyticsPage.tsx`

- [ ] **Step 1: 安装 Recharts 依赖**

```bash
cd frontend
npm install recharts
cd ..
```

- [ ] **Step 2: 验证依赖安装**

检查 `frontend/package.json` 中是否包含 recharts。

- [ ] **Step 3: 创建 AnalyticsPage.tsx**

创建文件 `frontend/src/pages/AnalyticsPage.tsx`，实现完整的监控页面，包括：
- 统计卡片（总查询数、成功率、平均时间、平均文档数）
- Agent 分布饼图
- Agent 性能柱状图
- 文档热度柱状图
- 10 秒自动刷新
- 导出按钮

参考设计文档第 6.3 节的完整代码。

- [ ] **Step 4: 提交前端依赖和页面**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: add Recharts dependency and create AnalyticsPage"
```

---

## Task 5: 集成前端路由和导航

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/AdminPage.tsx`

- [ ] **Step 1: 在 App.tsx 添加路由**

在 `frontend/src/App.tsx` 中添加：

```typescript
import AnalyticsPage from './pages/AnalyticsPage';

// 在路由配置中添加
<Route path="/app/analytics" element={<AnalyticsPage />} />
```

- [ ] **Step 2: 在 AdminPage 添加导航按钮**

在 `frontend/src/pages/AdminPage.tsx` 中添加导航按钮：

```typescript
import { useNavigate } from 'react-router-dom';

// 在组件中
const navigate = useNavigate();

// 在适当位置添加按钮
<button 
  onClick={() => navigate('/app/analytics')}
  style={{
    padding: '0.75rem 1.5rem',
    backgroundColor: '#0088FE',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem'
  }}
>
  📊 查看监控分析
</button>
```

- [ ] **Step 3: 测试前端集成**

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173/app/admin，点击"查看监控分析"按钮，验证跳转到监控页面。

- [ ] **Step 4: 提交前端集成**

```bash
git add frontend/src/App.tsx frontend/src/pages/AdminPage.tsx
git commit -m "feat: integrate AnalyticsPage into app routing and AdminPage navigation"
```

---

## Task 6: 端到端测试和文档

**Files:**
- None (testing only)

- [ ] **Step 1: 完整的端到端测试**

1. 启动后端服务器
2. 启动前端开发服务器
3. 执行几次不同的查询（不同 Agent）
4. 访问监控页面，验证：
   - 统计卡片显示正确数据
   - 图表正确渲染
   - 10 秒后自动刷新
   - 导出功能正常工作

- [ ] **Step 2: 验证所有测试通过**

```bash
pytest tests/services/test_retrieval_logger.py -v
pytest tests/api/test_analytics.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 3: 更新 internal_docs/OPTIMIZATION_SUMMARY.md**

在 `internal_docs/OPTIMIZATION_SUMMARY.md` 中添加"优化 5 - 监控和分析系统"的完成记录。

- [ ] **Step 4: 最终提交**

```bash
git add internal_docs/OPTIMIZATION_SUMMARY.md
git commit -m "docs: mark monitoring and analytics system as completed"
```

---

## 验收标准

完成后，系统应该具备以下功能：

1. ✅ 每次检索自动记录日志（问题、Agent、性能指标）
2. ✅ 内存存储最近 1000 条记录
3. ✅ 提供 4 个 API 端点（总览、Agent 分析、文档热度、导出）
4. ✅ 前端监控页面显示统计卡片和图表
5. ✅ 10 秒自动刷新数据
6. ✅ 支持 JSON 和 CSV 导出
7. ✅ AdminPage 有导航按钮跳转到监控页面
8. ✅ 所有单元测试和集成测试通过

---

## 故障排查

**问题：API 返回空数据**
- 检查是否执行过查询（日志需要有数据）
- 检查 RetrievalLogger 是否正确注入到 safe_wrappers.py

**问题：前端图表不显示**
- 检查 Recharts 是否正确安装
- 检查浏览器控制台是否有错误
- 检查 API 返回的数据格式是否正确

**问题：测试失败**
- 确保 conda 环境已激活
- 检查导入路径是否正确
- 检查测试数据是否符合预期

---

## 预估时间

- Task 1: 2-3 小时（核心服务）
- Task 2: 1-2 小时（API 路由）
- Task 3: 1 小时（日志注入）
- Task 4: 2-3 小时（前端页面）
- Task 5: 30 分钟（路由集成）
- Task 6: 1 小时（测试和文档）

**总计：7-10 小时（约 1-2 个工作日）**

