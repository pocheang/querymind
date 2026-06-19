# 项目结构 (Project Structure)

本文档详细介绍 Multi-Agent Local RAG 项目的目录结构和代码组织。

## 目录

- [快速参考](#快速参考)
- [总体结构](#总体结构)
- [后端结构 (app/)](#后端结构-app)
- [前端结构 (frontend/)](#前端结构-frontend)
- [配置文件](#配置文件)
- [测试结构](#测试结构)
- [脚本和工具](#脚本和工具)
- [文档结构](#文档结构)
- [数据目录](#数据目录)

---

## 快速参考

### 核心目录速查

| 目录 | 用途 | 关键文件 |
|------|------|---------|
| `app/api/` | API 层 | `main.py`, `routes/*.py` |
| `app/agents/` | 智能体 | `router_agent.py`, `vector_rag_agent.py` |
| `app/graph/` | 工作流 | `workflow.py`, `state.py` |
| `app/retrievers/` | 检索 | `vector_store.py`, `bm25_retriever.py` |
| `app/services/` | 服务层 | `auth.py`, `session_service.py` |
| `app/core/` | 核心 | `config.py`, `models.py`, `schemas.py` |
| `frontend/src/` | 前端 | `components/`, `services/` |
| `tests/` | 测试 | `test_*.py` |
| `scripts/` | 脚本 | `ingest.py`, `benchmark_pipeline.py` |
| `docs/` | 文档 | `guides/`, `project/` |

### 常用文件速查

**配置文件**:
- `.env` - 环境变量
- `pyproject.toml` - Python 项目配置
- `docker-compose.yml` - Docker 服务
- `frontend/package.json` - 前端依赖

**主要入口**:
- `app/api/main.py` - FastAPI 应用
- `app/graph/workflow.py` - LangGraph 工作流
- `frontend/src/main.tsx` - React 应用

**核心模块**:
- `app/core/config.py` - 配置管理
- `app/core/models.py` - 数据库模型
- `app/core/schemas.py` - Pydantic 模式

### 快速定位代码

**添加新的 API 端点**:
```
1. app/api/routes/ - 创建或修改路由文件
2. app/core/schemas.py - 定义请求/响应模式
3. app/services/ - 实现业务逻辑
4. app/api/main.py - 注册路由
```

**添加新的智能体**:
```
1. app/agents/ - 创建智能体文件
2. app/graph/nodes/ - 创建节点包装
3. app/graph/workflow.py - 添加到工作流
4. app/graph/state.py - 更新状态定义
```

**添加新的检索器**:
```
1. app/retrievers/ - 创建检索器文件
2. app/agents/vector_rag_agent.py - 集成到智能体
3. tests/ - 添加测试
```

**添加前端页面**:
```
1. frontend/src/components/ - 创建组件
2. frontend/src/services/ - 添加 API 调用
3. frontend/src/types/ - 定义类型
4. 配置路由
```

### 文件命名规范

| 类型 | Python | TypeScript | 示例 |
|------|--------|------------|------|
| **模块** | `snake_case.py` | `camelCase.ts` | `user_service.py` / `apiClient.ts` |
| **组件** | - | `PascalCase.tsx` | `UserProfile.tsx` |
| **测试** | `test_*.py` | `*.test.ts` | `test_auth.py` / `auth.test.ts` |
| **配置** | `snake_case.py` | `camelCase.ts` | `config.py` / `config.ts` |

### 依赖关系图

```
┌─────────────────┐
│   API Routes    │  ← HTTP 请求入口
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Graph Workflow │  ← 工作流编排
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│     Agents      │  ← 智能体逻辑
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Retrievers    │  ← 检索系统
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Data Stores   │  ← 数据持久化
└─────────────────┘
```

### 测试文件组织

```
tests/
├── unit/              # 单元测试（快速）
│   ├── test_auth.py
│   ├── test_retrievers.py
│   └── test_utils.py
│
├── integration/       # 集成测试（中速）
│   ├── test_api.py
│   ├── test_workflow.py
│   └── test_database.py
│
└── e2e/              # 端到端测试（慢速）
    ├── test_query_flow.py
    └── test_user_flow.py
```

### 数据目录说明

```
data/
├── chroma_db/        # ChromaDB 向量存储
├── docs/             # 待摄取文档
├── uploads/          # 用户上传文件
├── sessions/         # 会话数据
├── corpus/           # BM25 语料库
├── parent_chunks/    # 父块存储
├── app.db           # SQLite 数据库
└── logs/            # 日志文件
```

### 运行时文件

| 文件/目录 | 说明 | 是否提交 Git |
|----------|------|-------------|
| `.env` | 环境变量 | ❌ 不提交 |
| `data/` | 运行时数据 | ❌ 不提交 |
| `*.db` | 数据库文件 | ❌ 不提交 |
| `node_modules/` | 前端依赖 | ❌ 不提交 |
| `__pycache__/` | Python 缓存 | ❌ 不提交 |
| `.venv/` | 虚拟环境 | ❌ 不提交 |
| `*.log` | 日志文件 | ❌ 不提交 |

---

## 总体结构

```
multi_agent_rag_local_v4/
├── app/                          # 后端 Python 代码
├── frontend/                     # 前端 React 应用
├── tests/                        # 测试代码
├── scripts/                      # 运维和工具脚本
├── docs/                         # 公开文档
├── internal_docs/                # 内部文档（不提交到 Git）
├── data/                         # 运行时数据（大部分在 .gitignore）
├── configs/                      # 运行时配置文件
├── examples/                     # 使用示例
├── .env                          # 环境变量（不提交）
├── .env.example                  # 环境变量模板
├── pyproject.toml                # Python 项目配置
├── docker-compose.yml            # Docker 服务编排
├── README.md                     # 项目说明
├── CHANGELOG.md                  # 变更日志
├── CLAUDE.md                     # Claude AI 项目指令
└── LICENSE                       # 开源许可证
```

---

## 后端结构 (app/)

```
app/
├── __init__.py
├── __version__.py                # 版本号定义
│
├── api/                          # FastAPI 应用层
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── dependencies.py           # 依赖注入（数据库、认证等）
│   ├── middleware.py             # 中间件（CORS、日志等）
│   │
│   └── routes/                   # API 路由模块
│       ├── __init__.py
│       ├── auth.py               # 认证：注册、登录、登出
│       ├── query.py              # 查询：同步和流式查询
│       ├── sessions.py           # 会话管理
│       ├── documents.py          # 文档管理
│       ├── prompts.py            # 提示词管理
│       ├── admin_users.py        # 管理员：用户管理
│       ├── admin_ops.py          # 管理员：运维操作
│       ├── admin_settings.py     # 管理员：模型配置
│       ├── user_settings.py      # 用户：API 设置
│       ├── evaluation.py         # 性能评估
│       ├── agent_tracking.py     # 智能体追踪
│       ├── advanced_rag.py       # 高级 RAG 技术
│       ├── analytics.py          # 分析和监控
│       ├── health.py             # 健康检查
│       └── metrics.py            # 指标监控
│
├── agents/                       # 智能体实现
│   ├── __init__.py
│   ├── router_agent.py           # 路由智能体：分析查询意图
│   ├── vector_rag_agent.py       # 向量 RAG：混合检索
│   ├── graph_rag_agent.py        # 图 RAG：知识图谱查询
│   ├── graph_rag_agent_enhanced.py  # 增强版图 RAG
│   ├── web_research_agent.py     # 网络搜索智能体
│   └── synthesis_agent.py        # 合成智能体：生成最终答案
│
├── graph/                        # LangGraph 工作流编排
│   ├── __init__.py
│   ├── builder.py                # 图构建器
│   ├── state.py                  # 状态定义
│   ├── workflow.py               # 工作流定义
│   │
│   ├── nodes/                    # 图节点
│   │   ├── __init__.py
│   │   ├── router_node.py        # 路由节点
│   │   ├── vector_node.py        # 向量检索节点
│   │   ├── graph_node.py         # 图检索节点
│   │   ├── web_node.py           # 网络搜索节点
│   │   ├── synthesis_node.py     # 合成节点
│   │   └── safe_wrappers.py      # 安全包装器（超时、错误处理）
│   │
│   └── streaming/                # 流式处理
│       ├── __init__.py
│       ├── stream_processor.py   # 流式处理器
│       └── safe_wrappers.py      # 流式安全包装器
│
├── retrievers/                   # 检索系统
│   ├── __init__.py
│   ├── vector_store.py           # 向量存储（ChromaDB）
│   ├── bm25_retriever.py         # BM25 稀疏检索
│   ├── reranker.py               # 重排序器
│   ├── parent_retriever.py       # 父子块检索
│   │
│   └── hybrid/                   # 混合检索
│       ├── __init__.py
│       ├── fusion.py             # 倒数排名融合（RRF）
│       ├── adaptive_cache.py     # 自适应缓存
│       └── caching.py            # 查询缓存
│
├── services/                     # 业务服务层
│   ├── __init__.py
│   ├── auth.py                   # 认证服务
│   ├── user_service.py           # 用户管理服务
│   ├── session_service.py        # 会话管理服务
│   ├── document_service.py       # 文档管理服务
│   ├── prompt_service.py         # 提示词管理服务
│   ├── memory_service.py         # 记忆管理服务
│   ├── model_config_store.py     # 模型配置存储
│   ├── runtime_governance.py     # 运行时治理
│   ├── resilience.py             # 韧性工具（熔断器、重试）
│   ├── agent_document_filter.py  # 智能体文档过滤
│   ├── outbound_redaction.py     # 出站数据脱敏
│   └── role_based_rate_limiter.py # 基于角色的限流
│
├── ingestion/                    # 文档摄取
│   ├── __init__.py
│   ├── loaders.py                # 文档加载器
│   ├── chunking.py               # 分块策略
│   ├── indexer.py                # 索引器
│   │
│   └── utils/                    # 摄取工具
│       ├── __init__.py
│       ├── ocr_utils.py          # OCR 工具
│       ├── vision_utils.py       # 视觉工具（图像描述）
│       ├── chart_extractor.py    # 图表提取
│       └── pdf_utils.py          # PDF 工具
│
├── tools/                        # 工具集成
│   ├── __init__.py
│   ├── graph_tools.py            # 图数据库工具
│   ├── graph_tools_enhanced.py   # 增强版图工具
│   └── web_tools.py              # 网络搜索工具
│
├── core/                         # 核心模块
│   ├── __init__.py
│   ├── config.py                 # 配置管理
│   ├── models.py                 # 数据库模型
│   ├── schemas.py                # Pydantic 模式定义
│   ├── exceptions.py             # 自定义异常
│   ├── logging.py                # 日志配置
│   └── utils.py                  # 通用工具
│
└── evaluation/                   # 评估系统
    ├── __init__.py
    ├── service.py                # 评估服务
    ├── metrics.py                # 评估指标
    └── baseline_systems.py       # 基线系统
```

### 关键模块说明

#### 1. API 层 (app/api/)

**职责**：
- 处理 HTTP 请求和响应
- 路由定义和参数验证
- 认证和授权
- 中间件处理

**主要文件**：
- `main.py`: FastAPI 应用初始化，注册路由
- `dependencies.py`: 依赖注入（数据库连接、当前用户等）
- `middleware.py`: CORS、日志、错误处理中间件
- `routes/`: 各功能模块的路由定义

#### 2. 智能体层 (app/agents/)

**职责**：
- 实现各种专业智能体
- 查询分析和意图理解
- 检索策略选择
- 答案生成

**智能体类型**：
- **Router Agent**: 分析查询，决定路由策略
- **Vector RAG Agent**: 执行混合检索（向量 + BM25）
- **Graph RAG Agent**: 查询知识图谱获取实体关系
- **Web Research Agent**: 在本地知识不足时进行网络搜索
- **Synthesis Agent**: 综合所有信息生成最终答案

#### 3. 工作流编排 (app/graph/)

**职责**：
- LangGraph 工作流定义
- 状态管理
- 节点间数据传递
- 流式输出处理

**核心概念**：
- **State**: 工作流状态，包含查询、上下文、中间结果等
- **Nodes**: 各个处理节点，对应不同智能体
- **Edges**: 节点间的转换逻辑（条件路由）
- **Safe Wrappers**: 超时控制、错误恢复

#### 4. 检索系统 (app/retrievers/)

**职责**：
- 向量检索（语义搜索）
- BM25 检索（关键词匹配）
- 混合检索和融合
- 重排序

**技术栈**：
- **ChromaDB**: 向量存储和检索
- **rank-bm25**: BM25 算法实现
- **sentence-transformers**: 重排序模型
- **RRF**: 倒数排名融合算法

#### 5. 业务服务 (app/services/)

**职责**：
- 业务逻辑封装
- 数据持久化
- 缓存管理
- 安全和治理

**关键服务**：
- `auth.py`: JWT 令牌、密码哈希、权限验证
- `session_service.py`: 会话生命周期、历史记录
- `document_service.py`: 文档元数据管理
- `runtime_governance.py`: 金丝雀路由、回滚、基准测试

#### 6. 文档摄取 (app/ingestion/)

**职责**：
- 文档加载（PDF、TXT、DOCX、图片等）
- 文本分块
- OCR 处理
- 向量化和索引

**处理流程**：
```
文档 → 加载器 → OCR（如需要）→ 分块 → 嵌入 → 索引
```

---

## 前端结构 (frontend/)

```
frontend/
├── public/                       # 静态资源
│   ├── vite.svg
│   └── ...
│
├── src/                          # 源代码
│   ├── main.tsx                  # 应用入口
│   ├── App.tsx                   # 根组件
│   ├── index.css                 # 全局样式
│   │
│   ├── components/               # React 组件
│   │   ├── Auth/                 # 认证组件
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   └── AuthContext.tsx
│   │   │
│   │   ├── Chat/                 # 聊天组件
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── StreamingMessage.tsx
│   │   │
│   │   ├── Session/              # 会话管理
│   │   │   ├── SessionList.tsx
│   │   │   ├── SessionDetail.tsx
│   │   │   └── SessionHistory.tsx
│   │   │
│   │   ├── Document/             # 文档管理
│   │   │   ├── DocumentList.tsx
│   │   │   ├── DocumentUpload.tsx
│   │   │   └── DocumentViewer.tsx
│   │   │
│   │   ├── Admin/                # 管理界面
│   │   │   ├── UserManagement.tsx
│   │   │   ├── SystemSettings.tsx
│   │   │   └── OperationsPanel.tsx
│   │   │
│   │   ├── Settings/             # 设置界面
│   │   │   ├── APISettings.tsx
│   │   │   ├── ModelSettings.tsx
│   │   │   └── PreferencesSettings.tsx
│   │   │
│   │   ├── Analytics/            # 分析面板
│   │   │   ├── AnalyticsDashboard.tsx
│   │   │   ├── RetrievalStats.tsx
│   │   │   └── PerformanceChart.tsx
│   │   │
│   │   └── Common/               # 通用组件
│   │       ├── Header.tsx
│   │       ├── Sidebar.tsx
│   │       ├── Modal.tsx
│   │       ├── Button.tsx
│   │       ├── Loading.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── services/                 # API 服务
│   │   ├── api.ts                # API 客户端配置
│   │   ├── authService.ts        # 认证 API
│   │   ├── queryService.ts       # 查询 API
│   │   ├── sessionService.ts     # 会话 API
│   │   ├── documentService.ts    # 文档 API
│   │   └── adminService.ts       # 管理 API
│   │
│   ├── hooks/                    # React Hooks
│   │   ├── useAuth.ts            # 认证 Hook
│   │   ├── useQuery.ts           # 查询 Hook
│   │   ├── useSession.ts         # 会话 Hook
│   │   └── useWebSocket.ts       # WebSocket Hook
│   │
│   ├── utils/                    # 工具函数
│   │   ├── formatting.ts         # 格式化工具
│   │   ├── validation.ts         # 验证工具
│   │   └── helpers.ts            # 辅助函数
│   │
│   ├── types/                    # TypeScript 类型定义
│   │   ├── auth.ts
│   │   ├── query.ts
│   │   ├── session.ts
│   │   └── document.ts
│   │
│   └── styles/                   # 样式文件
│       ├── variables.css         # CSS 变量
│       ├── components.css        # 组件样式
│       └── utilities.css         # 工具类
│
├── index.html                    # HTML 入口
├── vite.config.ts                # Vite 配置
├── tsconfig.json                 # TypeScript 配置
├── package.json                  # npm 依赖
└── README.md                     # 前端说明
```

### 前端技术栈

- **框架**: React 18+
- **构建工具**: Vite
- **语言**: TypeScript
- **样式**: CSS Modules + CSS Variables
- **路由**: React Router
- **状态管理**: React Context + Hooks
- **HTTP 客户端**: Axios
- **实时通信**: Server-Sent Events (SSE)

---

## 配置文件

### pyproject.toml

Python 项目配置，包含：
- 项目元数据（名称、版本、描述）
- 依赖管理（核心依赖和可选依赖）
- 工具配置（pytest、coverage、ruff）

```toml
[project]
name = "multi-agent-local-rag"
version = "0.4.4"
dependencies = [...]

[project.optional-dependencies]
ocr = [...]
reranker = [...]
full = [...]

[tool.pytest.ini_options]
[tool.ruff]
```

### docker-compose.yml

Docker 服务编排：
- Neo4j 图数据库
- Redis 缓存（可选）

```yaml
services:
  neo4j:
    image: neo4j:5.13
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
```

### .env.example

环境变量模板，包含：
- 模型配置
- 数据库连接
- 安全密钥
- 功能开关

---

## 测试结构

```
tests/
├── conftest.py                   # Pytest 配置和 fixtures
│
├── unit/                         # 单元测试
│   ├── test_auth.py
│   ├── test_retrievers.py
│   ├── test_chunking.py
│   └── test_utils.py
│
├── integration/                  # 集成测试
│   ├── test_query_flow.py
│   ├── test_document_ingestion.py
│   └── test_session_management.py
│
├── workflow/                     # 工作流测试
│   ├── test_routing_logic.py
│   ├── test_streaming.py
│   └── test_multi_agent.py
│
└── fixtures/                     # 测试数据
    ├── sample_docs/
    ├── test_queries.json
    └── expected_outputs.json
```

### 测试类型

- **单元测试**: 测试单个函数或类
- **集成测试**: 测试多个组件协作
- **工作流测试**: 测试完整的查询流程
- **性能测试**: 基准测试和负载测试

---

## 脚本和工具

```
scripts/
├── ingest.py                     # 文档摄取脚本
├── benchmark_pipeline.py         # 检索性能基准测试
├── load_test_query.py            # 查询负载测试
├── eval_retrieval.py             # RAG 评估（精确率/召回率）
├── chaos_probe.py                # 混沌工程测试
├── ci_quality_gate.py            # CI 质量门控
├── backup_database.py            # 数据库备份
├── bump_version.py               # 版本号管理
├── query_analytics.py            # 查询分析
│
└── dev/                          # 开发辅助脚本
    ├── smoke_test_auth.py
    ├── smoke_test_query.py
    └── README.md
```

### 脚本分类

#### 1. 摄取和索引
- `ingest.py`: 批量摄取文档到向量库

#### 2. 测试和评估
- `eval_retrieval.py`: 评估检索质量
- `benchmark_pipeline.py`: 性能基准测试
- `load_test_query.py`: 并发负载测试
- `chaos_probe.py`: 故障注入测试

#### 3. 运维工具
- `backup_database.py`: 备份数据
- `query_analytics.py`: 分析查询日志
- `ci_quality_gate.py`: CI/CD 质量检查

#### 4. 开发工具 (dev/)
- 手动烟雾测试脚本
- 快速验证工具

---

## 文档结构

```
docs/
├── README.md                     # 文档中心
├── DEVELOPER_GUIDE.md            # 开发者指南（本文档的索引）
│
├── guides/                       # 指南文档
│   ├── startup-guide.md          # 快速启动
│   ├── quick-reference.md        # 快速参考
│   ├── API_SETTINGS_GUIDE.md     # API 设置指南
│   ├── PERFORMANCE_OPTIMIZATION.md
│   ├── PDF_TESTING_GUIDE.md
│   │
│   └── development/              # 开发指南
│       ├── SETUP_GUIDE.md        # 环境搭建
│       ├── PROJECT_STRUCTURE.md  # 项目结构（本文档）
│       ├── ARCHITECTURE.md       # 系统架构
│       └── ...
│
├── design/                       # 设计文档
│   ├── INDEX.md
│   └── 2026-xx-xx-feature-design.md
│
├── features/                     # 功能文档
│   ├── rag/                      # RAG 功能
│   ├── agents/                   # 智能体
│   ├── pdf/                      # PDF 处理
│   └── ocr/                      # OCR 功能
│
├── archive/                      # 归档文档
│   ├── completion-reports/       # 完成报告
│   ├── plans/                    # 历史计划
│   ├── fixes/                    # 修复记录
│   ├── refactoring/              # 重构报告
│   └── investigations/           # 调查报告
│
├── project/                      # 项目管理
│   ├── SECURITY.md               # 安全指南
│   ├── CODE_CHANGE_POLICY.md     # 代码变更政策
│   └── production_readiness_checklist.md
│
└── templates/                    # 文档模板
    ├── FEATURE_DESIGN_TEMPLATE.md
    ├── VERSION_PLAN_TEMPLATE.md
    └── ...
```

---

## 数据目录

```
data/
├── chroma_db/                    # ChromaDB 向量存储
│   └── [自动生成的数据文件]
│
├── docs/                         # 待摄取的文档
│   ├── sample.pdf
│   ├── knowledge_base.txt
│   └── ...
│
├── uploads/                      # 用户上传的文档
│   └── [按用户 ID 组织]
│
├── sessions/                     # 会话数据
│   └── [按会话 ID 组织]
│
├── corpus/                       # BM25 语料库
│   └── corpus_store.json
│
├── parent_chunks/                # 父块存储
│   └── parent_store.json
│
├── app.db                        # SQLite 应用数据库
│
└── logs/                         # 日志文件
    ├── app.log
    ├── error.log
    └── audit.log
```

### 数据持久化

- **ChromaDB**: 向量嵌入和元数据
- **Neo4j**: 知识图谱（实体和关系）
- **SQLite**: 用户、会话、文档元数据
- **文件系统**: 原始文档、日志、缓存

---

## 配置文件

```
configs/
├── profiles/                     # 检索配置文件
│   ├── baseline.json
│   ├── advanced.json
│   └── safe.json
│
└── prompts/                      # 提示词模板
    ├── router.txt
    ├── synthesis.txt
    └── ...
```

---

## 代码导航建议

### 新手入门路径

1. **理解入口点**
   - 后端: `app/api/main.py`
   - 前端: `frontend/src/main.tsx`

2. **追踪查询流程**
   ```
   routes/query.py
   → graph/workflow.py
   → graph/nodes/router_node.py
   → graph/nodes/vector_node.py
   → agents/vector_rag_agent.py
   → retrievers/vector_store.py
   ```

3. **理解数据模型**
   - `app/core/models.py`: 数据库模型
   - `app/core/schemas.py`: API 模式

4. **学习配置系统**
   - `app/core/config.py`: 配置加载
   - `.env.example`: 环境变量

### 常见开发任务

#### 添加新的 API 端点
```
1. 在 app/api/routes/ 中创建或修改路由文件
2. 在 app/core/schemas.py 中定义请求/响应模式
3. 在 app/services/ 中实现业务逻辑
4. 在 tests/ 中添加测试
5. 在 app/api/main.py 中注册路由
```

#### 添加新的智能体
```
1. 在 app/agents/ 中创建智能体文件
2. 在 app/graph/nodes/ 中创建对应节点
3. 在 app/graph/workflow.py 中集成节点
4. 更新 app/graph/state.py 的状态定义
5. 添加测试
```

#### 添加新的前端页面
```
1. 在 frontend/src/components/ 中创建组件
2. 在 frontend/src/services/ 中添加 API 调用
3. 在 frontend/src/types/ 中定义类型
4. 配置路由
5. 添加样式
```

---

## 代码约定

### 命名规范

- **Python**:
  - 文件: `snake_case.py`
  - 类: `PascalCase`
  - 函数/变量: `snake_case`
  - 常量: `UPPER_SNAKE_CASE`

- **TypeScript**:
  - 文件: `PascalCase.tsx` (组件) 或 `camelCase.ts` (工具)
  - 组件: `PascalCase`
  - 函数/变量: `camelCase`
  - 类型/接口: `PascalCase`

### 目录组织原则

1. **按功能分组**: 相关代码放在同一目录
2. **清晰的层次**: API → Service → Data Access
3. **可测试性**: 每个模块都应易于测试
4. **文档化**: 每个目录应有 `__init__.py` 或 README

---

## 依赖关系

```
┌─────────────────┐
│   API Routes    │  ← HTTP 请求入口
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Graph Workflow │  ← 工作流编排
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│     Agents      │  ← 智能体逻辑
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Retrievers    │  ← 检索系统
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Data Stores   │  ← 数据持久化
└─────────────────┘
```

### 依赖规则

- **向下依赖**: 上层可以调用下层，反之不可
- **水平隔离**: 同层模块避免相互依赖
- **接口抽象**: 通过接口降低耦合

---

## 下一步

了解项目结构后，建议继续阅读：

1. **[系统架构](./ARCHITECTURE.md)** - 深入理解设计原理
2. **[开发流程](./DEVELOPMENT_WORKFLOW.md)** - 学习开发规范
3. **[API 开发](./API_DEVELOPMENT.md)** - 开始编写代码

---

**更新日期**: 2026-06-19  
**文档版本**: 1.0
