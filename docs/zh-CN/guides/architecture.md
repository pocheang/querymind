# 🏗️ QueryMind 系统架构

> 企业级智能问答引擎架构设计说明

---

## 📋 目录

- [架构概览](#架构概览)
- [技术栈](#技术栈)
- [系统分层](#系统分层)
- [核心模块](#核心模块)
- [数据流](#数据流)
- [部署架构](#部署架构)

---

## 架构概览

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         前端层                               │
│  React + Vite + TypeScript + TailwindCSS                    │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/WebSocket
┌────────────────▼────────────────────────────────────────────┐
│                       API 网关层                             │
│  FastAPI + Uvicorn + CORS + JWT 认证                        │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐
│业务逻辑│  │Agent   │  │检索    │
│服务层  │  │编排层  │  │服务层  │
└────────┘  └───┬────┘  └───┬────┘
                 │            │
    ┌────────────┼────────────┼────────────┐
    │            │            │            │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐  ┌───▼────┐
│关系型  │  │向量    │  │图数据库│  │外部LLM │
│数据库  │  │数据库  │  │Neo4j   │  │API     │
│SQLite  │  │ChromaDB│  │        │  │        │
└────────┘  └────────┘  └────────┘  └────────┘
```

### 设计原则

1. **模块化设计** - 高内聚、低耦合的模块划分
2. **可扩展性** - 支持水平扩展和垂直扩展
3. **可维护性** - 清晰的代码结构和文档
4. **安全性** - 多层安全防护机制
5. **性能优化** - 缓存、异步、并发处理

---

## 技术栈

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主要开发语言 |
| **FastAPI** | 0.104+ | Web 框架 |
| **Uvicorn** | 0.24+ | ASGI 服务器 |
| **SQLAlchemy** | 2.0+ | ORM 框架 |
| **Pydantic** | 2.0+ | 数据验证 |
| **LangChain** | 0.1+ | LLM 编排框架 |
| **LangGraph** | 0.0.26+ | Agent 工作流 |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18+ | UI 框架 |
| **TypeScript** | 5+ | 类型安全 |
| **Vite** | 5+ | 构建工具 |
| **TailwindCSS** | 3+ | CSS 框架 |
| **Axios** | 1.6+ | HTTP 客户端 |
| **Zustand** | 4+ | 状态管理 |

### 数据存储

| 技术 | 用途 |
|------|------|
| **SQLite / PostgreSQL** | 关系型数据（用户、文档元数据） |
| **ChromaDB** | 向量存储（文档嵌入） |
| **Neo4j** | 知识图谱（实体关系） |
| **Redis（可选）** | 缓存和会话存储 |

### AI/ML 技术

| 技术 | 用途 |
|------|------|
| **OpenAI API** | GPT-4, Embeddings |
| **Anthropic Claude** | Claude 3 系列 |
| **Ollama** | 本地 LLM 部署 |
| **Jieba** | 中文分词 |

---

## 系统分层

### 1. 表现层（Presentation Layer）

**职责**：用户交互界面

**组件**：
- React 组件（Chat, Documents, Graph, Admin）
- 路由管理（React Router）
- 状态管理（Zustand）
- UI 组件库（自定义 + TailwindCSS）

**关键特性**：
- 响应式设计
- 实时更新（SSE）
- 错误边界
- 加载状态

### 2. API 层（API Layer）

**职责**：接口暴露和请求处理

**组件**：
```python
app/api/
├── main.py              # FastAPI 应用入口
├── dependencies.py      # 依赖注入
└── endpoints/
    ├── auth.py         # 认证端点
    ├── documents.py    # 文档管理
    ├── chat.py         # 对话查询
    ├── graph.py        # 知识图谱
    └── admin.py        # 管理功能
```

**关键特性**：
- RESTful API 设计
- JWT 认证
- 请求验证（Pydantic）
- CORS 配置
- 速率限制

### 3. 业务逻辑层（Service Layer）

**职责**：核心业务逻辑实现

**组件**：
```python
app/services/
├── llm/
│   ├── openai_service.py
│   ├── anthropic_service.py
│   └── ollama_service.py
├── retrieval/
│   ├── vector_retrieval.py
│   ├── bm25_retrieval.py
│   └── hybrid_retrieval.py
├── agents/
│   ├── router_agent.py
│   ├── rag_agent.py
│   └── synthesis_agent.py
└── document/
    ├── processor.py
    └── chunker.py
```

**关键特性**：
- 服务解耦
- 依赖注入
- 错误处理
- 日志记录

### 4. 数据访问层（Data Access Layer）

**职责**：数据持久化和查询

**组件**：
```python
app/db/
├── database.py          # 数据库连接
├── models.py            # SQLAlchemy 模型
├── crud.py              # CRUD 操作
└── repositories/
    ├── user_repo.py
    └── document_repo.py
```

**关键特性**：
- Repository 模式
- 事务管理
- 连接池
- 查询优化

---

## 核心模块

### 1. 多智能体系统

#### 架构设计

```python
from langgraph.graph import StateGraph

# 定义状态
class QueryState(TypedDict):
    query: str
    route: str
    documents: List[Document]
    answer: str

# 构建工作流
workflow = StateGraph(QueryState)

# 添加节点
workflow.add_node("router", router_agent)
workflow.add_node("vector_rag", vector_rag_agent)
workflow.add_node("graph_rag", graph_rag_agent)
workflow.add_node("synthesis", synthesis_agent)

# 定义边
workflow.add_conditional_edges(
    "router",
    route_query,
    {
        "vector_rag": "vector_rag",
        "graph_rag": "graph_rag"
    }
)

workflow.add_edge("vector_rag", "synthesis")
workflow.add_edge("graph_rag", "synthesis")
```

#### Agent 类型

**1. Router Agent（路由代理）**
- **职责**: 分析查询意图，选择执行路径
- **输入**: 用户查询
- **输出**: 路由决策（vector_rag / graph_rag / web_search）

**2. Vector RAG Agent（向量检索代理）**
- **职责**: 执行向量检索和混合检索
- **流程**: 
  1. 查询向量化
  2. 向量检索 + BM25 检索
  3. 结果融合（RRF）
  4. 重排序

**3. Graph RAG Agent（图检索代理）**
- **职责**: 查询知识图谱
- **流程**:
  1. 实体识别
  2. 关系查询
  3. 多跳推理

**4. Synthesis Agent（合成代理）**
- **职责**: 生成最终答案
- **流程**:
  1. 上下文整合
  2. LLM 生成
  3. 安全检查
  4. 引用标注

### 2. 检索系统

#### 混合检索架构

```
用户查询
    │
    ├─→ 向量检索 ────┐
    │   (ChromaDB)   │
    │                │
    ├─→ BM25检索 ────┤→ RRF融合 ─→ 重排序 ─→ 结果
    │   (Inverted)   │  (权重)     (Cross-  
    │                │             Encoder)
    └─→ 图谱检索 ────┘
        (Neo4j)
```

#### 检索流程

```python
class HybridRetriever:
    def retrieve(self, query: str, top_k: int = 5):
        # 1. 并行检索
        vector_results = self.vector_retrieval(query, top_k * 2)
        bm25_results = self.bm25_retrieval(query, top_k * 2)
        
        # 2. 结果融合（RRF）
        fused_results = self.rrf_fusion(
            vector_results, 
            bm25_results,
            weights=[0.7, 0.3]
        )
        
        # 3. 重排序
        reranked = self.rerank(query, fused_results, top_k)
        
        return reranked
```

### 3. 文档处理管道

```
上传文档
    │
    ▼
文件验证 → 格式检测
    │
    ▼
内容提取
    ├─→ PDF: pdfplumber + Docling
    ├─→ DOCX: python-docx
    └─→ TXT: 直接读取
    │
    ▼
文本预处理
    ├─→ 清洗
    ├─→ 分词（Jieba）
    └─→ 同义词扩展
    │
    ▼
文档分块
    ├─→ Recursive splitting
    ├─→ Semantic splitting
    └─→ 重叠处理
    │
    ▼
向量化
    ├─→ OpenAI Embeddings
    └─→ 本地 Embeddings
    │
    ▼
存储
    ├─→ 向量 → ChromaDB
    ├─→ 元数据 → SQLite/PostgreSQL
    └─→ 实体 → Neo4j
```

### 4. 安全认证系统

#### JWT 认证流程

```
1. 用户登录
   ├─→ 验证用户名密码
   └─→ 生成 JWT Token

2. 请求验证
   ├─→ 提取 Token
   ├─→ 验证签名
   ├─→ 检查过期
   └─→ 提取用户信息

3. 权限检查
   ├─→ RBAC（基于角色）
   └─→ 资源级权限
```

#### 代码实现

```python
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        SECRET_KEY, 
        algorithm=ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username: str = payload.get("sub")
    return username
```

---

## 数据流

### 查询处理流程

```
1. 用户输入查询
   │
   ▼
2. API 接收请求
   ├─→ JWT 验证
   └─→ 请求验证
   │
   ▼
3. Router Agent 分析
   ├─→ 意图识别
   └─→ 路由决策
   │
   ▼
4. 检索执行
   ├─→ Vector RAG Agent
   │   ├─→ 向量检索
   │   ├─→ BM25 检索
   │   └─→ 混合融合
   │
   └─→ Graph RAG Agent
       ├─→ 实体识别
       └─→ 关系查询
   │
   ▼
5. Synthesis Agent
   ├─→ 上下文整合
   ├─→ LLM 生成答案
   └─→ 引用标注
   │
   ▼
6. 返回结果
   ├─→ 答案
   ├─→ 引用来源
   └─→ Agent 追踪
```

### 文档上传流程

```
1. 用户选择文件
   │
   ▼
2. 前端上传
   ├─→ 文件验证
   └─→ FormData 封装
   │
   ▼
3. API 接收
   ├─→ 大小检查
   ├─→ 格式验证
   └─→ 保存临时文件
   │
   ▼
4. 后台处理（异步）
   ├─→ 内容提取
   ├─→ 文本处理
   ├─→ 分块
   └─→ 向量化
   │
   ▼
5. 存储
   ├─→ 向量 → ChromaDB
   ├─→ 元数据 → DB
   └─→ 实体 → Neo4j
   │
   ▼
6. 更新状态
   └─→ 通知前端
```

---

## 部署架构

### 开发环境

```
┌─────────────────┐
│  开发机器        │
├─────────────────┤
│ Frontend:5173   │
│ Backend:8000    │
│ SQLite          │
│ ChromaDB        │
└─────────────────┘
```

### 生产环境

```
              ┌─────────────┐
              │   Nginx     │ (反向代理 + 负载均衡)
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼─────┐ ┌───▼──────┐ ┌──▼───────┐
   │Frontend 1│ │Frontend 2│ │Frontend 3│
   └──────────┘ └──────────┘ └──────────┘
                     │
              ┌──────▼──────┐
              │  API Gateway │
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼─────┐ ┌───▼──────┐ ┌──▼───────┐
   │Backend 1 │ │Backend 2 │ │Backend 3 │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────┼────────────────────┐
        │            │            │        │
   ┌────▼─────┐ ┌───▼──────┐ ┌──▼────┐ ┌─▼─────┐
   │PostgreSQL│ │ ChromaDB │ │Neo4j  │ │Redis  │
   └──────────┘ └──────────┘ └───────┘ └───────┘
```

### Docker 部署

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/querymind
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
      - chroma
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: querymind
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
  
  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  postgres_data:
  chroma_data:
  neo4j_data:
```

---

## 🔗 相关资源

- [开发者指南](./development.md) - 开发详细说明
- [配置指南](./configuration.md) - 系统配置
- [API 文档](./api-guide.md) - API 接口

---

<div align="center">

**了解更多架构细节**

[返回文档中心](../INDEX.md) · [GitHub 仓库](https://github.com/pocheang/querymind)

</div>
