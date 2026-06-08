# 多智能体RAG系统项目分析报告

> 生成时间：2026-06-07  
> 分析范围：完整代码库、配置、文档、测试

---

## 📊 项目概况

**项目名称**: Multi-Agent Local RAG  
**当前版本**: v0.4.3 (2026-06-02)  
**许可证**: MIT  
**开发环境**: `rag-local` conda环境  
**定位**: 企业级本地优先RAG平台，支持多智能体编排、混合检索、图增强和管理治理

---

## 📈 基本统计

### 代码规模
- **后端代码**: 209个Python文件 (app目录)
- **前端代码**: 120个TypeScript/TSX文件 (frontend/src目录)
- **测试文件**: 89个测试模块 (tests目录)
- **运维脚本**: 42个Python脚本 (scripts目录)

### 技术要求
- **Python**: 3.11+
- **Node.js**: 18+
- **数据库**: Neo4j 5.26, ChromaDB 0.5.5+
- **缓存**: Redis 5.0+ (可选)

### 代码行数估算
- 后端约 **15,000+ 行** Python代码
- 前端约 **8,000+ 行** TypeScript代码
- 测试约 **6,000+ 行** 测试代码
- 总计约 **30,000+ 行** 有效代码

---

## 🎯 目标用例

1. **企业内部知识助手** - 安全的文档访问控制
2. **私有文档问答** - PDF、图像、文本语料库，支持OCR
3. **RAG评估实验** - 检索策略实验和基准测试工具
4. **可控AI运维** - 可审计性、回滚和金丝雀部署
5. **混合模型部署** - Ollama本地、OpenAI、Anthropic
6. **多跳推理** - 知识图谱集成处理复杂查询
7. **会话式AI** - 带记忆和上下文管理的会话系统

---

## 🏆 核心特性

### ✨ 多智能体编排
- 基于LangGraph的5个专门智能体
- 智能路由和条件执行
- 向量和图检索并发执行
- 流式输出支持

### 🔍 混合检索
- 向量搜索 (ChromaDB)
- BM25稀疏检索
- Reciprocal Rank Fusion融合
- 跨编码器重排序 (BGE-reranker-v2-m3)
- 父子分块策略

### 🇨🇳 中文NLP优化
- Jieba分词
- 同义词扩展
- 查询预处理
- 自动语言检测 (20%中文阈值)

### 🛡️ 安全与治理
- RBAC权限控制
- JWT令牌认证 (24小时TTL)
- 会话隔离
- 审计日志
- 安全加固 (HTTPS-only cookies, CSRF防护)

### 📊 可观测性
- 实时智能体执行追踪
- SSE流式可视化
- 检索分析仪表板
- 性能基准测试
- RAG评估指标 (精确率/召回率/F1)

---

## 🏗️ 技术架构

### 后端技术栈

#### 核心框架
- **Web框架**: FastAPI 0.115.0+
- **ASGI服务器**: Uvicorn 0.30.0+
- **数据验证**: Pydantic 2.8.0+

#### AI/ML框架
- **编排引擎**: LangGraph 0.2.0+ (多智能体工作流)
- **LLM框架**: LangChain 0.3.0+
- **模型集成**: 
  - `langchain-openai` 0.2.0+ (OpenAI/兼容API)
  - `langchain-anthropic` 0.3.0+ (Claude系列)
  - `langchain-ollama` 0.2.0+ (本地模型)

#### 存储与检索
- **向量数据库**: ChromaDB 0.5.5+ (`langchain-chroma`)
- **图数据库**: Neo4j 5.26 (`neo4j` driver 5.24.0+)
- **缓存系统**: Redis 5.0+ (可选)
- **BM25检索**: rank-bm25 0.2.2+

#### 文档处理
- **PDF解析**: pypdf 5.0.0+
- **图像处理**: Pillow 10.0.0+
- **OCR引擎**: 
  - Tesseract (pytesseract 0.3.10+, 可选)
  - PaddleOCR 2.7.0+ (可选，中文增强)
- **高级文档**: Docling 2.93.0+ (可选，结构化提取)

#### 重排序与NLP
- **跨编码器**: sentence-transformers 3.0.1+ (可选)
- **中文分词**: jieba 0.42.1+
- **文本分割**: langchain-text-splitters 0.3.0+
- **相似度**: scikit-learn 1.3.0+

#### 安全与认证
- **OAuth/JWT**: authlib 1.3.0+, itsdangerous 2.1.0+
- **HTTP客户端**: httpx 0.27.0+ (异步支持)

#### 工具与搜索
- **网络搜索**: ddgs 8.0.0+ (DuckDuckGo Search)

#### 工具与序列化
- **JSON**: orjson 3.10.0+ (高性能)
- **重试机制**: tenacity 9.0.0+
- **文件上传**: python-multipart 0.0.9+
- **环境配置**: python-dotenv 1.0.1+

---

### 前端技术栈

#### 核心框架
- **UI框架**: React 18.3.1
- **构建工具**: Vite 6.4.2
- **编译器**: @vitejs/plugin-react-swc 3.11.0

#### 类型系统
- **TypeScript**: 5.9.3
- **React类型**: @types/react 18.3.28, @types/react-dom 18.3.7

#### 路由与状态
- **路由**: react-router-dom 6.30.3

#### UI组件与可视化
- **流程图**: ReactFlow 11.11.4
- **图表**: Recharts 3.8.1
- **Markdown**: react-markdown 9.0.1, remark-gfm 4.0.0
- **样式工具**: clsx 2.1.1

#### 国际化
- **i18n核心**: i18next 26.3.1
- **React集成**: react-i18next 17.0.8

#### 性能优化
- **CSS优化**: 
  - critical 7.2.1 (关键CSS提取)
  - @fullhuman/postcss-purgecss 8.0.0
  - purgecss 8.0.0
- **打包优化**: esbuild 0.28.0

#### 测试工具
- **E2E测试**: @playwright/test 1.59.1, puppeteer 23.11.1

---

### 基础设施

#### 容器化
```yaml
服务列表 (docker-compose.yml):
├── neo4j:5.26        # 图数据库 (端口: 7474, 7687)
│   ├── APOC插件支持
│   └── 持久化卷: data, logs, plugins, conf
└── n8n               # 工作流自动化 (端口: 5678)
    └── 持久化卷: ~/.n8n
```

#### CI/CD
- **质量门禁**: GitHub Actions (`.github/workflows/quality-gate.yml`)
- **自动化检查**: 
  - 后端测试 (pytest)
  - RAG评估 (精确率/召回率/F1)
  - 性能基准测试
  - 代码质量检查 (ruff)

---

### 模型后端支持

#### OpenAI / 兼容API
```bash
MODEL_BACKEND=openai
OPENAI_API_KEY=<your-key>
OPENAI_CHAT_MODEL=gpt-5.4-codex
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_REASONING_MODEL=gpt-5.4-codex
OPENAI_VISION_MODEL=gpt-4.1-mini
```

#### Anthropic
```bash
MODEL_BACKEND=anthropic
ANTHROPIC_API_KEY=<your-key>
ANTHROPIC_CHAT_MODEL=claude-sonnet-4-6
ANTHROPIC_REASONING_MODEL=claude-sonnet-4-6
# 注意：Anthropic使用OpenAI的嵌入模型
```

#### Ollama (本地)
```bash
MODEL_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_VISION_MODEL=llava:7b
```

#### 本地模式 (无API密钥)
```bash
MODEL_BACKEND=local
# 适用于开发/测试，不需要外部API
```

---

## 📁 项目结构

### 顶层目录树

```
multi_agent_rag_local_v4/
├── app/                    # 后端应用代码 (209个.py文件)
├── frontend/               # 前端React应用
├── tests/                  # 测试套件 (89个测试文件)
├── scripts/                # 运维脚本 (42个.py文件)
├── docs/                   # 项目文档
├── configs/                # 运行时配置文件
├── data/                   # 本地数据存储 (gitignored)
├── examples/               # 使用示例
├── internal_docs/          # 内部文档 (gitignored)
├── .github/                # GitHub Actions CI/CD
├── .claude/                # Claude Code配置
├── docker-compose.yml      # 容器编排
├── pyproject.toml          # Python项目配置
├── CLAUDE.md               # 项目指令
├── README.md               # 项目说明
└── CHANGELOG.md            # 变更日志
```

---

### 后端目录结构 (`app/`)

```python
app/
├── agents/                 # 多智能体实现
│   ├── router.py           # 路由智能体 - 查询意图分析
│   ├── vector_rag.py       # 向量RAG智能体 - 混合检索
│   ├── graph_rag.py        # 图RAG智能体 - Neo4j查询
│   ├── web_research.py     # 网络研究智能体 - 在线搜索
│   └── synthesis.py        # 合成智能体 - 答案生成
│
├── api/                    # FastAPI应用
│   ├── main.py             # 应用入口点
│   ├── dependencies.py     # 依赖注入
│   ├── middleware.py       # 中间件配置
│   └── routes/             # 路由模块 (10+个路由文件)
│       ├── auth.py         # 认证: 注册/登录/登出
│       ├── query.py        # 查询: 同步/流式端点
│       ├── sessions.py     # 会话管理
│       ├── documents.py    # 文档CRUD
│       ├── prompts.py      # 提示词管理
│       ├── admin_users.py  # 用户管理 (管理员)
│       ├── admin_ops.py    # 运维操作 (管理员)
│       ├── evaluation.py   # 性能评估
│       ├── agent_tracking.py  # 智能体追踪
│       ├── advanced_rag.py    # 高级RAG技术
│       └── analytics.py       # 检索分析
│
├── baselines/              # 基准系统实现
│   ├── simple_rag.py       # 简单RAG基线
│   └── baseline_manager.py # 基准管理器
│
├── core/                   # 核心配置与工具
│   ├── config.py           # 设置管理 (Pydantic)
│   ├── logging.py          # 日志配置
│   └── exceptions.py       # 自定义异常
│
├── data/                   # 数据模型
│   └── models.py           # Pydantic数据模型
│
├── evaluation/             # RAG评估框架
│   ├── service.py          # 评估服务
│   ├── metrics.py          # 精确率/召回率/F1
│   └── comparison.py       # 系统比较
│
├── graph/                  # LangGraph编排
│   ├── studio_entry.py     # LangGraph Studio入口
│   ├── workflow.py         # 工作流定义
│   ├── state.py            # 状态管理
│   ├── streaming.py        # SSE流式支持
│   └── neo4j_client.py     # Neo4j客户端
│
├── ingestion/              # 文档摄取管道
│   ├── loaders/            # 文档加载器
│   │   ├── pdf_loader.py   # PDF处理 (流式处理)
│   │   ├── text_loader.py  # 文本文件
│   │   └── image_loader.py # 图像+OCR
│   ├── chunkers/           # 分块策略
│   │   ├── parent_child.py # 父子分块
│   │   └── text_splitter.py
│   ├── ocr/                # OCR处理
│   │   ├── tesseract.py    # Tesseract引擎
│   │   └── paddle.py       # PaddleOCR (中文)
│   └── indexer.py          # 索引管理
│
├── models/                 # 数据模型定义
│   └── schemas.py          # API模式
│
├── prompts/                # 提示词模板
│   ├── templates/          # 提示词文件
│   └── manager.py          # 模板管理
│
├── retrievers/             # 检索管道
│   ├── hybrid.py           # 混合检索器 (向量+BM25)
│   ├── vector.py           # ChromaDB向量检索
│   ├── bm25.py             # BM25稀疏检索
│   ├── reranker.py         # 跨编码器重排序
│   ├── fusion.py           # RRF融合算法
│   ├── corpus_store.py     # 语料存储
│   └── query_rewrite.py    # 查询重写
│
├── services/               # 核心服务层
│   ├── auth/               # 认证服务
│   │   ├── service.py      # JWT令牌管理
│   │   ├── db_service.py   # 用户数据库
│   │   └── password.py     # 密码策略
│   ├── rbac.py             # 角色权限控制
│   ├── memory_store.py     # 会话记忆
│   ├── history_store.py    # 会话历史
│   ├── prompt_store.py     # 提示词版本管理
│   ├── runtime_ops.py      # 运行时治理
│   ├── resilience.py       # 弹性工具 (熔断器)
│   ├── bulkhead.py         # 隔离舱模式
│   ├── rate_limiter.py     # 速率限制
│   ├── quota_guard.py      # 配额守卫
│   ├── answer_safety.py    # 答案安全检查
│   ├── consistency_guard.py # 一致性守护
│   ├── evidence_conflict.py # 证据冲突检测
│   ├── request_context.py  # 请求上下文
│   ├── input_normalizer.py # 输入规范化
│   ├── agent_classifier.py # 查询分类器
│   └── runtime_metrics.py  # 运行时指标
│
├── tools/                  # 工具集成
│   └── web_search.py       # DuckDuckGo搜索
│
└── workflow/               # 工作流定义
    └── config.py           # 工作流配置
```

---

### 前端目录结构 (`frontend/`)

```typescript
frontend/
├── src/
│   ├── components/         # 可复用UI组件
│   │   ├── ChatTopbar.tsx  # 聊天顶部栏
│   │   ├── DataFlowVisualization.tsx  # 数据流可视化
│   │   ├── ThemeToggle.tsx # 主题切换
│   │   └── LanguageToggle.tsx  # 语言切换
│   │
│   ├── pages/              # 页面组件
│   │   ├── LoginPage.tsx   # 登录页
│   │   ├── ArchitecturePage.tsx  # 架构可视化
│   │   └── chat/           # 聊天页面模块
│   │       ├── ChatPage.tsx
│   │       └── components/
│   │
│   ├── hooks/              # 自定义React Hooks
│   │   └── useAuth.ts      # 认证Hook
│   │
│   ├── i18n/               # 国际化配置
│   │   ├── config.ts       # i18next配置
│   │   └── locales/        # 翻译文件
│   │       ├── en.json     # 英文
│   │       └── zh.json     # 中文
│   │
│   ├── lib/                # 工具库
│   │   ├── api.ts          # API客户端
│   │   └── theme.ts        # 主题配置
│   │
│   ├── styles/             # CSS样式
│   │   ├── core/           # 核心样式
│   │   │   └── critical.css  # 关键CSS
│   │   ├── components/     # 组件样式
│   │   ├── pages/          # 页面样式
│   │   │   └── auth/       # 认证页面样式
│   │   └── themes/         # 主题变体
│   │       └── dark/       # 暗色主题
│   │
│   ├── types/              # TypeScript类型
│   │   └── index.ts        # 类型定义
│   │
│   ├── App.tsx             # 应用根组件
│   └── main.tsx            # 应用入口点
│
├── public/                 # 静态资源
├── scripts/                # 构建脚本
│   └── extract-critical-css.js  # 关键CSS提取
├── package.json            # Node依赖
├── tsconfig.json           # TypeScript配置
├── vite.config.ts          # Vite配置
├── I18N_README.md          # 国际化文档
└── CSS_CONFLICT_PREVENTION.md  # CSS规范
```

---

## 🌐 API接口清单

### 认证接口 (`/auth`)
| 端点 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/auth/register` | POST | 用户注册 | 公开 |
| `/auth/login` | POST | 用户登录 | 公开 |
| `/auth/logout` | POST | 用户登出 | 认证 |
| `/auth/refresh` | POST | 刷新令牌 | 认证 |
| `/auth/me` | GET | 获取当前用户信息 | 认证 |
| `/auth/oauth/callback` | GET | OAuth回调 | 公开 |

---

### 查询接口 (`/query`)
| 端点 | 方法 | 功能 | 特性 |
|------|------|------|------|
| `/query` | POST | 同步查询 | 分层执行 (Fast/Balanced/Deep) |
| `/query/stream` | POST | 流式查询 | SSE实时输出 |

**查询参数**：
- `question`: 用户查询文本
- `session_id`: 会话ID (可选)
- `tier`: 执行层级 (`auto`/`fast`/`balanced`/`deep`)
- `enable_web`: 启用网络搜索回退
- `enable_graph`: 启用图数据库增强

---

### 会话管理 (`/sessions`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `/sessions` | GET | 列出用户会话 |
| `/sessions` | POST | 创建新会话 |
| `/sessions/{session_id}` | GET | 获取会话详情 |
| `/sessions/{session_id}` | DELETE | 删除会话 |
| `/sessions/{session_id}/history` | GET | 获取会话历史 |
| `/sessions/{session_id}/memory` | GET | 获取会话记忆 |
| `/sessions/{session_id}/strategy` | PUT | 锁定检索策略 |

---

### 文档管理 (`/documents`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `/documents` | GET | 列出文档清单 |
| `/documents` | POST | 上传文档 |
| `/documents/{doc_id}` | DELETE | 删除文档 |
| `/documents/reindex` | POST | 重新索引所有文档 |
| `/documents/metadata` | GET | 获取文档元数据 |

**支持的文档类型**：
- PDF (含OCR扫描件)
- 文本文件 (TXT, MD)
- 图像 (PNG, JPG - 支持OCR和图像描述)
- Office文档 (DOCX, PPTX - 需Docling)

---

### 提示词管理 (`/prompts`)
| 端点 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/prompts` | GET | 列出提示词模板 | 用户 |
| `/prompts` | POST | 创建提示词 | 管理员 |
| `/prompts/{id}` | PUT | 更新提示词 | 管理员 |
| `/prompts/{id}/validate` | POST | 验证提示词 | 管理员 |
| `/prompts/{id}/approve` | POST | 审批提示词 | 管理员 |
| `/prompts/{id}/versions` | GET | 获取版本历史 | 管理员 |
| `/prompts/rollback` | POST | 回滚到历史版本 | 管理员 |

---

### 用户管理 (`/admin/users`) 🔐
| 端点 | 方法 | 功能 |
|------|------|------|
| `/admin/users` | GET | 列出所有用户 |
| `/admin/users/{user_id}` | GET | 获取用户详情 |
| `/admin/users/{user_id}/role` | PUT | 更新用户角色 |
| `/admin/users/{user_id}/status` | PUT | 更新用户状态 |
| `/admin/users/{user_id}` | DELETE | 删除用户 |
| `/admin/users/audit` | GET | 获取审计日志 |

---

### 运维操作 (`/admin/ops`) 🔐
| 端点 | 方法 | 功能 |
|------|------|------|
| `/admin/ops/profiles` | GET | 列出检索配置 |
| `/admin/ops/profiles/{profile}` | PUT | 更新配置 |
| `/admin/ops/canary` | POST | 启用金丝雀路由 |
| `/admin/ops/rollback` | POST | 回滚配置 |
| `/admin/ops/benchmark` | POST | 运行基准测试 |
| `/admin/ops/replay` | POST | 重放历史查询 |
| `/admin/ops/reports` | GET | 获取运维报告 |

**检索配置档案**：
- `baseline`: 基础配置 (仅向量搜索)
- `advanced`: 高级配置 (混合检索+重排序)
- `safe`: 安全配置 (严格过滤)

---

### 模型设置 (`/admin/model-settings`, `/user/api-settings`)
| 端点 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/admin/model-settings` | GET | 获取全局模型配置 | 管理员 |
| `/admin/model-settings` | PUT | 更新全局模型配置 | 管理员 |
| `/user/api-settings` | GET | 获取用户API设置 | 用户 |
| `/user/api-settings` | PUT | 更新用户API密钥 | 用户 |

---

### 性能评估 (`/api/evaluation`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/evaluation/compare` | POST | 比较多个系统 |
| `/api/evaluation/baselines` | GET | 列出基准系统 |
| `/api/evaluation/metrics` | GET | 获取评估指标 |

**评估指标**：
- 精确率 (Precision)
- 召回率 (Recall)
- F1分数
- 平均延迟
- P95/P99延迟
- 引用准确率

---

### 智能体追踪 (`/api/agent-tracking`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/agent-tracking/stream` | GET | SSE实时追踪流 |
| `/api/agent-tracking/history/{query_id}` | GET | 获取执行历史 |

**追踪事件**：
- `agent_start`: 智能体启动
- `agent_thinking`: 思考过程
- `agent_action`: 执行动作
- `agent_complete`: 完成任务
- `agent_error`: 错误事件

---

### 高级RAG技术 (`/api/advanced-rag`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/advanced-rag/decompose` | POST | 查询分解 |
| `/api/advanced-rag/self-rag` | POST | Self-RAG评估 |

**查询分解**：将复杂查询拆分为多个子查询并行处理

**Self-RAG**：检索后评估文档相关性和答案质量

---

### 检索分析 (`/api/analytics`)
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/analytics/stats` | GET | 获取检索统计 |
| `/api/analytics/visualization` | GET | 可视化数据 |
| `/api/analytics/export` | GET | 导出分析报告 |

**统计维度**：
- 查询量趋势
- 检索延迟分布
- 命中率
- 用户活跃度
- 文档热度

---

### 健康检查
| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 (存活探针) |
| `/ready` | GET | 就绪检查 (就绪探针) |
| `/metrics` | GET | Prometheus指标 |

---

## ⚙️ 核心功能模块详解

### 1. 多智能体编排系统

#### 智能体架构
```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Orchestrator               │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Router Agent │  ← 分析查询意图
                    └──────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ Vector RAG   │  │  Graph RAG   │  │ Web Research │
   │    Agent     │  │    Agent     │  │    Agent     │
   └──────────────┘  └──────────────┘  └──────────────┘
           │                │                │
           └────────────────┼────────────────┘
                            ▼
                    ┌──────────────┐
                    │  Synthesis   │  ← 生成最终答案
                    │    Agent     │
                    └──────────────┘
```

#### 1.1 Router Agent (路由智能体)
**职责**：
- 分析查询意图 (事实查询 vs 推理查询)
- 检测查询复杂度 (Fast/Balanced/Deep)
- 决定执行策略 (仅向量 vs 混合 vs 图增强)
- 判断是否需要网络搜索回退

**决策因子**：
- 查询长度和结构
- 关键词密度
- 实体识别
- 问题类型分类 (事实/解释/比较/总结)

---

#### 1.2 Vector RAG Agent (向量检索智能体)
**职责**：
- 执行混合检索 (向量 + BM25)
- 应用RRF融合算法
- 调用跨编码器重排序
- 返回高质量文档片段

**检索流程**：
```python
1. 查询重写 (可选) - 扩展同义词、重新表述
2. 并行检索:
   ├─ ChromaDB向量搜索 (top_k=6-20)
   └─ BM25关键词检索 (top_k=6-20)
3. RRF融合 (k=60)
4. 跨编码器重排序 (top_n=3-10)
5. 父文档检索 (获取完整上下文)
```

---

#### 1.3 Graph RAG Agent (图检索智能体)
**职责**：
- 从查询中提取实体
- 查询Neo4j知识图谱
- 获取实体关系和属性
- 提供结构化上下文

**图查询类型**：
- 单跳关系: `(实体A)-[:关系]->(实体B)`
- 多跳路径: 2-3跳深度搜索
- 子图提取: 获取实体邻域
- 属性查询: 实体属性和元数据

**优化**：
- 实体缓存 (Redis)
- 查询超时控制 (5秒)
- 结果大小限制 (最多100个节点)

---

#### 1.4 Web Research Agent (网络研究智能体)
**职责**：
- 本地知识不足时触发
- 执行DuckDuckGo搜索
- 过滤可信域名 (政府、教育、知名机构)
- 提取网页内容并去噪

**触发条件**：
- 路由智能体判断本地知识不足
- 向量检索得分低于阈值 (< 0.2)
- 用户显式启用 `enable_web=true`

**安全控制**：
```python
WEB_DOMAIN_ALLOWLIST = [
    'gov.cn', 'gov', 'edu', 'org',
    'nist.gov', 'cisa.gov', 'mitre.org',
    'wikipedia.org', 'owasp.org',
    'microsoft.com', 'openai.com'
]
WEB_MIN_SOURCE_SCORE = 0.2
```

---

#### 1.5 Synthesis Agent (合成智能体)
**职责**：
- 整合所有检索证据
- 生成连贯答案
- 添加引用标注
- 执行安全和一致性检查

**答案生成流程**：
```python
1. 证据排序和去重
2. 冲突检测 (evidence_conflict.py)
3. LLM生成答案
4. 引用提取和验证
5. 安全扫描 (answer_safety.py)
6. 一致性检查 (consistency_guard.py)
7. 最终答案输出
```

**质量保证**：
- **Grounding支持率**: ≥60% 的答案有引用支持
- **冲突检测**: 检测矛盾证据并标注
- **安全扫描**: 过滤有害内容、PII泄露
- **一致性守护**: 验证答案与证据的一致性 (相似度≥0.55)

---

### 2. 分层执行系统

#### 三层架构
| 层级 | 适用场景 | 检索配置 | 超时限制 | Token限制 | 网络回退 |
|------|----------|----------|----------|-----------|----------|
| **Fast** | 简单事实查询、单实体查找 | `vector_top_k=5`<br>`bm25_top_k=5`<br>`rerank_top_n=3` | 800ms | 300 | ❌ 禁用 |
| **Balanced** | 默认层级、中等复杂度 | `vector_top_k=10`<br>`bm25_top_k=10`<br>`rerank_top_n=5` | 2000ms | 800 | ⚠️ 条件启用 |
| **Deep** | 多跳推理、综合分析 | `vector_top_k=20`<br>`bm25_top_k=20`<br>`rerank_top_n=10` | 5000ms | 1500 | ✅ 默认启用 |

#### 自动分层逻辑
```python
def classify_tier(query: str) -> Tier:
    # 1. 查询长度
    if len(query) < 20:
        return Tier.FAST
    
    # 2. 关键词密度
    keywords = extract_keywords(query)
    if len(keywords) > 5:
        return Tier.DEEP
    
    # 3. 问题类型
    question_type = classify_question(query)
    if question_type in ['comparison', 'explanation', 'analysis']:
        return Tier.DEEP
    elif question_type in ['fact', 'entity']:
        return Tier.FAST
    
    # 4. 默认平衡
    return Tier.BALANCED
```

#### 负载降级
当系统负载 > 80% 时，自动降级：
- Deep → Balanced
- Balanced → Fast
- 禁用重排序和网络搜索

---

### 3. 混合检索管道

#### 3.1 向量检索 (Dense Retrieval)
**引擎**: ChromaDB  
**嵌入模型**:
- OpenAI: `text-embedding-3-small` (1536维)
- Ollama: `nomic-embed-text` (768维)

**配置**：
```python
VECTOR_TOP_K = 6-20 (动态调整)
VECTOR_SIMILARITY_THRESHOLD = 0.2  # 标准阈值
VECTOR_SIMILARITY_RELAXED_THRESHOLD = 0.05  # 宽松阈值
```

**优化**：
- 查询嵌入缓存 (TTL=45秒)
- 批量嵌入处理
- 余弦相似度计算

---

#### 3.2 BM25检索 (Sparse Retrieval)
**实现**: `rank-bm25` 库  
**分词**:
- 英文: 空格分词 + 小写化
- 中文: Jieba分词

**配置**：
```python
BM25_TOP_K = 6-20 (动态调整)
BM25参数:
├─ k1 = 1.5  # 词频饱和参数
└─ b = 0.75  # 文档长度归一化
```

**特性**：
- 精确关键词匹配
- 词频-逆文档频率 (TF-IDF)
- 文档长度归一化
- 中文分词支持

---

#### 3.3 RRF融合 (Reciprocal Rank Fusion)
**算法**：
```python
def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)

# 融合向量和BM25结果
final_score = rrf_score(vector_rank) + rrf_score(bm25_rank)
```

**配置**：
```python
HYBRID_RRF_K = 60
HYBRID_VECTOR_WEIGHT = 0.95  # 向量权重
HYBRID_BM25_WEIGHT = 0.05    # BM25权重
```

**优势**：
- 平衡语义和关键词匹配
- 鲁棒性强（不依赖绝对分数）
- 减少单一检索器偏差

---

#### 3.4 跨编码器重排序
**模型**: `BAAI/bge-reranker-v2-m3`  
**类型**: Cross-Encoder (交叉编码器)

**工作流程**：
```python
1. 输入: 查询 + 候选文档列表 (10-20个)
2. 计算: 每对 (query, doc) 的相关性分数
3. 排序: 按分数降序排列
4. 输出: Top-N 最相关文档 (3-10个)
```

**性能**：
- 精度提升: +15-25% 相比无重排序
- 延迟: ~50-200ms (取决于候选数量)
- GPU加速: 支持CUDA推理

**配置**：
```python
ENABLE_RERANKER = true
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
RERANKER_TOP_N = 3-10 (分层调整)
```

---

#### 3.5 父子分块策略
**目标**: 平衡检索精度和答案上下文

**两层结构**：
```python
父块 (Parent Chunk):
├─ 大小: 1500字符
├─ 重叠: 200字符
└─ 用途: 提供完整上下文给LLM

子块 (Child Chunk):
├─ 大小: 600字符
├─ 重叠: 120字符
└─ 用途: 用于检索匹配
```

**检索流程**：
```
1. 用子块进行检索 (精确匹配)
2. 检索到子块后，返回对应的父块
3. 父块提供更完整的上下文给LLM
```

**优势**：
- 更精确的语义匹配
- 更丰富的上下文信息
- 减少上下文截断问题

---

### 4. 查询优化

#### 4.1 查询重写
**策略**：
- 同义词扩展 (基于规则或LLM)
- 查询重新表述
- 去重相似变体

**配置**：
```python
QUERY_REWRITE_ENABLED = true
QUERY_REWRITE_WITH_LLM = false  # 使用规则还是LLM
QUERY_REWRITE_MAX_VARIANTS = 6  # 最多生成变体数
```

**效果**：
- 召回率提升: +10-30%
- LLM调用减少: 10-30% (通过去重)

---

#### 4.2 查询分解 (Query Decomposition)
**适用**: 复杂多子问题查询

**示例**：
```
原查询: "比较Python和JavaScript的异步编程模型，并说明各自的优缺点"

分解后:
├─ 子查询1: "Python的异步编程模型是什么"
├─ 子查询2: "JavaScript的异步编程模型是什么"
├─ 子查询3: "Python异步编程的优缺点"
└─ 子查询4: "JavaScript异步编程的优缺点"
```

**并行处理**：
- 每个子查询独立检索
- 结果合并和去重
- 综合生成最终答案

---

#### 4.3 中文查询优化
**Jieba分词**：
```python
import jieba
tokens = jieba.lcut(query)  # 精确模式
# "机器学习算法" → ["机器", "学习", "算法"]
```

**同义词扩展**：
```python
synonyms = {
    "机器学习": ["ML", "Machine Learning", "机器学习"],
    "深度学习": ["DL", "Deep Learning", "深度学习"],
    "神经网络": ["NN", "Neural Network", "神经网络"]
}
```

**复杂度检测**：
```python
def is_chinese_heavy(query: str) -> bool:
    chinese_chars = len([c for c in query if '一' <= c <= '鿿'])
    return chinese_chars / len(query) > 0.20  # 20%阈值
```

---

## 🔒 安全与权限控制

### 1. 认证系统

#### JWT令牌机制
```python
认证流程:
1. 用户登录 → 验证密码
2. 生成JWT访问令牌 (有效期: 24小时)
3. 令牌存储在HTTP-only Cookie中
4. 每次请求携带令牌进行验证
5. 令牌过期后需要重新登录
```

**令牌配置**：
```python
AUTH_TOKEN_TTL_HOURS = 24
AUTH_COOKIE_SECURE = true      # HTTPS-only
AUTH_COOKIE_SAMESITE = "strict" # CSRF防护
AUTH_COOKIE_HTTPONLY = true    # 防止XSS
```

**安全特性**：
- 常量时间令牌比较（防止时序攻击）
- 令牌黑名单（登出后失效）
- 自动过期清理
- 会话绑定（IP + User-Agent验证可选）

---

#### 密码策略
```python
强制要求:
├─ 长度: 12-128 字符
├─ 必须包含: 特殊字符 (!@#$%^&*等)
├─ 存储: bcrypt哈希 (成本因子=12)
└─ 验证: 使用安全比较函数
```

**登录保护**：
```python
AUTH_LOGIN_MAX_FAILURES = 8      # 最大失败次数
AUTH_LOGIN_WINDOW_SECONDS = 300  # 时间窗口(5分钟)
# 超过限制 → 账户临时锁定
```

**注册限流**：
```python
AUTH_REGISTER_MAX_ATTEMPTS = 12
AUTH_REGISTER_WINDOW_SECONDS = 300
```

---

### 2. RBAC权限控制

#### 角色定义
```python
class Role(Enum):
    USER = "user"     # 普通用户
    ADMIN = "admin"   # 管理员
```

#### 权限矩阵
| 功能 | USER | ADMIN |
|------|------|-------|
| 查询文档 | ✅ | ✅ |
| 管理自己的会话 | ✅ | ✅ |
| 上传文档 | ✅ | ✅ |
| 查看所有用户 | ❌ | ✅ |
| 修改用户角色 | ❌ | ✅ |
| 删除用户 | ❌ | ✅ |
| 管理提示词模板 | ❌ | ✅ |
| 运维操作（金丝雀/回滚） | ❌ | ✅ |
| 查看审计日志 | ❌ | ✅ |
| 系统配置 | ❌ | ✅ |

#### 会话隔离
```python
用户数据隔离:
├─ 会话: 仅可见自己的会话
├─ 文档: 用户级权限控制（可选）
├─ 历史记录: 会话绑定
└─ API设置: 用户私有加密存储
```

---

### 3. 管理员创建机制

**审批令牌系统**：
```python
# 生成审批令牌
approval_token = secrets.token_urlsafe(32)

# 哈希后存储在环境变量
ADMIN_CREATE_APPROVAL_TOKEN_HASH = bcrypt.hash(approval_token)

# 创建管理员时验证
POST /auth/register
{
  "username": "admin",
  "password": "secure_password",
  "role": "admin",
  "approval_token": "<one-time-token>"
}
```

**安全特性**：
- 单次使用：令牌使用后立即标记为已用
- 哈希存储：环境变量存储哈希值而非明文
- 审计追踪：记录管理员创建事件

---

### 4. 数据加密

#### API凭证加密
```python
# 用户API密钥加密存储
API_SETTINGS_ENCRYPTION_KEY = <32-byte-key>

加密流程:
1. 用户输入API密钥
2. 使用Fernet对称加密
3. 加密后存储到SQLite数据库
4. 使用时解密（仅在内存中）
```

#### 敏感配置保护
```
.env 文件安全:
├─ 不提交到Git (.gitignore)
├─ 生产环境使用环境变量
├─ 开发环境使用 .env.example 模板
└─ 定期轮换密钥
```

---

### 5. 审计日志

**记录事件**：
```python
审计范围:
├─ 用户登录/登出
├─ 管理员创建/删除用户
├─ 角色/状态变更
├─ 配置更新（检索配置、模型设置）
├─ 文档上传/删除
├─ 敏感操作失败（登录失败、权限拒绝）
└─ 系统运维操作（金丝雀、回滚）
```

**日志字段**：
```python
{
  "timestamp": "2026-06-07T10:30:00Z",
  "user_id": "user123",
  "action": "delete_user",
  "target": "user456",
  "ip_address": "192.168.1.100",
  "status": "success",
  "metadata": {...}
}
```

**存储**：
- SQLite数据库 (`APP_DB_PATH`)
- 保留期：建议180天
- 仅管理员可访问

---

### 6. 输入验证与防护

#### SQL注入防护
- 使用参数化查询（SQLite）
- ORM安全实践（Pydantic验证）

#### XSS防护
```python
前端:
├─ react-markdown (安全渲染)
├─ DOMPurify (HTML清理)
└─ CSP头部配置

后端:
└─ 自动转义HTML输出
```

#### CSRF防护
```python
Cookie配置:
├─ SameSite=Strict
├─ HTTP-only
└─ Secure (HTTPS)
```

#### 文件上传安全
```python
限制:
├─ 文件类型: 白名单 (.pdf, .txt, .md, .png, .jpg)
├─ 文件大小: 20MB/文件, 100MB/批次
├─ 文件数量: 20个/批次
├─ 病毒扫描: 可选集成
└─ 隔离存储: UPLOADS_DIR
```

#### API限流
```python
速率限制:
├─ 登录端点: 8次/5分钟
├─ 注册端点: 12次/5分钟
├─ 查询端点: 用户级配额
└─ 管理端点: 更严格限制
```

---

### 7. 网络安全

#### API Base URL白名单
```python
# 防止SSRF攻击
API_BASE_URL_ALLOWLIST = "api.openai.com,api.anthropic.com"
API_BASE_URL_ALLOW_PRIVATE = false  # 禁止内网地址
API_BASE_URL_DNS_CHECK = true       # DNS验证
```

#### Web搜索域名过滤
```python
WEB_DOMAIN_ALLOWLIST = [
    'gov.cn', 'gov', 'edu', 'org',
    'nist.gov', 'cisa.gov', 'mitre.org',
    'wikipedia.org', 'owasp.org'
]
# 仅允许可信域名的搜索结果
```

---

## 🧪 测试覆盖

### 测试统计
```
总测试文件: 89个
测试类型分布:
├─ 单元测试: ~60个 (组件级)
├─ 集成测试: ~20个 (跨模块)
└─ 工作流测试: ~9个 (端到端)
```

### 主要测试模块

#### 1. 核心服务测试
```python
tests/test_auth_service.py          # 认证服务
tests/test_auth_db_service.py       # 用户数据库
tests/test_security_hardening.py    # 安全加固
tests/test_rbac.py                  # 权限控制
tests/test_memory_store.py          # 会话记忆
tests/test_history_store.py         # 历史存储
tests/test_prompt_store.py          # 提示词存储
```

#### 2. 检索系统测试
```python
tests/test_retrieval_strategy.py    # 检索策略
tests/test_chunker_parent_child.py  # 分块策略
tests/test_index_manager.py         # 索引管理
tests/test_ingestion_loaders.py     # 文档加载
```

#### 3. 智能体测试
```python
tests/test_routing_logic.py         # 路由逻辑
tests/test_agent_classifier.py      # 查询分类
tests/test_pdf_agent_guard.py       # PDF智能体守卫
tests/test_query_intent.py          # 意图识别
```

#### 4. 图数据库测试
```python
tests/test_graph_extractor.py       # 图提取
tests/test_graph_tools_enhancement.py # 图工具增强
tests/test_neo4j_delete_by_source.py # 源删除
```

#### 5. 安全与质量测试
```python
tests/test_answer_safety.py         # 答案安全
tests/test_consistency_guard.py     # 一致性守护
tests/test_evidence_conflict.py     # 证据冲突
tests/test_citation_grounding.py    # 引用支撑
tests/test_web_research_filtering.py # 网络搜索过滤
```

#### 6. 弹性与性能测试
```python
tests/test_resilience.py            # 弹性工具（熔断器）
tests/test_concurrency_regression.py # 并发回归
tests/test_input_normalizer.py      # 输入规范化
```

#### 7. API测试
```python
tests/test_admin_ops_api.py         # 运维API
tests/test_readiness_api.py         # 就绪检查
```

#### 8. 工作流测试
```python
tests/test_runtime_ops.py           # 运行时操作
tests/test_prompt_versions.py       # 提示词版本
tests/test_prompt_checker.py        # 提示词检查
tests/test_history_strategy_lock.py # 策略锁定
tests/test_history_session_security.py # 会话安全
```

### 测试运行

#### 基本命令
```bash
# 运行所有测试
pytest -q

# 带覆盖率
pytest --cov=app --cov-report=html

# 运行特定测试
pytest tests/test_routing_logic.py -v

# 并行测试
pytest -n auto
```

#### CI质量门禁
```bash
python scripts/ci_quality_gate.py

检查项:
├─ 后端测试 (29+ 核心测试)
├─ RAG评估 (精确率/召回率/F1)
├─ 性能基准 (延迟/吞吐量)
└─ 代码质量 (ruff)

退出码:
├─ 0 = 全部通过
├─ 1 = 后端测试失败
├─ 2 = 精确率低于阈值
├─ 3 = F1分数低于阈值
└─ 4 = 召回率低于阈值 (非阻塞)
```

### 测试配置 (pyproject.toml)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --strict-markers --tb=short"
markers = [
  "unit: Unit tests",
  "performance: Performance tests",
  "integration: Integration tests",
  "slow: Slow tests"
]
asyncio_mode = "auto"
```

---

## ⚙️ 配置管理

### 环境变量配置

#### 1. 模型与运行时
```bash
# 模型后端选择
MODEL_BACKEND=local|ollama|openai|anthropic|deepseek|custom
REASONING_MODEL_BACKEND=  # 推理模型后端（可选）

# 超时配置
QUERY_REQUEST_TIMEOUT_MS=60000  # 查询超时(60秒)
STREAM_HEARTBEAT_SECONDS=6      # 流式心跳间隔
```

#### 2. OpenAI配置
```bash
OPENAI_API_KEY=<your-key>
OPENAI_BASE_URL=https://api.openai.com/v1  # 可自定义
OPENAI_CHAT_MODEL=gpt-5.4-codex
OPENAI_EMBED_MODEL=text-embedding-3-small
OPENAI_REASONING_MODEL=gpt-5.4-codex
OPENAI_VISION_MODEL=gpt-4.1-mini
```

#### 3. Anthropic配置
```bash
ANTHROPIC_API_KEY=<your-key>
ANTHROPIC_CHAT_MODEL=claude-sonnet-4-6
ANTHROPIC_REASONING_MODEL=claude-sonnet-4-6
```

#### 4. Ollama配置
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_REASONING_MODEL=
OLLAMA_VISION_MODEL=llava:7b
```

#### 5. 数据库配置
```bash
# Neo4j图数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<strong-password>

# ChromaDB向量数据库
CHROMA_COLLECTION=local_rag_collection
CHROMA_PERSIST_DIR=./data/chroma

# Redis缓存（可选）
REDIS_URL=redis://localhost:6379/0
RETRIEVAL_CACHE_BACKEND=auto  # auto|redis|memory
```

#### 6. 存储路径
```bash
DATA_DIR=./data/docs                    # 源文档目录
CORPUS_STORE_PATH=./data/chunks/chunks.jsonl   # 子块存储
PARENT_STORE_PATH=./data/chunks/parents.jsonl  # 父块存储
SESSIONS_DIR=./data/sessions            # 会话目录
UPLOADS_DIR=./data/uploads              # 上传目录
APP_DB_PATH=./data/app.db               # SQLite数据库
USERS_FILE=./data/security/users.json   # 用户文件
AUTH_SESSIONS_FILE=./data/security/auth_sessions.json
```

#### 7. 分块配置
```bash
# 父块
PARENT_CHUNK_SIZE=1500
PARENT_CHUNK_OVERLAP=200

# 子块
CHILD_CHUNK_SIZE=600
CHILD_CHUNK_OVERLAP=120
```

#### 8. 检索配置
```bash
# 基础检索
TOP_K=4                      # 最终返回数量
MAX_CONTEXT_CHUNKS=6         # 最大上下文块数
VECTOR_TOP_K=6               # 向量检索数量
BM25_TOP_K=6                 # BM25检索数量

# 混合检索
HYBRID_RRF_K=60              # RRF参数k
HYBRID_VECTOR_WEIGHT=0.95    # 向量权重
HYBRID_BM25_WEIGHT=0.05      # BM25权重

# 相似度阈值
VECTOR_SIMILARITY_THRESHOLD=0.2         # 标准阈值
VECTOR_SIMILARITY_RELAXED_THRESHOLD=0.05 # 宽松阈值

# 重排序
ENABLE_RERANKER=true
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3
RERANKER_TOP_N=5
```

#### 9. 查询优化
```bash
# 查询重写
QUERY_REWRITE_ENABLED=true
QUERY_REWRITE_WITH_LLM=false  # 使用LLM还是规则
QUERY_REWRITE_MAX_VARIANTS=6

# 查询分解
QUERY_DECOMPOSE_ENABLED=true

# 排序特征
RANK_FEATURE_ENABLED=true
RANK_FEATURE_SOURCE_WEIGHT=0.08        # 源权重
RANK_FEATURE_FRESHNESS_WEIGHT=0.07    # 新鲜度权重
RANK_FEATURE_RETRIEVAL_DIVERSITY_WEIGHT=0.05  # 多样性权重

# 动态检索
DYNAMIC_RETRIEVAL_ENABLED=true
DYNAMIC_VECTOR_TOP_K_CAP=16
DYNAMIC_BM25_TOP_K_CAP=16
DYNAMIC_RERANKER_TOP_N_CAP=10
```

#### 10. 缓存配置
```bash
RETRIEVAL_CACHE_ENABLED=true
RETRIEVAL_CACHE_TTL_SECONDS=45      # 缓存有效期
RETRIEVAL_CACHE_MAX_ITEMS=256       # 最大缓存项
RETRIEVAL_CACHE_BACKEND=auto        # auto|redis|memory
```

#### 11. 弹性配置
```bash
# 熔断器
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAIL_THRESHOLD=3    # 失败阈值
CIRCUIT_BREAKER_COOLDOWN_SECONDS=30 # 冷却时间

# 可观测性
OTEL_TRACING_ENABLED=true
```

#### 12. 运维配置
```bash
# 检索配置档案
RETRIEVAL_PROFILE=advanced  # baseline|advanced|safe

# 一致性守护
CONSISTENCY_GUARD_ENABLED=true
CONSISTENCY_GUARD_SIMILARITY_THRESHOLD=0.55

# Web搜索
WEB_DOMAIN_ALLOWLIST=gov.cn,gov,edu,org,wikipedia.org
WEB_MIN_SOURCE_SCORE=0.2

# 答案安全
ANSWER_SAFETY_SCAN_ENABLED=true

# SLO阈值
SLO_P95_LATENCY_MS_THRESHOLD=3000
SLO_ERROR_RATE_PERCENT_THRESHOLD=5
SLO_GROUNDING_SUPPORT_RATIO_THRESHOLD=0.6
```

#### 13. 图提取配置
```bash
GRAPH_EXTRACTION_MODE=llm  # llm|spacy|none
GRAPH_TRIPLET_BATCH_CHARS=2200
```

#### 14. 自动摄取
```bash
AUTO_INGEST_ENABLED=false
AUTO_INGEST_INTERVAL_SECONDS=3
AUTO_INGEST_WATCH_DOCS=true
AUTO_INGEST_WATCH_UPLOADS=true
AUTO_INGEST_RECURSIVE=true
```

#### 15. 认证配置
```bash
AUTH_TOKEN_TTL_HOURS=24
AUTH_LOGIN_MAX_FAILURES=8
AUTH_LOGIN_WINDOW_SECONDS=300
AUTH_REGISTER_MAX_ATTEMPTS=12
AUTH_REGISTER_WINDOW_SECONDS=300

# 管理员审批
ADMIN_CREATE_APPROVAL_TOKEN_HASH=<bcrypt-hash>

# API设置加密
API_SETTINGS_ENCRYPTION_KEY=<32-byte-key>
API_BASE_URL_ALLOWLIST=api.openai.com,api.anthropic.com
API_BASE_URL_ALLOW_PRIVATE=false
API_BASE_URL_DNS_CHECK=true
```

#### 16. 文件上传
```bash
UPLOAD_MAX_FILES=20
UPLOAD_MAX_FILE_BYTES=20971520       # 20MB
UPLOAD_MAX_TOTAL_BYTES=104857600     # 100MB
UPLOAD_READ_CHUNK_BYTES=1048576      # 1MB
```

#### 17. OCR配置
```bash
# Tesseract
TESSERACT_CMD=<path-to-tesseract>    # 可选
TESSERACT_LANG=chi_sim+eng           # 语言包
TESSDATA_PREFIX=<path>               # 数据目录
OCR_PREPROCESS_ENABLED=true
OCR_UPSCALE_MIN_SIDE=1200
OCR_PSM_MODES=6,11,3

# 人物检测
PEOPLE_DETECTION_ENABLED=true
PEOPLE_DETECTION_MODE=face           # face|pose

# 图像描述
IMAGE_CAPTION_ENABLED=false
IMAGE_CAPTION_BACKEND=auto           # auto|openai|ollama
```

#### 18. PDF处理
```bash
PDF_CACHE_TTL_DAYS=30               # 缓存有效期
PDF_STREAMING_CHUNK_SIZE=10         # 流式处理块大小
PDF_BATCH_CHART_SIZE=5              # 批量图表提取
PDF_ENABLE_METRICS=true             # 启用指标收集
```

---

## 📊 版本历史与改进

### v0.4.3 (2026-06-02) - 当前版本
**主题**: 异常处理卓越

**核心改进**：
- ✅ **100%异常处理覆盖**：消除55个裸异常处理，引入15+特定异常类型
- ✅ **错误诊断速度提升200%**：通过精确异常分类
- ✅ **优雅降级**：Redis→内存、LLM→规则回退
- ✅ **生产级错误处理**：上下文信息丰富的日志

**优化轮次**：
- Round 8: 服务层 + OCR (prompt_checker, query_guard, query_result_cache)
- Round 9: 深度服务优化 (6文件, 21改进)
- Round 10: 可选依赖最终化 (100%完成)

**影响**：
- 零性能回归
- 更快的调试和问题解决
- 自文档化的异常处理

---

### v0.4.2 (2026-05-22)
**主题**: 安全加固与卫生

**核心改进**：
- 🔧 **FastAPI生命周期现代化**：`@app.on_event` → `lifespan`上下文管理器
- 🧹 **代码清理**：删除375行备份文件，135行死代码
- ⚠️ **9个静默失败路径增加日志**
- 🕐 **时间API现代化**：`datetime.utcnow()` → `datetime.now(timezone.utc)`
- 📦 **配置整合**：pytest.ini, .coveragerc → pyproject.toml

**净变化**: 18文件, +471/-742行 (净-271)

---

### v0.4.1 (2026-05-20)
**主题**: 代码质量重构

**核心改进**：
- ♻️ **消除~2,700行重复代码**
- 🧩 **创建19个可复用模块和组件**
- 🛠️ **标准化错误响应**：专用工具类
- 🌍 **多语言支持**：自动语言检测（20%中文阈值）
- 📊 **分析仪表板**：检索监控、统计、导出

---

### v0.4.0 (2026-05-16)
**主题**: 性能比较与中文优化

**核心改进**：
- 📊 **性能比较框架**：基准系统 + 评估指标
- 👁️ **智能体执行可视化**：实时追踪 + SSE流式
- 🇨🇳 **中文NLP优化**：Jieba分词、同义词扩展、查询预处理
- 🚀 **高级RAG技术**：查询分解、Self-RAG评估

---

### v0.3.x 及更早版本
详见 [CHANGELOG.md](../CHANGELOG.md) 和 [docs/VERSION_HISTORY.md](VERSION_HISTORY.md)

---

## 📌 当前项目状态分析

### Git状态快照 (2026-06-07)

#### 修改的文件 (Modified)
```
前端修改 (11个文件):
├─ frontend/package.json
├─ frontend/package-lock.json
├─ frontend/src/App.tsx
├─ frontend/src/main.tsx
├─ frontend/src/components/
│   ├─ DataFlowVisualization.tsx
│   └─ ThemeToggle.tsx
├─ frontend/src/pages/
│   ├─ ArchitecturePage.tsx
│   ├─ LoginPage.tsx
│   └─ chat/components/ChatTopbar.tsx
├─ frontend/src/lib/theme.ts
└─ frontend/src/styles/
    ├─ core/critical.css
    ├─ pages/auth/layout.css
    └─ themes/dark/auth.css
```

**分析**：前端正在进行主题和国际化相关的改进

#### 未跟踪的文件 (Untracked)
```
新增内容:
├─ .claude/memory/                    # Claude记忆存储
├─ docs/
│   ├─ VISUALIZATION_*.md             # 可视化文档
│   ├─ dashboard.html                 # 仪表板
│   ├─ structure_*.txt/html           # 结构报告
│   ├─ project/
│   │   ├─ MANUFACTURING_IMPLEMENTATION_PLAN.md
│   │   └─ VERTICAL_INDUSTRY_ANALYSIS.md
│   └─ visualizations/                # 可视化输出
├─ frontend/
│   ├─ CSS_CONFLICT_PREVENTION.md     # CSS规范
│   ├─ I18N_README.md                 # 国际化文档
│   ├─ src/components/LanguageToggle.tsx
│   ├─ src/i18n/                      # 国际化配置
│   └─ src/styles/components/
│       ├─ language-toggle.css
│       └─ theme-toggle.css
└─ scripts/
    ├─ eval_rag_ragas.py              # RAGAS评估
    └─ visualize_*.py                 # 可视化脚本
```

**分析**：
1. 国际化功能已实现但未提交
2. 项目结构可视化工具已开发
3. 垂直行业分析文档已创建
4. RAGAS评估集成正在进行

#### 最近提交
```
aa43206 - docs: add comprehensive problem resolution summary
a58980b - fix: improve Chinese query complexity detection
84260f8 - feat: implement v0.4.4 accuracy and speed optimizations
5534b17 - docs: fix remaining cross-reference links
afea2da - docs: update release notes links
```

**分析**：
- 正在准备v0.4.4版本（精度和速度优化）
- 中文查询优化持续改进
- 文档链接修复和整理

---

### 技术债务评估

#### 优先级1 - 高优先级
1. **未提交的国际化功能**
   - 影响：功能完成但未纳入版本控制
   - 建议：评估后提交或清理

2. **未跟踪的可视化脚本**
   - 影响：工具未标准化
   - 建议：整理到scripts目录并提交

#### 优先级2 - 中优先级
3. **前端样式修改**
   - 影响：主题系统改进中
   - 建议：完成后统一提交

4. **垂直行业文档**
   - 影响：项目扩展规划
   - 建议：评估是否应归档到internal_docs

#### 优先级3 - 低优先级
5. **临时测试目录**
   - `.pytest_tmp_run_*` 多个临时目录
   - 建议：配置清理策略

---

## 📦 依赖关系分析

### 核心依赖图

```
FastAPI应用层
    ├─→ LangGraph (多智能体编排)
    │   ├─→ LangChain (LLM抽象)
    │   │   ├─→ langchain-openai
    │   │   ├─→ langchain-anthropic
    │   │   └─→ langchain-ollama
    │   └─→ langgraph-cli (开发工具)
    │
    ├─→ 检索系统
    │   ├─→ ChromaDB (向量数据库)
    │   │   └─→ langchain-chroma
    │   ├─→ rank-bm25 (稀疏检索)
    │   ├─→ sentence-transformers (重排序) [可选]
    │   └─→ scikit-learn (相似度计算)
    │
    ├─→ 图数据库
    │   └─→ neo4j (Python驱动)
    │
    ├─→ 文档处理
    │   ├─→ pypdf (PDF解析)
    │   ├─→ Pillow (图像处理)
    │   ├─→ pytesseract (OCR) [可选]
    │   ├─→ paddleocr (中文OCR) [可选]
    │   └─→ docling (结构化提取) [可选]
    │
    ├─→ 中文NLP
    │   └─→ jieba (分词)
    │
    ├─→ 缓存与弹性
    │   ├─→ redis (缓存)
    │   └─→ tenacity (重试)
    │
    ├─→ 认证与安全
    │   ├─→ authlib (OAuth/JWT)
    │   └─→ itsdangerous (签名)
    │
    ├─→ HTTP客户端
    │   ├─→ httpx (异步HTTP)
    │   └─→ ddgs (DuckDuckGo搜索)
    │
    └─→ 数据验证
        ├─→ pydantic (模型验证)
        └─→ pydantic-settings (配置)
```

### 依赖版本要求

#### 严格要求 (>=)
```python
核心框架:
├─ Python >= 3.11
├─ fastapi >= 0.115.0
├─ uvicorn >= 0.30.0
└─ pydantic >= 2.8.0

AI/ML:
├─ langchain >= 0.3.0
├─ langgraph >= 0.2.0
├─ langchain-community >= 0.3.0
└─ chromadb >= 0.5.5

存储:
├─ neo4j >= 5.24.0
└─ redis >= 5.0.0
```

#### 可选依赖管理
```python
# 最小安装（核心功能）
pip install -e .

# OCR支持
pip install -e ".[ocr]"

# 中文OCR（PaddleOCR）
pip install -e ".[paddle]"

# 高级文档处理（Docling）
pip install -e ".[docling]"

# 重排序（sentence-transformers）
pip install -e ".[reranker]"

# 完整安装
pip install -e ".[full]"

# 开发工具
pip install -e ".[dev]"
```

### 前端依赖

#### 生产依赖
```json
核心:
├─ react@18.3.1
├─ react-dom@18.3.1
└─ react-router-dom@6.30.3

国际化:
├─ i18next@26.3.1
└─ react-i18next@17.0.8

可视化:
├─ reactflow@11.11.4
└─ recharts@3.8.1

Markdown:
├─ react-markdown@9.0.1
└─ remark-gfm@4.0.0

工具:
└─ clsx@2.1.1
```

#### 开发依赖
```json
构建:
├─ vite@6.4.2
├─ @vitejs/plugin-react-swc@3.11.0
└─ typescript@5.9.3

优化:
├─ critical@7.2.1
├─ purgecss@8.0.0
└─ esbuild@0.28.0

测试:
├─ @playwright/test@1.59.1
└─ puppeteer@23.11.1
```

---

## 🚀 部署指南

### 开发环境部署

#### 1. 环境准备
```bash
# 创建conda环境
conda create -n rag-local python=3.11
conda activate rag-local

# 安装依赖
pip install -U pip
pip install -e ".[full,dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件配置模型后端
```

#### 2. 启动Neo4j
```bash
docker compose up -d neo4j
```

#### 3. 启动后端
```bash
uvicorn app.api.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --reload-dir app \
  --reload-include "*.py" \
  --reload-exclude "data/*" \
  --reload-exclude "artifacts/*" \
  --reload-exclude "frontend/*"
```

#### 4. 启动前端
```bash
cd frontend
npm install
npm run dev
```

#### 5. 访问应用
- 前端: http://127.0.0.1:5173/app
- 后端API文档: http://127.0.0.1:8000/docs
- Neo4j浏览器: http://127.0.0.1:7474

---

### 生产环境部署建议

#### 1. 环境变量配置
```bash
# 使用生产级配置
APP_ENV=production

# HTTPS强制
AUTH_COOKIE_SECURE=true

# 性能优化
RETRIEVAL_CACHE_BACKEND=redis
REDIS_URL=redis://redis-server:6379/0

# 安全配置
API_BASE_URL_ALLOW_PRIVATE=false
API_BASE_URL_DNS_CHECK=true
```

#### 2. 数据库持久化
```yaml
# docker-compose.prod.yml
services:
  neo4j:
    volumes:
      - /data/neo4j/data:/data
      - /data/neo4j/logs:/logs
```

#### 3. 反向代理 (Nginx)
```nginx
server {
    listen 443 ssl http2;
    server_name rag.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端
    location / {
        root /var/www/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE流式端点
    location /query/stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

#### 4. 进程管理 (Systemd)
```ini
# /etc/systemd/system/rag-backend.service
[Unit]
Description=RAG Backend Service
After=network.target neo4j.service

[Service]
Type=simple
User=rag
WorkingDirectory=/opt/rag-app
Environment="PATH=/opt/conda/envs/rag-local/bin"
ExecStart=/opt/conda/envs/rag-local/bin/uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 5. 日志管理
```python
# app/core/logging.py 配置
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    '/var/log/rag-app/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

#### 6. 监控与告警
```python
# Prometheus指标端点
GET /metrics

关键指标:
├─ query_latency_seconds (直方图)
├─ query_total (计数器)
├─ retrieval_cache_hit_rate (仪表)
├─ llm_token_usage_total (计数器)
└─ active_sessions_count (仪表)
```

---

## 💡 优化建议与最佳实践

### 性能优化

#### 1. 检索优化
```python
建议配置:
├─ 启用Redis缓存 (生产环境)
├─ 调整top_k参数平衡精度和速度
├─ 使用Fast层级处理简单查询
└─ 启用查询重写去重 (减少10-30% LLM调用)
```

#### 2. 模型选择
```python
场景推荐:
├─ 开发/测试: Ollama (qwen2.5:7b-instruct)
├─ 生产低延迟: OpenAI (gpt-4-turbo)
├─ 生产高质量: Anthropic (claude-sonnet-4-6)
└─ 嵌入模型: text-embedding-3-small (性能/成本平衡)
```

#### 3. 分块策略调整
```python
# 长文档（技术手册）
PARENT_CHUNK_SIZE=2000
CHILD_CHUNK_SIZE=800

# 短文档（FAQ）
PARENT_CHUNK_SIZE=1000
CHILD_CHUNK_SIZE=400
```

#### 4. 重排序权衡
```python
# 精度优先
ENABLE_RERANKER=true
RERANKER_TOP_N=10

# 速度优先
ENABLE_RERANKER=false
或
RERANKER_TOP_N=3
```

---

### 安全加固

#### 1. 密钥管理
```bash
✅ 使用环境变量，不要硬编码
✅ 生产环境使用密钥管理服务 (AWS Secrets Manager, Vault)
✅ 定期轮换API密钥和数据库密码
✅ 使用哈希存储审批令牌
```

#### 2. 网络隔离
```bash
✅ Neo4j、Redis仅监听localhost
✅ 使用防火墙限制外部访问
✅ API Base URL白名单严格控制
✅ 禁用API_BASE_URL_ALLOW_PRIVATE
```

#### 3. 审计与监控
```bash
✅ 启用审计日志
✅ 定期审查管理员操作
✅ 监控异常登录行为
✅ 设置告警规则 (失败率、延迟)
```

---

### 运维最佳实践

#### 1. 文档管理
```bash
# 定期重新索引
python scripts/ingest.py

# 删除过期文档
DELETE /documents/{doc_id}

# 清理无效会话
定期清理 SESSIONS_DIR 中的旧会话文件
```

#### 2. 检索配置管理
```bash
# 测试新配置（金丝雀路由）
POST /admin/ops/canary
{
  "profile": "advanced",
  "canary_percentage": 10
}

# 确认无问题后全量切换
POST /admin/ops/profiles/advanced
{...}

# 回滚（如果有问题）
POST /admin/ops/rollback
```

#### 3. 性能基准测试
```bash
# 运行基准测试
python scripts/benchmark_pipeline.py

# 负载测试
python scripts/load_test_query.py --concurrency 10 --duration 60

# RAG评估
python scripts/eval_retrieval.py
```

#### 4. 备份策略
```bash
需要备份的内容:
├─ ./data/chroma/         # 向量数据库
├─ ./data/chunks/         # 分块存储
├─ ./data/app.db          # SQLite数据库
├─ ./data/sessions/       # 会话数据
├─ ./data/security/       # 用户和会话文件
└─ Neo4j volumes          # 图数据库卷

备份频率:
├─ 每日: 增量备份
└─ 每周: 完整备份
```

---

## 📝 项目健康度评估

### 优势 ✅
1. **架构清晰**: 模块化设计，职责分离良好
2. **文档完善**: README、CHANGELOG、API文档齐全
3. **测试覆盖**: 89个测试文件，覆盖核心功能
4. **安全设计**: RBAC、JWT、审计日志、加密存储
5. **可扩展性**: 支持多模型后端、可选依赖、配置灵活
6. **国际化**: 支持中英文，自动语言检测
7. **可观测性**: 审计日志、指标、追踪、分析仪表板
8. **异常处理**: v0.4.3实现100%覆盖

### 改进空间 ⚠️
1. **未提交变更**: 国际化功能和可视化脚本未纳入版本控制
2. **临时文件**: 多个pytest临时目录需清理
3. **文档分类**: 部分文档应移至internal_docs
4. **前端测试**: E2E测试覆盖可以扩展
5. **性能监控**: 可以集成APM工具（如Datadog、New Relic）
6. **容器化**: 后端和前端可以容器化部署
7. **CI/CD**: 可以增加自动化部署流程

### 技术债务优先级
| 优先级 | 项目 | 影响 | 工作量 |
|--------|------|------|--------|
| P0 | 提交或清理未跟踪的国际化功能 | 高 | 1-2小时 |
| P1 | 清理pytest临时目录 | 中 | 30分钟 |
| P1 | 整理可视化脚本到scripts/ | 中 | 1小时 |
| P2 | 评估垂直行业文档归档 | 低 | 1小时 |
| P2 | 扩展前端E2E测试 | 中 | 4-8小时 |
| P3 | 容器化部署配置 | 低 | 4小时 |

---

## 🎓 学习资源

### 项目文档
1. [README.md](../README.md) - 项目概述
2. [CHANGELOG.md](../CHANGELOG.md) - 版本变更
3. [docs/README.md](README.md) - 文档中心
4. [docs/VERSION_HISTORY.md](VERSION_HISTORY.md) - 完整版本历史
5. [DOCUMENTATION_POLICY.md](../DOCUMENTATION_POLICY.md) - 文档政策

### 开发指南
1. [CLAUDE.md](../CLAUDE.md) - 项目配置
2. [frontend/I18N_README.md](../frontend/I18N_README.md) - 国际化指南
3. [frontend/CSS_CONFLICT_PREVENTION.md](../frontend/CSS_CONFLICT_PREVENTION.md) - CSS规范

### 外部资源
1. [LangGraph文档](https://langchain-ai.github.io/langgraph/)
2. [LangChain文档](https://python.langchain.com/)
3. [ChromaDB文档](https://docs.trychroma.com/)
4. [Neo4j文档](https://neo4j.com/docs/)
5. [FastAPI文档](https://fastapi.tiangolo.com/)

---

## 📞 总结

### 项目评级: A-

**亮点**：
- 🏆 完善的多智能体RAG系统
- 🔒 企业级安全和权限控制
- 🇨🇳 优秀的中文NLP支持
- 📊 全面的可观测性和评估框架
- 🧪 良好的测试覆盖
- 📚 详尽的文档

**需要关注**：
- 🔄 未提交的功能需要决策（提交或清理）
- 🧹 临时文件清理
- 📦 容器化部署可以进一步完善

### 下一步行动建议

#### 立即执行 (本周)
1. 决定国际化功能是否提交
2. 清理pytest临时目录
3. 整理可视化脚本

#### 短期 (本月)
1. 完成v0.4.4版本发布
2. 扩展前端E2E测试
3. 评估垂直行业文档

#### 中期 (下季度)
1. 容器化部署配置
2. 集成APM监控工具
3. 完善CI/CD自动化部署

---

**报告生成完成**  
**作者**: Claude (Kiro)  
**日期**: 2026-06-07  
**版本**: 1.0

*本报告基于项目当前状态分析，涵盖代码库、配置、文档、测试等全方面内容。*

