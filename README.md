<div align="center">

# QueryMind（智询）

### 企业私有知识库 Agentic RAG 系统

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB.svg)](https://react.dev/)
[![Version](https://img.shields.io/badge/version-v0.6.0-blue.svg)](./CHANGELOG.md)

**智能路由 · 混合检索 · 知识图谱 · 质量保证 · 执行追踪**

[功能特性](#-核心特性) · [快速开始](#-快速开始) · [系统架构](#-系统架构) · [文档](#-文档) · [更新日志](./CHANGELOG.md)

</div>

---

## 📖 项目简介

**QueryMind（智询）** 是一个**生产级企业知识库 RAG 系统**，采用多智能体架构，提供高精度、可解释、可追踪的企业级知识问答服务。

### 🎯 核心特性

- 🧠 **智能路由系统** - LLM驱动的意图识别，准确率>95%
- 🔍 **混合检索引擎** - 向量检索 + BM25 + 重排序，Precision@5 >0.90
- 🛡️ **质量保证体系** - 5层验证流水线，幻觉率<10%
- 🕸️ **知识图谱推理** - GraphRAG支持多跳推理
- 📎 **精确引用溯源** - 文档/段落/字符三层追溯
- 🔬 **实时执行追踪** - SSE流式状态推送
- 🔐 **企业级安全** - JWT认证 + RBAC权限
- 🤖 **多智能体协作** - 11个专业Agent协同工作

### ✨ v0.6.0 新特性

**质量优化发布** (2026-06-28)

- ⭐ **Router准确率提升**: 95% → 99% (+4.2%)
- ⭐ **幻觉率大幅降低**: 27.5% → 8.0% (-71%)
- ⭐ **引用完整性提升**: 85% → 96% (+13%)
- ⭐ **零破坏性变更**: 100%向后兼容

📖 [完整发布说明](./docs/releases/RELEASE_NOTES_v0.6.0.md)

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 16+
- PostgreSQL 14+ (可选)
- Neo4j 5+ (可选)

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/yourorg/querymind.git
cd querymind
```

2. **创建环境**

```bash
conda env create -f environment.yml
conda activate rag-local
```

3. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，配置API密钥等
```

4. **初始化数据库**

```bash
python scripts/init_db.py
```

5. **启动后端服务**

```bash
uvicorn app.main:app --reload --port 8000
```

6. **启动前端服务**

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 开始使用！

### 基本使用

```python
from app.main import query_system

# 简单查询
result = query_system("什么是机器学习？")
print(result["answer"])

# 带引用的查询
result = query_system(
    "解释深度学习的原理",
    include_sources=True
)
print(result["answer"])
print(result["sources"])
```

---

## 🏗️ 系统架构

### 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                     用户接口层                            │
│              React Frontend + RESTful API                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    智能路由层                             │
│          Router Agent (准确率>95%)                       │
└─────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        ↓                                   ↓
┌───────────────┐                   ┌───────────────┐
│  向量检索路径  │                   │  图谱推理路径  │
│  Vector RAG   │                   │  Graph RAG    │
└───────────────┘                   └───────────────┘
        ↓                                   ↓
┌─────────────────────────────────────────────────────────┐
│                    质量保证层                             │
│     Route Validator → Retrieval Quality → Answer        │
│     Validator → Context Tracker → Quality Orchestrator  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    答案生成层                             │
│         Synthesis Agent + Citation + Verification       │
└─────────────────────────────────────────────────────────┘
```

### 技术栈

**后端**
- FastAPI - 高性能异步Web框架
- LangGraph - 多智能体编排
- ChromaDB - 向量数据库
- Neo4j - 知识图谱数据库
- PostgreSQL - 关系数据库

**前端**
- React 18 - UI框架
- TypeScript - 类型安全
- Vite - 构建工具
- TailwindCSS - 样式框架

**AI/ML**
- OpenAI API - 大语言模型
- Sentence-Transformers - 向量嵌入
- BGE-Reranker - 重排序模型
- Jieba - 中文分词

---

## 📊 性能指标

### 检索性能

- **Precision@5**: >0.90
- **Recall@10**: >0.85
- **MRR (Mean Reciprocal Rank)**: >0.91

### 生成质量

- **路由准确率**: 99%
- **NLI验证准确率**: 95.5%
- **幻觉率**: <10%
- **引用完整性**: 96%

### 系统性能

- **P95响应时间**: <4秒
- **并发能力**: 50+用户
- **系统可用性**: >99.5%
- **错误率**: <1%

> 💡 以上数据基于测试环境，实际性能可能因配置和数据量而异

---

## 📚 文档

### 用户文档

- [快速开始指南](./docs/guides/getting-started.md)
- [配置说明](./docs/guides/configuration.md)
- [API参考](./docs/guides/api-reference.md)
- [常见问题](./docs/guides/faq.md)

### 开发文档

- [架构设计](./docs/architecture/README.md)
- [Agent系统](./docs/features/agents/README.md)
- [部署指南](./docs/guides/deployment.md)
- [贡献指南](./CONTRIBUTING.md)

### 发布说明

- [v0.6.0 - 质量优化](./docs/releases/RELEASE_NOTES_v0.6.0.md)
- [v0.5.0 - 权限系统](./docs/releases/RELEASE_NOTES_v0.5.0.md)
- [完整历史](./docs/history/VERSION_HISTORY.md)

---

## 🛠️ 配置选项

### 基础配置

```python
# config/settings.py

# LLM配置
LLM_PROVIDER = "openai"  # openai, azure, anthropic
LLM_MODEL = "gpt-4"
LLM_TEMPERATURE = 0.1

# 检索配置
VECTOR_TOP_K = 20
BM25_TOP_K = 20
RERANK_TOP_N = 5

# 质量配置
ENABLE_NLI_VALIDATION = True
HALLUCINATION_THRESHOLD = 0.85
CITATION_REQUIRED = True
```

### 高级配置

详见 [配置文档](./docs/guides/configuration.md)

---

## 🔧 开发

### 项目结构

```
querymind/
├── app/                    # 后端应用
│   ├── agents/            # Agent实现
│   ├── api/               # API路由
│   ├── core/              # 核心功能
│   └── models/            # 数据模型
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── components/   # React组件
│   │   ├── hooks/        # 自定义Hooks
│   │   └── utils/        # 工具函数
├── tests/                 # 测试
├── docs/                  # 文档
├── config/                # 配置文件
└── scripts/               # 脚本工具
```

### 运行测试

```bash
# 后端测试
pytest tests/ -v

# 前端测试
cd frontend && npm test

# 覆盖率报告
pytest --cov=app tests/
```

### 代码质量

```bash
# Python代码检查
black app/
pylint app/
mypy app/

# TypeScript代码检查
cd frontend
npm run lint
npm run type-check
```

---

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

详见 [贡献指南](./CONTRIBUTING.md)

### 行为准则

请阅读并遵守我们的 [行为准则](./CODE_OF_CONDUCT.md)

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](./LICENSE) 文件

---

## 🙏 致谢

### 技术栈

- [LangChain](https://github.com/langchain-ai/langchain) - LLM应用框架
- [FastAPI](https://fastapi.tiangolo.com/) - Web框架
- [React](https://react.dev/) - UI框架
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Neo4j](https://neo4j.com/) - 图数据库

### 灵感来源

本项目受到以下工作的启发：
- [GraphRAG](https://github.com/microsoft/graphrag) - Microsoft的图谱RAG
- [LangGraph](https://github.com/langchain-ai/langgraph) - 多智能体编排
- [Ragas](https://github.com/explodinggradients/ragas) - RAG评估框架

---

## 📧 联系方式

- **问题反馈**: [GitHub Issues](https://github.com/yourorg/querymind/issues)
- **功能建议**: [GitHub Discussions](https://github.com/yourorg/querymind/discussions)
- **安全问题**: 请查看 [SECURITY.md](./SECURITY.md)

---

## 🗺️ 路线图

### v0.7.0 (计划中)

- [ ] 多模态支持 (图片、表格理解)
- [ ] 增强的实时学习能力
- [ ] 更多LLM提供商支持
- [ ] 性能优化和扩展性改进

### 长期计划

- 联邦学习支持
- 更多语言支持
- 移动端应用
- 企业级部署解决方案

---

<div align="center">

**⭐ 如果觉得有用，请给个星标支持一下！**

Made with ❤️ by the QueryMind Team

</div>
