# QueryMind（智询）

<p align="center">
  <img src="frontend/public/architecture_flow_diagram.jpg" alt="QueryMind System Architecture" width="800" style="border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);" />
</p>

<p align="center">
  <b>Enterprise-Grade Agentic RAG Platform with Stateful LangGraph Multi-Agent Orchestration</b><br>
  <i>企业级多智能体协同 RAG 知识引擎 · 本地优先 · 混合多跳检索 · 严谨引用验证与数据脱敏</i>
</p>

<p align="center">
  <a href="https://github.com/pocheang/querymind/releases"><img src="https://img.shields.io/badge/Release-v0.7.0.1-brightgreen.svg?style=flat-square" alt="Release"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.138+-009688.svg?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-18.3-61DAFB.svg?style=flat-square&logo=react&logoColor=black" alt="React"></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img src="https://img.shields.io/badge/LangGraph-Stateful%20Workflow-FF6F00.svg?style=flat-square" alt="LangGraph"></a>
  <a href="https://tailwindcss.com/"><img src="https://img.shields.io/badge/TailwindCSS-v4.0-38B2AC.svg?style=flat-square&logo=tailwind-css&logoColor=white" alt="TailwindCSS"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/badge/Code%20Style-Ruff-000000.svg?style=flat-square" alt="Ruff"></a>
</p>

<p align="center">
  <a href="https://github.com/pocheang/querymind/actions/workflows/ci.yml"><img src="https://github.com/pocheang/querymind/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://github.com/pocheang/querymind/actions/workflows/codeql.yml"><img src="https://github.com/pocheang/querymind/actions/workflows/codeql.yml/badge.svg?branch=main" alt="CodeQL"></a>
  <a href="https://github.com/pocheang/querymind/actions/workflows/security.yml"><img src="https://github.com/pocheang/querymind/actions/workflows/security.yml/badge.svg?branch=main" alt="Security"></a>
  <a href="https://sonarcloud.io/dashboard?id=pocheang_querymind"><img src="https://sonarcloud.io/api/project_badges/measure?project=pocheang_querymind&metric=alert_status" alt="Quality Gate"></a>
</p>

---

## 🌟 Executive Overview (项目概述)

**QueryMind（智询）** 是一个面向企业私有知识库与多源数据分析的**生产级多智能体协同 RAG（Retrieval-Augmented Generation）系统**。针对传统 RAG 普遍存在的「幻觉严重」、「检索上下文割裂」、「缺乏租户隔离与数据泄露防护」以及「复杂问题无法多跳推理」等工业界痛点，QueryMind 实现了从**确定性权限预检**、**动态意图路由**、**混合向量与知识图谱融合检索**、**受控 ReAct 工具环**到**句子级反事实验证与流式敏感数据脱敏（DLP）**的端到端可信赖链路。

系统采用 **前后端分离与本地优先（Local-First）** 架构，原生支持脱离外部云端依赖的纯本地轻量运行模式，同时具备企业级高并发、微服务拆分和分布式配置治理能力。

### 🎯 为什么在面试和技术评测中选择 QueryMind？

- 🚀 **标准 LangGraph 状态机编排**：全链路采用规范的单一权威 LangGraph 状态图，告别混乱的胶水代码，具备阶段超时降级与优雅熔断机制。
- 🛡️ **严格的数据安全与多租户隔离**：数据范围在检索执行**之前（Preflight）**即完成强制绑定，杜绝“全量检索后再做过滤”导致的高危数据越权。
- 🔍 **双路融合检索 + 知识图谱多跳推理**：密集向量与 BM25 稀疏分词检索经 RRF（Reciprocal Rank Fusion）融合，配合 BGE-Reranker-V2-M3 重排及 Neo4j 拓扑推理。融合发生在**每个 (来源, 查询) 对**的独立排名列表上，而不是先拼成一张表——后者会让第二个查询的最佳命中被罚到 `top_k + 1` 名。
- 📝 **独创引用优先与 NLI 蕴含校验**：生成的每一个论据携带实时引用锚点 `[1]`, `[2]`，结合 NLI 逻辑蕴含算法过滤幻觉，未获证据支撑的论述自动进行审慎降级对齐。
- ⚡ **按路由代码分割与全景可观测性**：基于 Vite 6 + Tailwind v4 + Zustand 切片精准订阅；入口 chunk **151.5 KB（gzip）** + 主样式 38.6 KB，其余 40 个 chunk 按路由懒加载。配套 5 维交互式架构流转图与实时 SSE 执行链路追踪面板。

---

## 🏛️ System Architecture (系统核心架构)

QueryMind 架构由上至下划分为用户交互层、智能体编排管道、混合检索引擎与持久化存储层：

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Frontend Layer (React 18 + Tailwind v4 + Zustand)          │
│   • 交互式控制台 /app    • 5重视角架构流转 /architecture    • SSE 实时执行链路面板 │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │ HTTP / REST / SSE Stream
┌────────────────────────────────────────▼────────────────────────────────────────┐
│                   FastAPI Enterprise Gateway (Python 3.11+)                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                    Canonical LangGraph Orchestration Pipeline             │  │
│  │                                                                           │  │
│  │  1. Privacy & Scope Preflight ─── 确定性租户数据范围硬隔离（Pre-retrieval）  │  │
│  │          │                                                                │  │
│  │  2. Router Agent ─────────────── 规则 + 置信度 + LLM 意图识别               │  │
│  │          │                                                                │  │
│  │  3. Bounded Planner DAG ──────── 复杂问题动态任务拆解（按需激活）            │  │
│  │          │                                                                │  │
│  │  4. Hybrid Knowledge Engine ──── 密集向量 + BM25 + Neo4j 图谱 + 企业记忆   │  │
│  │          │                                                                │  │
│  │  5. Governed Tool Runner ─────── 受控 ReAct 循环（沙箱隔离，阶段预算熔断）   │  │
│  │          │                                                                │  │
│  │  6. Synthesizer Agent ────────── 引用优先（Citation-First）流式生成         │  │
│  │          │                                                                │  │
│  │  7. Bounded Verifier ─────────── 句子级 Grounding + NLI 逻辑蕴含抗幻觉校验  │  │
│  │          │                                                                │  │
│  │  8. Output DLP Filter ────────── 逐 Chunk 敏感信息脱敏与合法引用重编号       │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌─────────────────┐            ┌───────────────────┐            ┌─────────────────┐
│ ChromaDB 0.5+   │            │ SQLite            │            │ Neo4j 5.24+     │
│ 向量嵌入 (BGE)   │            │ 用户/会话/审计/元数据│            │ 知识图谱多跳拓扑  │
└─────────────────┘            └───────────────────┘            └─────────────────┘
```

### 🧩 核心智能体组件设计理念

| 阶段组件 | 核心职责 | 工业级工程考量 |
| :--- | :--- | :--- |
| **Privacy Preflight** | 确定性权限校验与请求重写 | 检索执行前严格圈定当前用户的业务单元与数据范围，无权限直接熔断，无漏报。 |
| **Router** | 意图识别与执行流分流 | 路由是**指令而非提示**：`_knowledge_hints` 把路由翻译成它蕴含的检索源并无条件带上，避免 `graph` 路由在措辞不含关系词时静默退化成向量+BM25。系统只有一个 profile（`advanced`）。 |
| **Planner** | 复杂多步任务拆解 | 针对多实体对比或复合统计问题构建有向无环图（DAG），设定明确的任务预算上限。 |
| **Retriever** | 混合多模态与图谱检索 | 向量 + BM25 并行查询，RRF 融合后 Cross-Encoder 重排。每个来源按 `owner` **关键字参数且无默认值**接收调用者身份——漏传是 `TypeError` 而不是悄悄放宽检索范围。 |
| **Tool Runner** | 受控工具调用与环境交互 | 工具选择对检索文档盲调用（Prompt Injection 防御），具备调用频次与超时熔断。 |
| **Table SQL** | 结构化表格精确分析 | 按文档属主隔离、一表一引擎；DuckDB 关闭外部文件/网络访问，只读 SQL 校验；表格持久化到 SQLite，重启与多 worker 一致。 |
| **Synthesizer** | 引用优先文本生成 | 生成时注入 `[E1]`, `[E2]` 证据标记，并在流式传输过程中动态解析为前端锚点。 |
| **Verifier** | 抗幻觉与事实一致性校验 | 基于自然语言推理（NLI）对比生成的陈述与召回切片，证据不足时自动增加对齐免责提示。 |
| **Output DLP** | 数据防泄漏与最终过滤 | 在生成流与最终文本边界运行敏感词/正则扫描，屏蔽手机号、身份证、密钥等企业敏感资产。 |

---

## ✨ Key Highlights (关键技术亮点)

### 1. 🔍 企业级混合检索与多模态知识提取 (Hybrid & Multimodal RAG)
- **多路召回融合**：密集向量 + 基于 Jieba 分词与字符 bigram 的 BM25 匹配，经倒数排名融合（RRF）。**中文分词是 jieba 加字符 bigram**：只靠 jieba 词典时，词典外的词（如 `年假`）会被切成单字后丢弃从而完全检索不到，而 `陪产假` 会被切成 `产假`——不是漏检而是答错。加上 bigram 后语料实测 MRR 0.9062 → 0.9688。
- **嵌入取决于配置**：`local` 后端（全新 checkout 的默认值）用的是 `LocalHashEmbeddings`——blake2b 哈希分桶，**不是语义向量**，管理台会如实报告为 `degraded`。装上 `LOCAL_EMBED_MODEL`（默认 `BAAI/bge-m3`）或配置 OpenAI / Ollama 才是真正的语义检索。
- **动态重排机制**：BGE-Reranker-V2-M3 二阶段交叉注意力打分，候选窗口按提问复杂度缩放（`TOP_K` 4 起、`RERANKER_TOP_N` 5 起）；重排输出随检索宽度一起放大，否则多召回的候选只是被丢掉。
- **知识图谱协同 (Graph RAG)**：集成 Neo4j Cypher 查询，针对跨部门、跨实体多跳关联推理，自动提取子图关系补全上下文。
- **多模态流式解析**：内置 PDF 解析引擎，支持流式解析、父子分块（Parent-Child 1500/600 字符切分）、表格结构化抽取与 Tesseract OCR 离线文字识别。
- **表格与电子表格（v0.7.0.1）**：支持 Excel（`.xlsx`/`.xls`）、CSV、Word 内嵌表格；合并单元格前向填充；长表切块时每个切片都保留表头与行号范围（如 `(Rows 16-30 of 60)`），避免列错位幻觉；可通过 `querymind_table_query` 工具对表格做精确的求和、均值、分组等 SQL 分析。
- **图谱富属性与社区摘要**：实体带类型与描述，社区检测支持宏观问题的全局检索；描述与社区摘要按文档来源存储和读取。
- **可插拔联网检索**：`WEB_SEARCH_PROVIDER` 可选 DuckDuckGo / Tavily / Bing / SearXNG，支持代理、超时与重试；聊天输入框提供「联网」开关。

### 2. 🛡️ 确定性安全架构与输出合规 (Zero-Trust Security & DLP)
- **非后置的数据隔离**：传统的 RAG 往往全量召回后再过滤未授权切片，容易造成泄露。QueryMind 在检索发起时直接在底层向量数据库与 SQL 查询条件中注入 `tenant_id` 与 `data_scope`。
- **实时输出 DLP（Data Loss Prevention）**：在 SSE 字符流输出边界以滑动窗口检测敏感凭证、手机号、身份证和自定义正则规则，实时用掩码替换。
- **安全日志脱敏**：用户提问与私密文档内容通过 AST 守卫拦截，日志系统仅记录不可逆的内容指纹与耗时度量，符合金融医疗合规要求。
- **表格与图谱同样按归属隔离**：结构化表格只对文档属主（或公开文档、共享语料）可见，他人一律返回「不存在」；知识图谱的实体描述与社区摘要按来源授权，不会跨租户泄露。
- **提示词注入防护**：输入侧识别指令覆盖、越狱与系统提示词探测（按意图而非关键词判断，不误拦安全分析类正常提问）；提示词沙箱化与金丝雀令牌检测泄露；输出侧拦截外链图片外传。

### 3. 🎨 极致的前端现代化与全景可观测性 (Modern Web & Observability)
- **5 重动态视角流转图 (`PipelineFlowDiagram`)**：
  - 📖 **Story Mode**：直观展示一个用户请求从输入到回答的生命周期叙事；
  - ⚙️ **Tech Mode**：展示真实工程组件契约、毫秒级超时预算及故障降级机制；
  - 📊 **Table Mode**：结构化对照执行步骤、模型参数与降级策略；
  - 🗺️ **Blueprint Mode**：工业级系统拓扑总线全景蓝图；
  - 🕸️ **Topology Mode**：基于 ReactFlow 的实时交互式数据拓扑节点图。
- **LangGraph SSE 实时执行树面板**：在问答控制台可一键展开实时执行树，直观看到当前请求经过了哪个 Agent、消耗了多少 Token、命中了几篇切片、各阶段耗时毫秒数。
- **前端构建与样式体系**：Tailwind CSS v4（CSS-first，无配置文件）+ 精准 Zustand 切片订阅，消除流式响应下的重绘卡顿。层叠顺序在 `styles/main.css` 里**声明一次**（theme / legacy / components / design / utilities），因为未分层的规则无视特异性压过所有层。构建产物按路由分割成 40 个 chunk，入口 151.5 KB gzip。

---

## 📊 What Is Measured, and What Is Not (指标与其测量方式)

这一节按项目自己的规矩写：**每个指标都要指名道姓说出「什么在测它」，没有东西在测就写「没有」**。一个背后没有测量的数字是愿望不是主张——把它印出来比留空更糟，因为读的人会当真。这张表此前有五行属于后者，现已更正。

| 指标 (Metric) | 实测 (Observed) | 由什么测量 (Measured by) |
| :--- | :--- | :--- |
| **检索 MRR** | **0.9688** | `make eval-retrieval`：15 条双语语料 × 16 个查询，跑**真实的 `KnowledgeOrchestrator`**（BM25 单路，故无需模型即可复现）。钉死的是**每个查询的名次**而非聚合值，所以失败会指名是哪个查询；改善和回归一样让测试变红。 |
| **检索 P@5** | **0.2（理论上限）** | 同上。语料每个查询只有 1 篇相关文档，五取一就是天花板——拿它对标多标注语料常引的 0.85 是类别错误，`tests/evaluation/` 专门钉住这点以免有人从指标表里读出错误结论。 |
| **端点数量** | **157** | `tests/api/test_endpoint_census.py`，**精确**断言。变少说明某个 router 被静默丢掉，变多说明基线过期——两个方向都红。 |
| **后端行覆盖率** | **59.5%** | `scripts/check_coverage.py ratchet`，CI 双向门禁（掉了是回归，涨了是基线该更新）。 |
| **认知复杂度** | **0 个函数 > 15** | `tests/core/test_cognitive_complexity_is_bounded.py`，覆盖 `app/` 与 `scripts/` 的硬门禁。`scripts/audit/cognitive_complexity.py` 本地实现了 Sonar 的评分规则，`--validate` 能逐条复现项目全部 75 条历史 S3776 发现。 |
| **测试数量** | **2,122 后端 / 214 前端** | `pytest -q`（2,119 passed, 3 skipped）与 `vitest`（31 文件）。 |
| **入口包体积** | **151.5 KB gzip** | `npm run build` 实测：入口 chunk 441 KB 原始 / 151.5 KB gzip，主样式 142 KB / 38.6 KB gzip，其余按路由拆成 40 个懒加载 chunk。 |
| **Router 意图准确率** | **没有测量** | 项目里**不存在**标注过的路由测试集。此处曾写 99.1%，那个数字没有任何东西在测。 |
| **引用完整性** | **没有聚合测量** | 每个回答由校验级联的引用阶段**逐条强制执行**，但从未在一个查询集上打过总分。 |
| **回答接地率 / 延迟 P95** | **按请求记录，无历史聚合** | `build_ops_alerts` 读中间件写入的 `request_rows` 环形缓冲。**进程本地**：重启即空，多 worker 各看各的。跨越这个边界是时序数据库的决策，不是改这五行代码。 |

> ⚠️ **所有质量类指标描述的都是接了真实 LLM 的链路。** 全新 checkout 默认 `MODEL_BACKEND=local`，那是一个离线替身（按关键词路由、从自己 prompt 的证据段里拼答案），**回路里没有语言模型**——在它上面谈路由准确率或引用完整性没有意义。

---

## 🚀 Quick Start (快速上手指南)

为了方便面试官、架构师或开发者在 **2 分钟内开箱体验**，QueryMind 默认开启了 `MODEL_BACKEND=local` 本地离线替身模式：**无需填写 OpenAI Key，无需配置 Docker 或显卡，纯本地即可秒级启动！**

### 环境要求
- **Python 3.11+**
- **Node.js 18+**
- **Conda**（推荐用于隔离 Python 环境）

---

### 本地两步启动 (Local Development)

#### 1. 启动后端 API 服务
```bash
# 1. 创建并激活 Python 虚拟环境
conda create -n rag-local python=3.11 -y
conda activate rag-local

# 2. 安装项目依赖
pip install -e .
# 可选：Excel / CSV 表格解析与表格 SQL 分析（openpyxl、pandas、DuckDB）
pip install -e ".[office]"

# 3. 启动 FastAPI 后端服务（自动初始化 SQLite 与内置 ChromaDB）
uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```
> 💡 **管理员账号怎么来**
>
> 本项目**不内置任何默认密码**——仓库里的凭据等于每一份 checkout 里的凭据。账号按下述规则产生：
>
> - **仅当数据库里没有任何"启用中的管理员"时**，启动会自动创建一个，并把密码打到 **stderr（终端 / `docker logs`）打印一次**，只存哈希。已经有管理员的部署重启不会创建，也不会重复打印。
> - 想自己指定，就在**真实进程环境变量**里设 `ADMIN_USERNAME` / `ADMIN_PASSWORD`（密码需满足：12 位以上，含大小写、数字、特殊字符）。
>   ⚠️ 写进 `.runtime/*.env` **无效**——那个文件只会被读进 `Settings`，不会导出到进程环境，而这两个键是直接 `os.getenv` 读的。
> - 若该用户名已被一个非管理员账号占用，启动会**报错并拒绝**，不会把它提权（凭用户名撞车就提权等于按字符串提权）。换个 `ADMIN_USERNAME` 即可。
> - **已有部署 / 忘记密码**：`python scripts/create_admin.py --username <名字> --reset-password`，同样只打印一次。

#### 2. 启动前端控制台界面（新终端）
```bash
cd frontend
npm install

# 极速生产预览模式（推荐体验，毫秒级秒开）
npm run build
npm run preview

# 或启动本地热重载开发服务器
npm run dev
```

#### 3. 浏览器访问
- 🖥️ **前端交互控制台**：[http://localhost:5174](http://localhost:5174)（预览模式）或 [http://localhost:5173](http://localhost:5173)（开发模式）
- 🏛️ **多维架构可视化全景**：[http://localhost:5174/architecture](http://localhost:5174/architecture)
- 📚 **Swagger API 交互文档**：[http://localhost:8000/docs](http://localhost:8000/docs)

---

### 接入大模型 (可选)

若需要连接真实的云端模型或本地 Ollama，只需在启动前设置环境变量：

```bash
# 使用 OpenAI
export OPENAI_API_KEY="sk-..."

# 或使用 Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# 或使用本地部署的 Ollama (DeepSeek / Qwen / LLaMA)
export MODEL_BACKEND="ollama"
export OLLAMA_BASE_URL="http://localhost:11434"
```

---

### 🐳 Docker 一键部署 (Production Stack)

QueryMind 提供了生产环境标准的 Docker Compose 一键式编排体系：

```bash
# 一键拉起完整生产容器栈 (API + Frontend Nginx + Prometheus + Grafana + Neo4j)
./deploy/scripts/deploy.sh production balanced
```

---

## 🛠️ Technology Stack (技术栈选型与全貌)

```
QueryMind Technology Stack
├── Backend Core
│   ├── Framework: FastAPI 0.138+ (ASGI, 强类型 Pydantic v2 Settings)
│   ├── Workflow Engine: LangGraph 0.2+ (有状态多智能体图编排)
│   ├── LLM Ecosystem: LangChain 0.3+, Ollama SDK, OpenAI, Anthropic
│   ├── Vector Database: ChromaDB 0.5+ (轻量嵌入式 / Client-Server 模式)
│   ├── Graph Database: Neo4j 5.24+ (Cypher 图遍历，关系推理)
│   ├── Search & Tokenizer: rank-bm25, jieba, Sentence-Transformers
│   ├── Embeddings & Reranker: BGE-M3 (密集向量), BGE-Reranker-V2-M3
│   ├── Table Analytics: DuckDB (只读、关闭外部访问) / SQLite 回退
│   └── Database & Security: SQLite (本地轻量持久化), Passlib PBKDF2, PyJWT
├── Frontend Modern Web
│   ├── Core Framework: React 18.3, TypeScript 5.9, Vite 6
│   ├── Styling System: Tailwind CSS v4 (@theme, CSS 原生变量, tw-animate-css)
│   ├── State Management: Zustand (细粒度切片订阅，无冗余 re-render)
│   ├── Interactive Graph: ReactFlow 11 (拓扑流转交互), Recharts (实时度量)
│   ├── Localization: i18next (中英双语即时切换)
│   └── UI Primitives: Radix UI (@radix-ui/react-dialog, slot, dropdown)
└── Engineering & DevOps
    ├── Code Quality: Ruff (Linter & Formatter), Pre-commit (CI 内同样执行)
    ├── Testing: Pytest (后端 2,122 用例), Vitest (前端 214 用例), Prettier
    ├── CI: GitHub Actions 5 job (lint / backend 3.11+3.12 / frontend Node 20+22 / images / analysis)
    ├── Security: CodeQL (python + js-ts), pip-audit + npm audit 门禁, Trivy 镜像扫描（每周）
    ├── Static Analysis: SonarCloud Quality Gate, 认知复杂度本地门禁 (S3776, 0 超标)
    └── Observability: Prometheus Metrics (/metrics), Grafana Dashboard
```

---

## 📂 Repository Structure (项目工程目录)

```
multi_agent_rag_local_v4/
├── app/                        # FastAPI 后端应用核心
│   ├── api/                    # REST 路由层 (auth, query, sessions, admin, docs)
│   ├── orchestration/          # 统一 LangGraph 状态机编排引擎
│   │   └── langgraph/          # 权威管道图构建与执行节点
│   ├── retrievers/             # 混合检索器 (vector, bm25, rrf, reranker)
│   ├── agents/                 # 核心算法组件 (synthesizer, validation, router)
│   ├── services/               # 领域业务服务 (models, security, memory, ingestion)
│   └── core/                   # 全局配置中心 (Settings, Schema, Precedence)
├── frontend/                   # React 18 + Tailwind v4 现代化前端应用
│   ├── src/
│   │   ├── components/         # 可复用原子组件与业务复合组件
│   │   │   └── architecture/   # 核心 PipelineFlowDiagram 五重视角流转器
│   │   ├── features/           # 特性域模块 (execution-trace, memory, approval)
│   │   ├── pages/              # 路由视图 (ChatPage, ArchitecturePage, AdminPage...)
│   │   ├── stores/             # 细粒度 Zustand 状态存储
│   │   └── styles/             # Tailwind CSS v4 基础设计系统
├── config/                     # 统一配置体系 (Single Source of Truth)
│   ├── env/                    # 环境配置文件模板 (dev/prod/test)
│   ├── profiles/               # 运行时性能配置文件 (balanced/deep/fast)
│   └── observability/          # Prometheus / Grafana / Alertmanager 规则
├── deploy/                     # 生产化部署基础设施
│   ├── compose/                # 模块化 Docker Compose 文件
│   └── scripts/                # 容器健康检查与自动化部署脚本
├── docs/                       # 架构与开发文档中心
│   └── releases/               # 历史版本发布说明 (v0.7.0.1 Release Notes)
├── tests/                      # 自动化测试套件 (Pytest 单元、集成、安全回归测试)
├── pyproject.toml              # Python 构建配置与依赖锁定声明
└── CLAUDE.md                   # 架构技术规范与工程实现备忘录
```

---

## 🧪 Testing & CI (工程质量与持续集成)

```bash
# 后端：2,122 项用例（2,119 passed / 3 skipped，缺可选的 openpyxl 时跳过）
pytest -q

# 推送前用这个：把 CI 不安装的可选包（pytesseract / pdfplumber / sentence-transformers）屏蔽掉跑一遍
make test-ci

# 前端：214 项用例，31 个文件
cd frontend && npm test -- --run

# 静态检查
ruff check . && ruff format --check .
cd frontend && npm run lint && npm run type-check && npm run lint:design
npm run build && npm run lint:classes   # 这两项必须在 build 之后：它们问的是浏览器实际收到了什么

# 离线检索质量评估（无需模型、无需 Chroma / Neo4j / LLM，全新 checkout 即可跑）
make eval-retrieval
```

### CI 跑什么

三个 workflow。`ci.yml` 五个 job 并行（只有最后一个有依赖）：

| Job | 内容 |
| :--- | :--- |
| `lint` | 敏感内容闸门 + ruff。**不装项目依赖**，所以一分钟内出结果——风格问题不会再把测试结果挡在后面。 |
| `backend` | 按 lock 安装、pre-commit 全量、pytest + 覆盖率 + 覆盖率棘轮。**3.11 / 3.12 矩阵**。 |
| `frontend` | eslint、tsc、prettier、设计尺度棘轮、vitest + 覆盖率、build、死类名审计。**Node 20 / 22 矩阵**。 |
| `images` | 校验九种环境×profile 配置组合，构建两个 Dockerfile，**然后真的把它们跑起来**：两个容器上同一个网络，对着它们发真实请求，再用无头 Chromium 打开页面。 |
| `analysis` | 下载前后端两份覆盖率报告到同一个工作区，SonarCloud 扫描（当前休眠，等 `SONAR_TOKEN`）。 |

`codeql.yml` 做污点分析（python + javascript-typescript）；`security.yml` 每周跑 pip-audit / npm audit / Trivy 镜像扫描，**是门禁不是报告**——未经登记的公告直接红，已修复却仍留在豁免名单里的条目也红。

### 几条刻意的设计

- ✅ **每个门禁都被验证过「能失败」。** 一个从没红过的扫描器什么也证明不了。敏感内容闸门、死类名审计、覆盖率检查、复杂度门禁在改动时都要先种一个已知的坏样本确认它会报。
- ✅ **棘轮双向失败。** 覆盖率掉了是回归，涨了说明基线过期；端点数少了是 router 掉了，多了是基线该更新。只能涨不能收的豁免名单会从「决策记录」退化成「不做决策的方式」。
- ✅ **容器不只是构建，还要服务。** jsdom 测试、`npm run build`、`nginx -t` 全都能在一个**只会显示白屏**的部署上通过。冒烟检查断言 `/api/advanced-rag/health` 返回的是 JSON 而不是 SPA 兜底的 `index.html`——只有这一条能发现代理没接到后端。
- ✅ **Pre-commit 在 CI 里有副本。** 钩子能被 `--no-verify` 绕过，在没跑过 `pre-commit install` 的新 clone 里则根本不存在。

---

## 📜 Documentation Index (文档索引)

- 📗 **[CLAUDE.md](CLAUDE.md)**：系统底层实现细节、设计决策演进与工程规范
- 📝 **[v0.7.0.1 发布说明](docs/releases/v0.7.0.1-release-notes.md)**：最新版本——表格与 Excel/CSV、表格 SQL 分析、图谱社区、多搜索源、提示词注入防护及升级说明
- 📝 **[v0.7.0 发布说明](docs/releases/v0.7.0-release-notes.md)**：v0.7.0 LangGraph 重构与可观测性详细清单
- 📚 **[版本发布总览](docs/releases/README.md)**：历史版本演进历程与发布说明
- 🔒 **[安全合规政策](SECURITY.md)**：安全模型、漏洞披露流程与数据防护规范
- 🤝 **[贡献指南](CONTRIBUTING.md)**：代码规范、分支模型与 Pull Request 流程

---

## 👤 Author & Contact (作者与联系方式)

**Po Cheang**  
- 💼 **Profile**: Full-Stack AI Engineer / LLM & RAG Systems Architect
- 📧 **Email**: [po.cheang@gmail.com](mailto:po.cheang@gmail.com)
- 🐙 **GitHub**: [@pocheang](https://github.com/pocheang)

> 💬 **求职状态**：正在积极寻找 **AI / 大模型应用研发工程师**、**RAG 算法与全栈系统架构师** 相关的全职机会。如果您对本项目的设计思路或工程实现感兴趣，非常欢迎随时邮件或在 GitHub 上与我沟通交流！

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。欢迎 Star、Fork 与交流学习！

<p align="center">
  <b>⭐ 如果 QueryMind 对您的学习或项目有所启发，欢迎点一个 Star 给予支持！ ⭐</b>
</p>
