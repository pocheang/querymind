# RAG 系统进一步优化 - 提示词

## 📋 项目背景

这是一个多智能体 RAG（检索增强生成）系统，支持向量检索、知识图谱和 Web 搜索。

**技术栈：**
- 后端：FastAPI + Python
- 前端：React + TypeScript + Vite
- 向量数据库：Chroma
- 知识图谱：Neo4j
- LLM 后端：Ollama (qwen2.5:7b-instruct)

**项目路径：** `c:\Users\pocheang\Desktop\llm\multi_agent_rag_local_v4`

---

## ✅ 已完成的优化

### 1. 文档分类系统
- 为所有文档添加了 `agent` 元数据标签
- 支持 4 种 Agent 类别：
  - `cybersecurity` - 网络安全（11 个文档，685 个块）
  - `artificial_intelligence` - AI/ML（2 个文档，6 个块）
  - `pdf_text` - PDF 处理
  - `general` - 通用（1 个文档，1 个块）

**相关文件：**
- `scripts/classify_documents.py` - 文档分类规则
- `scripts/add_agent_labels.py` - 批量添加标签
- `scripts/check_agent_labels.py` - 验证分类结果

### 2. 基于 Agent 的自动文档过滤
- 创建了 `app/services/agent_document_filter.py` 模块
- 实现了 `get_sources_by_agent_class()` 函数
- 修改了检索流程，自动应用文档过滤

**修改的文件：**
- `app/agents/vector_rag_agent.py` - 添加 agent_class 参数
- `app/agents/graph_rag_agent.py` - 添加 agent_class 参数
- `app/graph/nodes/safe_wrappers.py` - 传递 agent_class
- `app/graph/streaming/stream_processor.py` - 应用过滤

### 3. 前端 Bug 修复
- 修复了 `frontend/src/pages/chat/components/MessageCard.tsx` 第 136 行的空值访问错误
- 添加了安全检查，防止前端崩溃

---

## 🎯 可选的优化方向

### 优化 1：动态文档分类管理 API 和前端界面

**目标：** 创建可视化的文档分类管理系统

**实现内容：**
1. 后端 API 端点：
   ```python
   # app/api/routes/document_management.py
   GET /api/documents/list - 列出所有文档及其分类
   GET /api/documents/categories - 获取所有分类统计
   PUT /api/documents/{doc_id}/category - 修改文档分类
   POST /api/documents/reindex - 重新索引文档
   POST /api/documents/classify-auto - 使用 LLM 自动分类
   ```

2. 前端界面：
   - 文档列表页面，显示每个文档的分类
   - 支持拖拽或下拉菜单修改分类
   - 批量操作：选择多个文档统一分类
   - 显示分类统计图表

3. 自动分类功能：
   - 使用 LLM 分析文档内容
   - 自动推荐分类
   - 支持用户确认或修改

**相关文件：**
- 需要创建：`app/api/routes/document_management.py`
- 需要创建：`frontend/src/pages/documents/` 目录
- 参考：`app/services/agent_document_filter.py`
- 参考：`app/retrievers/corpus_store.py`

---

### 优化 2：更细粒度的文档分类

**目标：** 支持多级分类和多标签

**实现内容：**
1. 多级分类结构：
   ```python
   cybersecurity/
     ├── attack_analysis/
     ├── defense_hardening/
     └── incident_response/
   
   artificial_intelligence/
     ├── llm/
     ├── rag/
     └── machine_learning/
   ```

2. 多标签支持：
   - 一个文档可以属于多个类别
   - 例如：`["cybersecurity", "ai_security", "llm"]`

3. 修改数据结构：
   - 将 `metadata.agent` 从字符串改为数组
   - 更新检索逻辑，支持多标签匹配

**相关文件：**
- 需要修改：`scripts/classify_documents.py`
- 需要修改：`app/services/agent_document_filter.py`
- 需要修改：`app/services/ingest_service.py`

---

### 优化 3：智能 Agent 路由优化

**目标：** 使用 LLM 进行更智能的意图识别

**实现内容：**
1. LLM 辅助分类：
   ```python
   # 替代当前的关键词匹配
   result = classify_with_llm(question)
   # 返回：
   # {
   #   "primary_agent": "cybersecurity",
   #   "confidence": 0.85,
   #   "secondary_agents": ["artificial_intelligence"],
   #   "reason": "问题涉及 AI 系统的安全防护"
   # }
   ```

2. 多 Agent 协作：
   - 一个问题可能需要多个 Agent
   - 合并多个 Agent 的检索结果

3. 置信度评分：
   - 低置信度时询问用户选择 Agent
   - 前端显示 Agent 选择器

**相关文件：**
- 需要修改：`app/services/agent_classifier.py`
- 需要修改：`app/agents/router_agent.py`
- 需要创建：前端 Agent 选择器组件

---

### 优化 4：检索策略优化

**目标：** 根据 Agent 类别调整检索参数

**实现内容：**
1. 动态检索参数：
   ```python
   if agent_class == "cybersecurity":
       top_k = 10  # 网络安全需要更多上下文
       similarity_threshold = 0.3
   elif agent_class == "artificial_intelligence":
       top_k = 5  # AI 问题更精确
       similarity_threshold = 0.5
   ```

2. 文档权重调整：
   - 为不同类别的文档设置不同的权重
   - 主类别文档权重更高

3. 跨类别检索：
   - 当主类别结果不足时，扩展到相关类别
   - 例如：cybersecurity 可以扩展到 ai_security

**相关文件：**
- 需要修改：`app/retrievers/hybrid_retriever.py`
- 需要修改：`app/agents/vector_rag_agent.py`
- 需要创建：`app/services/retrieval_strategy.py`

---

### 优化 5：监控和分析系统

**目标：** 添加检索日志和统计分析

**实现内容：**
1. 检索日志：
   ```python
   log_retrieval({
       "question": question,
       "agent_class": agent_class,
       "filtered_docs": len(allowed_sources),
       "retrieved_count": len(results),
       "top_scores": [r["score"] for r in results[:3]],
       "timestamp": datetime.now()
   })
   ```

2. 统计分析 API：
   ```python
   GET /api/analytics/retrieval-stats
   # 返回：
   # - 每个 Agent 的查询次数
   # - 平均检索文档数
   # - 检索成功率
   # - 最常检索的文档
   ```

3. 前端仪表板：
   - 显示检索统计图表
   - Agent 使用频率
   - 文档热度分析

**相关文件：**
- 需要创建：`app/services/retrieval_logger.py`
- 需要创建：`app/api/routes/analytics.py`
- 需要创建：`frontend/src/pages/analytics/`

---

### 优化 6：用户反馈机制

**目标：** 收集用户反馈，持续改进

**实现内容：**
1. 前端反馈按钮：
   ```typescript
   <FeedbackButtons
     onHelpful={() => recordFeedback("helpful")}
     onNotHelpful={() => recordFeedback("not_helpful")}
     onWrongAgent={() => showAgentSelector()}
   />
   ```

2. 手动切换 Agent：
   ```typescript
   <AgentSelector
     current={currentAgent}
     onChange={(newAgent) => retryWithAgent(newAgent)}
   />
   ```

3. 反馈数据收集：
   - 记录用户反馈
   - 分析哪些问题被误分类
   - 优化分类规则

**相关文件：**
- 需要修改：`frontend/src/pages/chat/components/MessageCard.tsx`
- 需要创建：`app/api/routes/feedback.py`
- 需要创建：`app/services/feedback_analyzer.py`

---

## 🚀 开始优化

### 推荐的优化顺序

1. **优化 5（监控和分析）** - 先建立数据收集，了解系统使用情况
2. **优化 3（智能路由）** - 提高 Agent 分类准确性
3. **优化 4（检索策略）** - 优化检索效果
4. **优化 1（管理界面）** - 提供可视化管理工具
5. **优化 6（用户反馈）** - 建立持续改进机制
6. **优化 2（细粒度分类）** - 最后扩展分类体系

### 使用此提示词

**复制以下内容到新的聊天框：**

```
我有一个多智能体 RAG 系统，已经完成了基础的文档分类和 Agent 过滤优化。

项目路径：c:\Users\pocheang\Desktop\llm\multi_agent_rag_local_v4

请阅读 NEXT_OPTIMIZATION_PROMPT.md 文件，了解项目背景和已完成的优化。

我想实现【选择一个优化方向，例如：优化 5 - 监控和分析系统】。

请帮我：
1. 分析需要修改和创建的文件
2. 设计实现方案
3. 逐步实现功能
4. 测试验证

技术栈：
- 后端：FastAPI + Python
- 前端：React + TypeScript
- 向量数据库：Chroma
- 知识图谱：Neo4j
- LLM：Ollama (qwen2.5:7b-instruct)
```

---

## 📚 重要文件参考

### 核心架构文件
- `app/api/main.py` - FastAPI 主入口
- `app/agents/router_agent.py` - Agent 路由逻辑
- `app/services/agent_classifier.py` - Agent 分类器
- `app/graph/streaming/stream_processor.py` - 流式查询处理

### 检索相关
- `app/retrievers/hybrid_retriever.py` - 混合检索
- `app/retrievers/vector_store.py` - 向量检索
- `app/retrievers/corpus_store.py` - 文档存储
- `app/agents/vector_rag_agent.py` - 向量 RAG Agent
- `app/agents/graph_rag_agent.py` - 图谱 RAG Agent

### 文档分类相关
- `app/services/agent_document_filter.py` - 文档过滤器
- `scripts/classify_documents.py` - 分类规则
- `scripts/add_agent_labels.py` - 添加标签
- `scripts/check_agent_labels.py` - 验证分类

### 前端相关
- `frontend/src/pages/chat/` - 聊天界面
- `frontend/src/pages/chat/components/MessageCard.tsx` - 消息卡片
- `frontend/src/pages/chat/hooks/useMessageActions.ts` - 消息处理

### 配置文件
- `.env` - 环境配置
- `app/core/config.py` - 应用配置

---

## 💡 提示

1. **先读取相关文件** - 了解现有实现
2. **小步迭代** - 每次只实现一个小功能
3. **及时测试** - 每个功能完成后立即测试
4. **保持兼容** - 不要破坏现有功能
5. **添加日志** - 方便调试和监控

祝优化顺利！🎉
