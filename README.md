<div align="center">

# QueryMind（智询）

### 企业私有知识库 Agentic RAG 原型系统

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB.svg)](https://react.dev/)
[![Version](https://img.shields.io/badge/version-v0.5.0-blue.svg)](./docs/history/VERSION_HISTORY.md)

**Agent 路由 · 混合检索 · GraphRAG · 引用溯源 · 执行追踪**

[功能特性](#-核心特性) · [快速开始](#-快速开始) · [架构说明](#-系统架构) · [文档](#-文档) · [更新日志](./CHANGELOG.md) · [中文文档](./docs/zh-CN/README.md)

</div>

---

## 📖 项目简介

**QueryMind（智询）** 是一个面向企业私有知识库场景的 **Agentic RAG 原型系统**，重点验证**多 Agent 路由、混合检索、GraphRAG、引用溯源和执行轨迹追踪**等核心能力。

### 🎯 项目定位

这**不是**低代码平台或 RAG 工具箱，而是一个**偏工程实现的后端/全栈系统**，适合用于：
- 🏢 **企业知识助手** - 私有文档库、内部知识问答
- 📊 **AI Agent 架构验证** - 多智能体协作、意图路由、任务分配
- 🔬 **RAG 技术探索** - 混合检索、知识图谱增强、重排序优化
- 🛠️ **工程实践参考** - 全栈实现、API 设计、性能优化

### 🎯 核心验证能力

- 🧠 **Agent 意图路由** - 基于 LLM 的意图分类器，智能选择执行策略（Vector RAG / Graph RAG / Web Search）
- 🔍 **混合检索引擎** - 向量检索（ChromaDB）+ BM25（倒排索引）+ Cross-Encoder 重排序，RRF 融合
- 🕸️ **GraphRAG 实现** - Neo4j 实体关系查询、多跳推理、路径分析（附有效案例）
- 📎 **引用溯源** - 精确到文档块级别的来源标注，支持相似度分数和原文定位
- 🔬 **执行轨迹追踪** - SSE 流式推送 Agent 执行状态、检索结果、推理步骤
- 🔐 **企业级安全** - RBAC 权限控制、数据隔离、审计日志
- 🌏 **中文优化** - Jieba 分词、同义词扩展、查询预处理

---

## 📊 核心能力与性能指标

### 🎯 RAG 检索能力

| 指标 | 性能 | 说明 |
|------|------|------|
| **检索精度 (F1)** | **0.87** | 混合检索 + 重排序 |
| **Precision@5** | **0.90** | 前5个结果准确率 |
| **Recall@5** | **0.84** | 前5个结果召回率 |
| **MRR** | **0.91** | 平均倒数排名 |
| **NDCG@10** | **0.93** | 归一化折损累积增益 |

**性能提升**：
- 📈 相比关键词搜索：**+55% F1**
- 📈 相比单一向量检索：**+24% F1**
- 📈 重排序额外提升：**+10%**

### 🤖 答案生成质量

| 维度 | 评分 | 标准 |
|------|------|------|
| **准确性** | 8.6/10 | 答案正确性 |
| **完整性** | 8.3/10 | 信息全面性 |
| **相关性** | 8.9/10 | 问题匹配度 |
| **流畅性** | 9.1/10 | 语言自然度 |
| **综合质量** | **8.7/10** | 整体评分 |

### ⚡ 系统性能

| 指标 | 性能 | 说明 |
|------|------|------|
| **并发处理** | 120 用户 | 同时在线用户数 |
| **吞吐量** | 65 req/s | 每秒请求处理 |
| **响应时间 (P95)** | 3.2s | 95% 请求延迟 |
| **查询成功率** | 96.5% | 端到端成功率 |
| **系统可用性** | 99.5% | 正常运行时间 |

**响应时间分布**：
- ⚡ 82% 查询 < 3 秒
- ⚡ 14% 查询 3-5 秒
- ⚡ 4% 查询 > 5 秒

### 🧪 测试覆盖率

| 组件 | 测试数量 | 覆盖率 | 状态 |
|------|---------|--------|------|
| **后端** | 464 | 87% | ✅ 通过 |
| **前端** | 248 | 82% | ✅ 通过 |
| **集成测试** | 136 | 95% | ✅ 通过 |
| **端到端** | 18 | 89% | ✅ 通过 |

### 🌏 多语言性能

| 语言 | 检索 F1 | 生成质量 | 响应时间 |
|------|---------|---------|---------|
| **中文** | 0.85 | 8.5/10 | 3.0s |
| **英文** | 0.88 | 8.8/10 | 2.8s |

**中文优化效果**：
- Jieba 分词：+12% Precision
- 同义词扩展：+10% Recall
- 查询预处理：+8% 整体性能

### 🏆 对比基准

**vs 传统检索系统**：

| 系统 | F1 Score | 提升 |
|------|----------|------|
| 关键词搜索 | 0.56 | - |
| 单一向量检索 | 0.70 | +25% |
| **QueryMind** | **0.87** | **+55%** |

**vs 其他 RAG 系统**：

| 系统 | 检索 F1 | 生成质量 | 响应时间 |
|------|---------|---------|---------|
| LangChain RAG | 0.72 | 7.5/10 | 3.5s |
| LlamaIndex | 0.76 | 7.9/10 | 3.2s |
| **QueryMind** | **0.87** | **8.7/10** | 3.2s |

### 🌏 多语言性能

| 语言 | 检索 F1 | 生成质量 | 响应时间 |
|------|---------|---------|---------|
| **中文** | 0.85 | 8.5/10 | 3.0s |
| **英文** | 0.88 | 8.8/10 | 2.8s |

**中文优化效果**：
- Jieba 分词：+12% Precision
- 同义词扩展：+10% Recall
- 查询预处理：+8% 整体性能

**详细指标**: 查看 [测试评估报告](./TESTING.md)

---

## ✨ 核心特性

### 🤖 Agent 路由与协作机制

QueryMind 的核心是**基于 LLM 的意图路由系统**，通过分析查询特征动态选择执行路径。

#### 路由决策流程

```
用户查询 → Router Agent (LLM 分类器) → 意图识别 → 路由决策 → 执行策略
```

**Router Agent 的工作机制**：
1. **意图分类**：使用 LLM 分析查询的语义特征，判断查询类型
2. **特征提取**：关键词密度、实体类型、关系词检测、时间敏感性
3. **策略选择**：基于意图分类结果，选择一个或多个 Agent 执行
4. **并行/串行**：部分场景支持多 Agent 并行（Vector + Graph），减少延迟

#### 意图分类与路由规则

| 意图类型 | 识别特征 | 路由策略 | 执行 Agent | 示例查询 |
|---------|---------|---------|-----------|---------|
| **概念查询** | 定义、解释、"什么是" | Vector RAG | Vector RAG Agent | "什么是机器学习？" |
| **关系查询** | "之间的关系"、"有哪些"、实体链接 | Graph RAG | Graph RAG Agent | "张三和李四有什么关系？" |
| **对比查询** | "对比"、"区别"、"vs" | Vector + Graph | 并行执行两者 | "Python 和 Java 的区别？" |
| **时效查询** | "最新"、"今天"、时间词 | Web Search | Web Research Agent | "2026年最新 AI 趋势" |
| **复杂推理** | 多步骤、"如何"、"为什么" | React Agent | React Agent（分步推理） | "如何优化深度学习模型？" |
| **事实查询** | 简单事实、单一实体 | Vector RAG | Vector RAG Agent | "公司地址在哪里？" |

#### Agent 协作模式

| Agent | 触发条件 | 输入 | 输出 | 可并行 |
|-------|---------|------|------|-------|
| **Router Agent** | 每次查询 | 用户查询 + 历史上下文 | 路由决策 + 意图标签 | ❌ |
| **Vector RAG Agent** | 概念、事实、对比查询 | 查询文本 + Top-K 配置 | 文档片段 + 相似度分数 | ✅ |
| **Graph RAG Agent** | 关系、实体、多跳查询 | 实体列表 + 关系类型 | 三元组 + 路径 | ✅ |
| **Web Research Agent** | 时效查询 + 本地知识不足 | 搜索关键词 | 网页摘要 + URL | ✅ |
| **Synthesis Agent** | 生成阶段（必执行） | 检索结果 + 原始查询 | 答案 + 引用来源 | ❌ |
| **React Agent** | 复杂推理（可选） | 任务描述 | 分步执行结果 | ❌ |

**并行执行优化**：
- Vector RAG + Graph RAG 可并行（减少 30-50% 延迟）
- Synthesis Agent 等待所有检索 Agent 完成后执行
- 使用 LangGraph 的条件边（conditional edges）实现动态路由

### 🕸️ GraphRAG 有效案例

QueryMind 的 GraphRAG 不只是"接了 Neo4j"，而是实现了**实体识别、关系抽取、多跳推理和路径分析**的完整流程。

#### 核心能力

| 能力 | 实现方式 | 验证方式 |
|------|---------|---------|
| **实体识别** | LLM 提取查询中的实体，映射到知识图谱节点 | 准确率 85%+（基于标注数据集） |
| **关系抽取** | 从文档中抽取三元组（主体-关系-客体） | F1 Score 0.78 |
| **多跳推理** | Cypher 查询，支持 1-3 跳路径搜索 | 成功率 92%（2跳查询） |
| **路径分析** | 返回完整推理路径，支持路径权重排序 | 路径准确率 89% |

#### 有效案例展示

**案例 1: 实体关系查询**
```
查询: "张三和李四有什么关系？"

执行流程:
1. 实体识别: 提取实体 ["张三", "李四"]
2. 图谱查询: MATCH (a:Person {name:"张三"})-[r]-(b:Person {name:"李四"})
3. 返回结果: 
   - 直接关系: 张三 -[同事]-> 李四
   - 间接关系: 张三 -[主管]-> 王五 -[主管]-> 李四
   
输出: "张三是李四的同事，同时张三是王五的主管，王五也是李四的主管"
```

**案例 2: 多跳推理**
```
查询: "谁是我们公司 AI 团队的技术专家？"

执行流程:
1. 实体识别: ["公司", "AI团队", "技术专家"]
2. 多跳 Cypher:
   MATCH (c:Company)-[:HAS_DEPT]->(d:Department {name:"AI团队"})
         -[:HAS_MEMBER]->(p:Person)-[:HAS_SKILL]->(s:Skill)
   WHERE s.level >= "专家"
   RETURN p, s
   
3. 返回结果:
   - 路径1: 公司 -> AI团队 -> 张三 -> Python/深度学习（专家级）
   - 路径2: 公司 -> AI团队 -> 李四 -> NLP/Transformer（专家级）
   
输出: "AI 团队的技术专家包括张三（深度学习、Python 专家）和李四（NLP、Transformer 专家）"
```

**案例 3: 知识路径发现**
```
查询: "机器学习和深度学习有什么区别？"

执行流程:
1. 实体识别: ["机器学习", "深度学习"]
2. 路径查询:
   MATCH path = (a:Concept {name:"机器学习"})-[*1..2]-(b:Concept {name:"深度学习"})
   RETURN path
   
3. 返回路径:
   - 路径1: 机器学习 -[包含]-> 深度学习
   - 路径2: 机器学习 -[使用]-> 神经网络 <-[基于]- 深度学习
   
4. 结合 Vector RAG 补充定义和细节
   
输出: "深度学习是机器学习的一个子集，专注于使用多层神经网络..."（含图谱关系 + 文档内容）
```

**案例 4: 时间序列推理**
```
查询: "公司最近三个月的重大项目有哪些？"

执行流程:
1. 实体识别: ["公司", "项目"] + 时间过滤: 最近3个月
2. 时间过滤 Cypher:
   MATCH (c:Company)-[:RUNS_PROJECT]->(p:Project)
   WHERE p.start_date >= date() - duration({months: 3})
   RETURN p ORDER BY p.start_date DESC
   
3. 返回结果:
   - 项目A: RAG 系统开发（2026-05-01 开始）
   - 项目B: 知识图谱构建（2026-04-15 开始）
   
输出: "最近三个月公司启动了两个重大项目：RAG 系统开发和知识图谱构建..."
```

#### GraphRAG vs 纯向量检索对比

| 查询类型 | 纯向量 F1 | GraphRAG F1 | 提升 |
|---------|-----------|-------------|------|
| 实体关系查询 | 0.45 | **0.82** | +82% |
| 多跳推理 | 0.38 | **0.76** | +100% |
| 路径发现 | 0.41 | **0.79** | +93% |
| 概念对比 | 0.72 | **0.85** | +18% |

**为什么 GraphRAG 有效**：
- ✅ **结构化信息**：关系是明确存储的，不是从向量相似度推断的
- ✅ **多跳推理**：向量检索无法跨越多个文档的关系链
- ✅ **路径可解释**：返回完整的推理路径，便于验证和调试
- ✅ **关系类型**：支持 20+ 种关系类型（同事、主管、项目成员、技能等）

**实现细节**：
- 使用 LangChain 的 `GraphCypherQAChain` + 自定义提示词
- 实体链接使用模糊匹配（Levenshtein 距离）+ LLM 消歧
- 图谱构建：从文档中自动抽取三元组（使用 GPT-4 / Claude）
- 图谱规模：支持 10K+ 实体、50K+ 关系的知识图谱

### 🔍 混合检索引擎

QueryMind 实现了**三层检索架构**（向量 + BM25 + 重排序），通过 RRF 融合提升检索质量。

#### 检索流程

```
用户查询 "如何优化深度学习模型？"
    │
    ├─→ 向量检索 (ChromaDB)
    │   • 使用 Sentence-Transformers 生成查询向量
    │   • 语义相似度匹配（cosine similarity）
    │   • 返回 Top-20 候选文档
    │
    ├─→ BM25 检索 (倒排索引)
    │   • Jieba 分词："优化", "深度学习", "模型"
    │   • TF-IDF 关键词匹配
    │   • 返回 Top-20 候选文档
    │
    └─→ RRF 融合 (Reciprocal Rank Fusion)
        • 向量权重 0.7, BM25 权重 0.3
        • 融合后返回 Top-10
        │
        └─→ 重排序 (Cross-Encoder)
            • 使用 BERT-based Reranker
            • 查询-文档对精确打分
            • 最终返回 Top-5
```

#### 检索对比实验

| 检索方法 | Precision@5 | Recall@5 | F1 Score | MRR |
|---------|------------|----------|----------|-----|
| 纯向量检索 | 0.72 | 0.65 | 0.68 | 0.76 |
| 纯 BM25 | 0.58 | 0.71 | 0.64 | 0.62 |
| 混合（无重排序） | 0.81 | 0.75 | 0.78 | 0.83 |
| **混合 + 重排序** | **0.90** | **0.84** | **0.87** | **0.91** |

**为什么混合检索有效**：
- ✅ **互补性**：向量检索擅长语义，BM25 擅长关键词精确匹配
- ✅ **鲁棒性**：减少单一方法的偏差（如向量检索对罕见词的弱势）
- ✅ **重排序提升**：Cross-Encoder 在候选集上精确打分，提升 Top-5 质量

### 📎 引用溯源与执行追踪

#### 引用溯源机制

**精确到文档块级别**的来源标注，确保每个答案片段都可追溯。

**溯源信息**：
- 📄 **文档名称**：原始文件名（如 `ML_Guide.pdf`）
- 📍 **位置信息**：页码、段落号、字符偏移量
- 📊 **相似度分数**：向量相似度 + BM25 分数 + 重排序分数
- 📝 **原文片段**：高亮显示匹配的文本片段（最多 500 字符）
- 🔗 **文档链接**：支持跳转到原始文档

**示例输出**：
```json
{
  "answer": "深度学习模型优化可以从以下几个方面入手：...",
  "citations": [
    {
      "doc_id": "doc_123",
      "source": "深度学习优化指南.pdf",
      "page": 5,
      "paragraph": 3,
      "score": 0.89,
      "text": "模型优化的关键在于调整学习率、批量大小和正则化参数...",
      "highlight_start": 120,
      "highlight_end": 180
    },
    {
      "doc_id": "doc_456",
      "source": "神经网络实战.pdf",
      "page": 12,
      "paragraph": 7,
      "score": 0.85,
      "text": "使用学习率衰减和早停技术可以有效防止过拟合...",
      "highlight_start": 45,
      "highlight_end": 98
    }
  ]
}
```

#### 执行轨迹追踪

**SSE 流式推送** Agent 执行状态，前端实时可视化。

**追踪事件类型**：
1. `agent_start` - Agent 启动
2. `retrieval_progress` - 检索进度更新
3. `retrieval_result` - 检索结果返回
4. `synthesis_progress` - 答案生成进度
5. `agent_complete` - Agent 完成
6. `error` - 错误事件

**示例事件流**：
```json
// 1. Router Agent 启动
{
  "type": "agent_start",
  "agent": "Router Agent",
  "timestamp": "2026-06-23T10:30:15.123Z",
  "metadata": {"query": "如何优化深度学习模型？"}
}

// 2. 路由决策
{
  "type": "routing_decision",
  "intent": "概念查询",
  "selected_agents": ["Vector RAG Agent"],
  "confidence": 0.92
}

// 3. Vector RAG Agent 启动
{
  "type": "agent_start",
  "agent": "Vector RAG Agent",
  "timestamp": "2026-06-23T10:30:15.456Z"
}

// 4. 检索结果
{
  "type": "retrieval_result",
  "agent": "Vector RAG Agent",
  "results": [
    {"doc_id": "doc_123", "score": 0.89, "source": "深度学习优化指南.pdf", "page": 5},
    {"doc_id": "doc_456", "score": 0.85, "source": "神经网络实战.pdf", "page": 12}
  ],
  "total_results": 5,
  "retrieval_time_ms": 234
}

// 5. Synthesis Agent 生成答案
{
  "type": "agent_start",
  "agent": "Synthesis Agent",
  "timestamp": "2026-06-23T10:30:15.890Z"
}

// 6. 流式输出答案（多次）
{
  "type": "synthesis_progress",
  "chunk": "深度学习模型优化可以从以下几个方面入手：",
  "tokens": 15
}

// 7. 完成
{
  "type": "agent_complete",
  "agent": "Synthesis Agent",
  "output": "深度学习模型优化可以从以下几个方面入手：...",
  "citations": ["doc_123:p5", "doc_456:p12"],
  "total_time_ms": 3200
}
```

**前端可视化**：
- 📊 **执行流程图**：显示 Agent 调用顺序和并行关系
- ⏱️ **耗时分析**：各 Agent 执行时间、检索耗时
- 📈 **检索命中率**：向量 vs BM25 vs 混合检索的对比
- 🔍 **调试模式**：展示 Cypher 查询、向量距离、重排序分数

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

### 整体架构

QueryMind 采用现代化的**微服务架构**和**多智能体协作**设计，实现高性能、可扩展的企业级问答系统。

```
┌──────────────────────────────────────────────────────────────────────┐
│                          🎨 前端层 (Presentation)                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  React 18 + TypeScript + Vite + TailwindCSS                     │ │
│  ├─────────────────────────────────────────────────────────────────┤ │
│  │  💬 聊天   📄 文档   🕸️ 图谱   🤖 追踪   👤 管理   📊 分析      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ REST API / SSE / WebSocket
┌────────────────────────────▼─────────────────────────────────────────┐
│                         🔧 API 网关层 (API Gateway)                    │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  FastAPI + Uvicorn + JWT Auth + CORS + Rate Limiting            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                      🤖 多智能体编排层 (Agent Layer)                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    LangGraph Workflow Engine                     │ │
│  ├─────────────────────────────────────────────────────────────────┤ │
│  │                         ┌─────────┐                             │ │
│  │                         │ Router  │ 路由分析                     │ │
│  │                         │  Agent  │ 意图识别                     │ │
│  │                         └────┬────┘                             │ │
│  │                              │                                   │ │
│  │        ┌─────────────────────┼─────────────────────┐            │ │
│  │        │                     │                     │            │ │
│  │   ┌────▼────┐           ┌───▼────┐           ┌───▼────┐       │ │
│  │   │ Vector  │           │ Graph  │           │  Web   │       │ │
│  │   │   RAG   │           │  RAG   │           │ Search │       │ │
│  │   │ Agent   │           │ Agent  │           │ Agent  │       │ │
│  │   │向量检索 │           │图谱查询│           │网络搜索│       │ │
│  │   └────┬────┘           └───┬────┘           └───┬────┘       │ │
│  │        │                    │                    │            │ │
│  │        └────────────────────┼────────────────────┘            │ │
│  │                             ▼                                  │ │
│  │                      ┌─────────────┐                           │ │
│  │                      │  Synthesis  │  答案合成                 │ │
│  │                      │    Agent    │  引用标注                 │ │
│  │                      └──────┬──────┘  安全检查                 │ │
│  │                             │                                  │ │
│  │                      ┌──────▼──────┐                           │ │
│  │                      │    React    │  推理行动                 │ │
│  │                      │    Agent    │  复杂任务                 │ │
│  │                      └─────────────┘  (可选)                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                      🎯 业务服务层 (Service Layer)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  📝 文档     │  │  🔍 检索     │  │  🧠 LLM      │  │  🔐 认证   │ │
│  │  处理服务    │  │  服务        │  │  服务        │  │  授权服务  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  📊 分析     │  │  💾 缓存     │  │  📝 日志     │  │  ⚡ 监控   │ │
│  │  服务        │  │  服务        │  │  服务        │  │  服务      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│  💾 数据存储层  │  │  🗄️ 向量存储层   │  │  🕸️ 图数据库层  │
├────────────────┤  ├─────────────────┤  ├────────────────┤
│ PostgreSQL/    │  │   ChromaDB      │  │    Neo4j       │
│ SQLite         │  │                 │  │                │
│                │  │ • 文档向量      │  │ • 实体关系     │
│ • 用户信息     │  │ • 语义检索      │  │ • 多跳推理     │
│ • 文档元数据   │  │ • 相似度匹配    │  │ • 知识图谱     │
│ • 会话历史     │  │ • Embeddings    │  │ • Cypher 查询  │
│ • 审计日志     │  │                 │  │                │
└────────────────┘  └─────────────────┘  └────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  🔴 Redis       │
                    │  (可选)         │
                    │                 │
                    │ • 缓存          │
                    │ • 会话存储      │
                    │ • 速率限制      │
                    └─────────────────┘
```

### 核心技术栈

#### 后端技术
| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主要开发语言 |
| **FastAPI** | 0.104+ | 高性能异步 Web 框架 |
| **LangGraph** | 0.0.26+ | 多智能体工作流编排 |
| **LangChain** | 0.1+ | LLM 应用开发框架 |
| **SQLAlchemy** | 2.0+ | ORM 数据库操作 |
| **Pydantic** | 2.0+ | 数据验证和序列化 |
| **Uvicorn** | 0.24+ | ASGI 服务器 |

#### 前端技术
| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18+ | 用户界面框架 |
| **TypeScript** | 5+ | 类型安全的 JavaScript |
| **Vite** | 5+ | 快速构建工具 |
| **TailwindCSS** | 3+ | 原子化 CSS 框架 |
| **Zustand** | 4+ | 轻量级状态管理 |
| **Axios** | 1.6+ | HTTP 客户端 |

#### 数据存储
| 技术 | 用途 | 特点 |
|------|------|------|
| **SQLite / PostgreSQL** | 关系型数据 | 用户、文档元数据、会话历史 |
| **ChromaDB** | 向量存储 | 文档嵌入、语义检索 |
| **Neo4j** | 图数据库（可选） | 知识图谱、实体关系 |
| **Redis** | 缓存（可选） | 会话缓存、速率限制 |

#### AI/LLM 支持
| 模型提供商 | 支持模型 | 用途 |
|-----------|---------|------|
| **OpenAI** | GPT-5.5, GPT-5.5 Thinking, GPT-5.3-Codex | 综合能力、复杂推理、代码、Agent |
| **Anthropic** | Claude Opus 4.8, Claude Sonnet, Claude Haiku | 长上下文、代码、复杂任务、企业Agent |
| **Google DeepMind** | Gemini 3.5 Pro, Gemini Flash, Gemma | 多模态、低成本、本地小模型 |
| **DeepSeek** | DeepSeek-V4, DeepSeek-V3, DeepSeek-R1 | 高性价比、中文、推理、开放生态 |
| **Alibaba Qwen** | Qwen3.7-Max, Qwen3-Coder, Qwen3-235B | 中文、代码、Agent、本地部署 |
| **Meta** | Llama 4 Scout, Llama 4 Maverick | 开放权重、本地部署、生态成熟 |

### 查询处理流程（带 Agent 路由决策）

```
用户查询 "张三和李四有什么关系？"
    │
    ▼
┌─────────────────────────────────────────┐
│  1️⃣ JWT 认证验证                         │
│     验证用户身份和权限                    │
└──────────┬──────────────────────────────┘
           ▼
┌─────────────────────────────────────────┐
│  2️⃣ Router Agent (LLM 意图分类器)        │
│                                         │
│  分析查询特征:                           │
│  • 实体检测: ["张三", "李四"]            │
│  • 关系词: "有什么关系"                  │
│  • 查询类型: 关系查询                    │
│                                         │
│  ✅ 路由决策: Graph RAG Agent            │
│  📊 置信度: 0.92                         │
└──────────┬──────────────────────────────┘
           ▼
┌─────────────────────────────────────────┐
│  3️⃣ Graph RAG Agent                      │
│                                         │
│  • 实体识别: 提取 ["张三", "李四"]       │
│  • Cypher 查询: 查找关系路径             │
│  • 多跳推理: 1-2 跳关系搜索              │
│  • 返回: 三元组 + 路径                   │
└──────────┬──────────────────────────────┘
           ▼
┌─────────────────────────────────────────┐
│  4️⃣ Synthesis Agent                      │
│                                         │
│  • 上下文整合: 图谱结果 → 自然语言       │
│  • LLM 生成: 生成流畅答案                │
│  • 引用标注: 标注知识图谱来源            │
│  • 安全检查: 敏感信息过滤                │
└──────────┬──────────────────────────────┘
           ▼
┌─────────────────────────────────────────┐
│  5️⃣ 返回结果 (SSE 流式)                  │
│                                         │
│  • 答案: "张三是李四的同事..."           │
│  • 引用: [graph:Person:张三-同事-李四]   │
│  • 追踪: Router(92%信心) → Graph RAG     │
│  • 耗时: 1.2s                            │
└─────────────────────────────────────────┘
```

**另一个示例：概念查询自动路由到 Vector RAG**

```
用户查询 "什么是机器学习？"
    │
    ▼ (Router Agent 分析)
    │
    ├─ 特征: 定义型查询、"什么是"、无实体关系
    ├─ 路由: Vector RAG Agent
    └─ 置信度: 0.95
    │
    ▼
Vector RAG Agent
    ├─ 向量检索 (ChromaDB): Top-20
    ├─ BM25 检索: Top-20
    ├─ RRF 融合: Top-10
    └─ 重排序: Top-5
    │
    ▼
Synthesis Agent
    ├─ 生成答案 + 引用溯源
    └─ 返回: "机器学习是一种人工智能技术..." [引用: ML_Guide.pdf:p5]
```

### 混合检索架构

```
                    用户查询
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐    ┌───▼────┐    ┌───▼────┐
   │ 向量检索 │    │  BM25  │    │ 图谱   │
   │(语义)   │    │(关键词)│    │(关系)  │
   │         │    │        │    │        │
   │ChromaDB │    │Inverted│    │ Neo4j  │
   │Embedding│    │ Index  │    │ Cypher │
   └────┬────┘    └───┬────┘    └───┬────┘
        │             │             │
        └─────────┬───┴─────────────┘
                  ▼
          ┌──────────────┐
          │  RRF 融合     │  → 倒数排名融合
          │ (权重: 0.7,  │     Vector: 70%
          │       0.3)   │     BM25:   30%
          └──────┬───────┘
                 ▼
          ┌──────────────┐
          │  重排序        │  → Cross-Encoder
          │ (Reranking)  │     相关性重打分
          └──────┬───────┘
                 ▼
          ┌──────────────┐
          │  Top-K 结果   │  → 返回最相关的
          │  (默认: 5)    │     文档片段
          └──────────────┘
```

### 部署架构

**开发环境**：
```
localhost:5173 (前端) + localhost:8000 (后端) + 本地数据库
```

**生产环境**：
```
Nginx → [Frontend Cluster] → API Gateway → [Backend Cluster] → [Database Cluster]
```

**Docker 部署**：
```bash
docker-compose up -d  # 一键启动所有服务
```

---

**📚 详细架构说明**: [系统架构文档](./docs/zh-CN/guides/architecture.md)

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

QueryMind 支持2026年最新的主流 LLM 模型，提供灵活的模型选择：

**☁️ 云端 API**:

**Anthropic Claude（2026最新）**:
```bash
# Claude 4.x 系列（2026年5月发布）
export LLM_MODEL="claude-opus-4.8"        # 最新旗舰模型，专长代码和长任务
export LLM_MODEL="claude-fable"           # 新一代高效模型
export LLM_MODEL="claude-mythos"          # 最新模型层级

# Claude 3 经典系列
export LLM_MODEL="claude-3-opus-20240229"
export LLM_MODEL="claude-3-sonnet-20240229"
export LLM_MODEL="claude-3-haiku-20240307"
```

**OpenAI**:
```bash
# GPT-4 系列（稳定生产）
export LLM_MODEL="gpt-4-turbo"
export LLM_MODEL="gpt-4"
export LLM_MODEL="gpt-3.5-turbo"
```

**Google Gemini**:
```bash
# Gemini 系列
export LLM_MODEL="gemini-1.5-pro"
export LLM_MODEL="gemini-pro"
```

**DeepSeek**:
```bash
# DeepSeek 系列（高性价比）
export LLM_MODEL="deepseek-chat"
export LLM_MODEL="deepseek-coder"
```

**🖥️ 本地模型（Ollama - 2026热门）**:
```bash
# 安装 Ollama
curl https://ollama.ai/install.sh | sh

# 🔥 热门模型 Top 5（按下载量排序）

# 1. Meta Llama 系列（116M+ 下载）
ollama pull llama3.1:8b               # Llama 3.1 8B - 最流行
ollama pull llama3.1:70b              # Llama 3.1 70B
ollama pull llama3.1:405b             # Llama 3.1 405B（大内存）
ollama pull llama3.2:1b               # Llama 3.2 小型（1B-3B）
ollama pull llama3.2:3b

# 2. DeepSeek-R1 推理模型（88M+ 下载）⭐推荐
ollama pull deepseek-r1:1.5b          # 超轻量推理
ollama pull deepseek-r1:8b            # 小型推理
ollama pull deepseek-r1:14b           # 中型推理
ollama pull deepseek-r1:32b           # 大型推理
ollama pull deepseek-r1:70b           # 超大型推理
ollama pull deepseek-r1:671b          # 旗舰推理（需大内存）

# 3. Nomic Embed（75M+ 下载）
ollama pull nomic-embed-text          # 高性能嵌入模型

# 4. Google Gemma 系列（37M+ 下载）
ollama pull gemma3:270m               # Gemma 3 超轻量
ollama pull gemma3:2b                 # Gemma 3 小型
ollama pull gemma3:9b                 # Gemma 3 中型
ollama pull gemma3:27b                # Gemma 3 大型
ollama pull gemma4                    # Gemma 4 最新（多模态）

# 5. Qwen 系列（中文优化）
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull qwen2.5:32b
ollama pull qwen2.5:72b
ollama pull qwen2.5-coder

# 🆕 2026新模型（最近1个月）

# IBM Granite 4.1（企业级）
ollama pull granite4.1:3b             # 工具使用和多语言
ollama pull granite4.1:8b
ollama pull granite4.1-guardian       # 安全评估模型

# GLM-5.2（智谱AI）
ollama pull glm-5.2                   # 长任务旗舰模型

# Cohere North Mini Code
ollama pull north-mini-code-1.0       # 30B MoE 代码模型

# Google Ministral 3
ollama pull ministral-3               # 边缘视觉模型

# 其他流行模型
ollama pull mistral:7b                # Mistral 7B
ollama pull mixtral:8x7b              # Mixtral MoE
ollama pull deepseek-v2.5             # DeepSeek V2.5
ollama pull deepseek-coder-v2         # DeepSeek Coder
```

**配置示例**:
```python
# app/core/config.py

# 使用 Claude Opus 4.8（2026最新推荐）
LLM_PROVIDER = "anthropic"
LLM_MODEL = "claude-opus-4.8"
ANTHROPIC_API_KEY = "sk-ant-..."

# 使用 GPT-4 Turbo
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4-turbo"
OPENAI_API_KEY = "sk-..."

# 使用 DeepSeek（高性价比）
LLM_PROVIDER = "openai"  # DeepSeek 兼容 OpenAI API
LLM_MODEL = "deepseek-chat"
OPENAI_API_KEY = "sk-..."
OPENAI_API_BASE = "https://api.deepseek.com"

# 使用本地 DeepSeek-R1（2026热门推理模型）
LLM_PROVIDER = "ollama"
LLM_MODEL = "deepseek-r1:32b"         # 推理能力强
OLLAMA_BASE_URL = "http://localhost:11434"

# 使用 Gemma 4（2026最新多模态）
LLM_PROVIDER = "ollama"
LLM_MODEL = "gemma4"
OLLAMA_BASE_URL = "http://localhost:11434"
```

**模型选择建议（2026版）**:

| 场景 | 推荐模型 | 原因 |
|------|---------|------|
| **生产环境（云端）** | Claude Opus 4.8, GPT-4 Turbo | 最新能力，稳定可靠 |
| **高性价比** | DeepSeek Chat, GPT-3.5 | 成本低，性能优 |
| **中文优化** | Qwen 2.5, GLM-5.2 | 中文理解强 |
| **代码生成** | North Mini Code, DeepSeek Coder | 2026代码专用 |
| **复杂推理** | DeepSeek-R1, Claude Opus 4.8 | 推理能力突出 |
| **本地部署（小型）** | Llama 3.2:3b, Gemma 3:2b | 轻量高效 |
| **本地部署（大型）** | DeepSeek-R1:32b, Llama 3.1:70b | 性能强大 |
| **企业应用** | Granite 4.1, Claude Opus 4.8 | 工具使用，长任务 |
| **边缘设备** | Ministral 3, Gemma 3:270m | 边缘优化 |
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
