<div align="center">

# QueryMind（智询）

### 企业级智能问答引擎

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB.svg)](https://react.dev/)
[![Version](https://img.shields.io/badge/version-v0.5.0-blue.svg)](./docs/history/VERSION_HISTORY.md)

**多智能体协作 · 混合检索 · 知识图谱增强 · 本地部署**

[功能特性](#-核心特性) · [快速开始](#-快速开始) · [架构说明](#-系统架构) · [文档](#-文档) · [更新日志](./CHANGELOG.md)

</div>

---

## 📖 项目简介

**QueryMind（智询）** 是一个企业级智能问答引擎，专为私有知识库、内部知识助手和受控企业 AI 工作流设计。通过多智能体协作、混合检索策略和知识图谱增强，提供高质量的问答体验。

### 🎯 核心优势

- 🤖 **多智能体协作** - 基于 LangGraph 的智能路由和任务分配
- 🔍 **混合检索** - 向量检索 + BM25 + 重排序 + 知识图谱
- 🔐 **企业级安全** - RBAC 权限控制、数据隔离、审计日志
- 🌏 **多语言支持** - 中英文 NLP 优化、自动语言检测
- 📊 **实时监控** - 代理执行可视化、检索分析、性能指标
- 🚀 **本地优先** - 支持 Ollama、OpenAI、Anthropic 等多种模型

### 🖼️ 界面预览

<table>
  <tr>
    <td width="50%">
      <img src="./docs/images/screenshots/login.png" alt="登录界面">
      <p align="center"><b>登录界面</b></p>
    </td>
    <td width="50%">
      <img src="./docs/images/screenshots/chat.png" alt="聊天界面">
      <p align="center"><b>智能问答</b></p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="./docs/images/screenshots/agent-tracking.png" alt="代理追踪">
      <p align="center"><b>代理执行追踪</b></p>
    </td>
    <td width="50%">
      <img src="./docs/images/screenshots/knowledge-graph.png" alt="知识图谱">
      <p align="center"><b>知识图谱</b></p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <img src="./docs/images/screenshots/documents.png" alt="文档管理">
      <p align="center"><b>文档管理</b></p>
    </td>
    <td width="50%">
      <img src="./docs/images/screenshots/admin-console.png" alt="管理控制台">
      <p align="center"><b>管理控制台</b></p>
    </td>
  </tr>
</table>

### 🎬 功能演示

---

## ✨ 核心特性

### 🤖 智能体系统

| 智能体 | 功能 | 特点 |
|--------|------|------|
| **Router Agent** | 查询意图分析与路由 | 智能判断查询类型，选择最优执行策略 |
| **Vector RAG Agent** | 混合检索与重排序 | 向量检索 + BM25 + Reranking，多策略融合 |
| **Graph RAG Agent** | 知识图谱查询 | Neo4j 实体关系查询，多跳推理 |
| **Web Research Agent** | 网络搜索 | 本地知识不足时，自动触发网络搜索 |
| **Synthesis Agent** | 答案生成与安全检查 | 引用溯源、安全防护、答案合成 |
| **React Agent** | 推理与行动循环 | 支持复杂任务的分步推理 |

### 🔍 检索能力

- **向量检索**: ChromaDB 密集检索，支持多种嵌入模型
- **BM25 检索**: 词频倒排索引，精确关键词匹配
- **混合融合**: Reciprocal Rank Fusion (RRF) 结果融合
- **重排序**: 基于 Cross-Encoder 的相关性重排序
- **知识图谱**: Neo4j 实体关系查询和多跳推理
- **中文优化**: Jieba 分词、同义词扩展、查询预处理

### 🔐 权限与安全

- **RBAC 系统**: Viewer（只读）和 Analyst（完全访问）角色
- **数据隔离**: 用户级数据隔离，多租户支持
- **会话管理**: JWT 认证，会话隔离，自动过期
- **审计日志**: 管理员操作追踪，安全事件记录
- **权限集成**: 前后端统一的权限检查机制

### 📊 监控与分析

- **实时追踪**: 代理执行可视化，SSE 流式更新
- **检索分析**: 检索统计、性能指标、可视化仪表板
- **性能对比**: 基线系统对比，全面评估指标（Precision, Recall, F1, MRR, NDCG）
- **运行时控制**: 检索配置热更新、金丝雀路由、回滚机制

### 🌏 多语言与国际化

- **自动语言检测**: 查询和文档的智能语言识别
- **会话语言偏好**: 用户级语言设置持久化
- **中文 NLP**: Jieba 分词、中文评估指标、查询预处理
- **界面国际化**: 中英文 UI，i18next 支持

### 📄 文档处理

- **多格式支持**: PDF, 图片, 文本, Office 文档
- **OCR 识别**: Tesseract OCR，图片文字提取
- **流式处理**: 大文件流式加载，减少 70% 内存使用
- **批量提取**: 并行图表提取，提升处理效率
- **增强分块**: 智能分块策略，保持语义完整性

---

## 🏗️ 系统架构

### 技术栈

**后端**:
- FastAPI - 高性能异步 Web 框架
- LangGraph - 多智能体工作流编排
- LangChain - LLM 应用开发框架
- ChromaDB - 向量数据库
- Neo4j - 知识图谱数据库（可选）
- Redis - 缓存和会话存储（可选）

**前端**:
- React 18 + TypeScript
- Vite - 快速构建工具
- Ant Design - UI 组件库
- i18next - 国际化

**模型支持**:
- Ollama（本地部署）
- OpenAI（GPT-4, GPT-3.5）
- Anthropic（Claude）

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (React)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 聊天界面  │  │ 文档管理  │  │ 管理控制台 │  │ 分析仪表板 │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API / SSE
┌────────────────────────▼────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LangGraph Workflow                         │ │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐   │ │
│  │  │Router│→ │Vector│→ │Graph │→ │Web   │→ │Synth │   │ │
│  │  │Agent │  │Agent │  │Agent │  │Agent │  │Agent │   │ │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Auth     │  │ RBAC     │  │ Caching  │  │ Monitoring│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
┌───▼────┐          ┌───▼────┐          ┌───▼────┐
│ChromaDB│          │Neo4j   │          │Redis   │
│向量库   │          │图数据库 │          │缓存     │
└────────┘          └────────┘          └────────┘
```

### 请求流程

1. **认证**: 用户通过 JWT 认证，启动或恢复会话
2. **路由**: Router Agent 分析查询意图，确定执行策略
3. **检索**: Vector/Graph/Web Agent 并行或串行执行检索
4. **融合**: 混合检索结果融合和重排序
5. **生成**: Synthesis Agent 生成答案，添加引用和安全检查
6. **流式返回**: 前端接收 SSE 流式输出或完整响应

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Conda（推荐）或 venv

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/pocheang/querymind.git
cd querymind
```

2. **后端安装**

```bash
# 创建虚拟环境
conda create -n querymind python=3.11
conda activate querymind

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置模型 API Key
```

3. **前端安装**

```bash
cd frontend
npm install
npm run build
```

4. **启动服务**

```bash
# 后端（开发模式）
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# 前端（开发模式）
cd frontend
npm run dev
```

5. **访问应用**

打开浏览器访问: http://localhost:5173

默认管理员账号: `admin` / 密码在首次启动时生成

### Docker 部署（推荐）

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 📚 文档

### 用户文档
- [快速入门指南](./docs/guides/QUICKSTART.md)
- [用户手册](./docs/guides/USER_GUIDE.md)
- [配置说明](./docs/guides/CONFIGURATION.md)

### 开发文档
- [架构设计](./docs/architecture/ARCHITECTURE.md)
- [API 文档](./docs/api/API_REFERENCE.md)
- [开发指南](./docs/development/DEVELOPMENT_GUIDE.md)
- [贡献指南](./CONTRIBUTING.md)

### 版本信息
- [更新日志](./CHANGELOG.md)
- [版本历史](./docs/history/VERSION_HISTORY.md)
- [发布说明](./docs/releases/)

---

## 🔧 配置说明

### 环境变量

关键配置项（`.env` 文件）:

```bash
# 模型配置
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4

# 数据库配置
CHROMA_PERSIST_DIR=./data/chroma
NEO4J_URI=bolt://localhost:7687

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379

# 安全配置
SECRET_KEY=your-secret-key
JWT_EXPIRE_MINUTES=1440

# 服务配置
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

### 模型支持

**本地模型（Ollama）**:
```bash
# 安装 Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 下载模型
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 配置 .env
DEFAULT_MODEL_PROVIDER=ollama
DEFAULT_MODEL_NAME=qwen2.5:7b
```

**云端模型**:
- OpenAI: GPT-4, GPT-3.5-Turbo
- Anthropic: Claude 3 Opus, Sonnet, Haiku

---

## 📊 功能对比

| 功能 | QueryMind | 传统 RAG | ChatGPT |
|------|-----------|----------|---------|
| 多智能体协作 | ✅ | ❌ | ❌ |
| 混合检索 | ✅ | 部分 | ❌ |
| 知识图谱 | ✅ | ❌ | ❌ |
| 本地部署 | ✅ | ✅ | ❌ |
| 权限控制 | ✅ | 部分 | ❌ |
| 数据隔离 | ✅ | ❌ | ❌ |
| 中文优化 | ✅ | 部分 | ✅ |
| 实时监控 | ✅ | ❌ | ❌ |
| 可扩展性 | ✅ | 部分 | ❌ |

---

## 🤝 贡献

欢迎贡献！请阅读 [贡献指南](./CONTRIBUTING.md) 了解详情。

### 开发流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE) 文件

---

## 🙏 致谢

感谢以下开源项目:
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 工作流编排
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库
- [FastAPI](https://github.com/tiangolo/fastapi) - Web 框架
- [React](https://github.com/facebook/react) - 前端框架

---

## 📞 联系方式

- 项目主页: https://github.com/pocheang/querymind
- 问题反馈: https://github.com/pocheang/querymind/issues
- 讨论区: https://github.com/pocheang/querymind/discussions

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个星标支持！**

Made with ❤️ by QueryMind Team

</div>
