# RAG 系统优化总结

## 🎯 优化目标

将 RAG 知识库中的文档按照不同的领域进行分类，让不同的 Agent 只检索相关领域的文档，提高检索准确性和效率。

---

## ✅ 已完成的优化

### 1. **文档分类系统** ✨

**实现内容：**
- 为所有文档添加了 `agent` 元数据标签
- 支持 4 种 Agent 类别：
  - `cybersecurity` - 网络安全相关文档（11 个文档，685 个块）
  - `artificial_intelligence` - AI/ML 相关文档（2 个文档，6 个块）
  - `pdf_text` - PDF 处理相关文档
  - `general` - 通用文档（1 个文档，1 个块）

**相关文件：**
- `scripts/classify_documents.py` - 文档分类规则
- `scripts/add_agent_labels.py` - 批量添加标签并重新索引
- `scripts/check_agent_labels.py` - 验证分类结果

### 2. **基于 Agent 的自动文档过滤** ⭐ 核心优化

**实现内容：**
- 创建了 `app/services/agent_document_filter.py` 模块
- 实现了 `get_sources_by_agent_class()` 函数，根据 agent_class 自动获取相关文档列表
- 修改了检索流程，自动应用文档过滤

**工作原理：**
```python
# 当 Cybersecurity Agent 查询时
agent_class = "cybersecurity"
allowed_sources = get_sources_by_agent_class(agent_class)
# 只检索 11 个网络安全相关文档，而不是全部 14 个文档

# 当 General Agent 查询时
agent_class = "general"
allowed_sources = get_sources_by_agent_class(agent_class)
# 返回 None，不过滤，可以访问所有文档
```

**修改的文件：**
- `app/agents/vector_rag_agent.py` - 添加 agent_class 参数和自动过滤
- `app/agents/graph_rag_agent.py` - 添加 agent_class 参数和自动过滤
- `app/graph/nodes/safe_wrappers.py` - 传递 agent_class 参数
- `app/graph/streaming/stream_processor.py` - 在所有检索调用中传递 agent_class

### 3. **前端黑屏 Bug 修复** 🐛

**问题：**
- MessageCard.tsx 第 136 行访问 `path.entities` 时未检查是否存在
- 导致前端崩溃，显示黑屏

**修复：**
- 添加了安全检查：`path.entities && Array.isArray(path.entities)`
- 提供降级显示：当数据不完整时显示提示信息

### 4. **监控和分析系统** 📊

**状态：** ✅ 已完成

**完成日期：** 2026-05-17

**实现内容：**
- ✅ RetrievalLogger 服务（内存存储，最近 1000 条记录）
- ✅ Analytics API（4 个端点：overview, agents, documents, export）
- ✅ 检索日志注入（safe_vector_result, safe_graph_result）
- ✅ 前端监控页面（Recharts 图表，10 秒自动刷新）
- ✅ 路由集成（/app/analytics）
- ✅ AdminPage 导航按钮

**测试结果：**
- 单元测试：20/20 通过（RetrievalLogger）
- 集成测试：14/14 通过（Analytics API）
- 端到端测试：✅ 通过

**文件变更：**
- 新建：`app/services/retrieval_logger.py`
- 新建：`app/api/routes/analytics.py`
- 新建：`frontend/src/pages/AnalyticsPage.tsx`
- 新建：`tests/services/test_retrieval_logger.py`
- 新建：`tests/api/test_analytics.py`
- 修改：`app/graph/nodes/safe_wrappers.py`
- 修改：`app/api/main.py`
- 修改：`frontend/src/App.tsx`
- 修改：`frontend/src/pages/AdminPage.tsx`
- 修改：`frontend/package.json`

**功能验证：**
- ✅ 每次检索自动记录日志
- ✅ 内存存储最近 1000 条记录
- ✅ 提供 4 个 API 端点（overview, agents, documents, export）
- ✅ 前端监控页面显示统计和图表
- ✅ 10 秒自动刷新
- ✅ 支持 JSON 和 CSV 导出
- ✅ AdminPage 导航按钮正常工作

**核心功能：**

1. **检索日志记录**
   - 自动记录每次向量检索和图检索
   - 记录查询文本、Agent 类型、检索到的文档、时间戳
   - 线程安全的单例模式

2. **分析 API**
   - `GET /api/analytics/overview` - 总体统计（总查询数、成功率、平均文档数）
   - `GET /api/analytics/agents` - Agent 使用分布
   - `GET /api/analytics/documents` - 文档检索频率（Top 20）
   - `GET /api/analytics/export` - 导出日志（JSON/CSV）

3. **前端监控页面**
   - 统计卡片：总查询数、成功率、平均文档数、Agent 数量
   - Agent 分布饼图（Recharts）
   - 文档检索频率柱状图（Top 10）
   - 自动刷新（10 秒间隔）
   - 导出功能（JSON/CSV）

4. **集成点**
   - `safe_vector_result()` - 向量检索后记录
   - `safe_graph_result()` - 图检索后记录
   - AdminPage - 添加"📊 查看监控分析"按钮

---

## 📊 优化效果

### 检索范围缩小

**优化前：**
- 所有 Agent 都检索全部 14 个文档（692 个块）
- 大量无关文档干扰检索结果

**优化后：**
- Cybersecurity Agent：只检索 11 个相关文档（685 个块）
- AI Agent：只检索 2 个相关文档（6 个块）
- General Agent：检索所有文档（保持灵活性）

### 性能提升

1. **检索准确性提升** - 减少无关文档干扰，提高相关文档的排名
2. **检索速度提升** - 减少需要检索的文档数量
3. **降低噪音** - 避免不同领域的文档混淆

---

## 🚀 进一步优化建议

### 1. **动态文档分类管理**

**当前限制：**
- 文档分类规则硬编码在脚本中
- 添加新文档需要手动运行脚本重新索引

**优化方案：**
- 创建文档分类管理 API
- 添加前端界面，支持可视化管理文档分类
- 实现增量索引，新文档自动分类

**实现步骤：**
```python
# 1. 创建 API 端点
POST /api/documents/classify
GET /api/documents/categories
PUT /api/documents/{doc_id}/category

# 2. 前端界面
- 文档列表页面，显示每个文档的分类
- 支持拖拽或下拉菜单修改分类
- 批量操作：选择多个文档统一分类

# 3. 自动分类
- 使用 LLM 分析文档内容，自动推荐分类
- 支持用户确认或修改
```

### 2. **更细粒度的分类**

**当前分类：**
- 只有 4 个大类，粒度较粗

**优化方案：**
- 支持多级分类（主类别 + 子类别）
- 支持多标签（一个文档可以属于多个类别）

**示例：**
```python
# 多级分类
cybersecurity/
  ├── attack_analysis/
  ├── defense_hardening/
  └── incident_response/

# 多标签
document.tags = ["cybersecurity", "ai_security", "llm"]
```

### 3. **智能 Agent 路由优化**

**当前实现：**
- Agent 分类基于关键词匹配（`agent_classifier.py`）
- 规则较简单，可能误判

**优化方案：**
- 使用 LLM 进行更智能的意图识别
- 支持多 Agent 协作（一个问题可能需要多个 Agent）
- 添加置信度评分，低置信度时询问用户

**实现示例：**
```python
# 智能路由
result = classify_with_llm(question)
# {
#   "primary_agent": "cybersecurity",
#   "confidence": 0.85,
#   "secondary_agents": ["artificial_intelligence"],
#   "reason": "问题涉及 AI 系统的安全防护"
# }

# 如果置信度低于阈值，询问用户
if result["confidence"] < 0.7:
    ask_user_to_choose_agent()
```

### 4. **检索策略优化**

**当前实现：**
- 简单的文档过滤
- 所有文档块权重相同

**优化方案：**
- 根据 Agent 类别调整检索参数
- 为不同类别的文档设置不同的权重
- 实现跨类别检索（当主类别结果不足时）

**实现示例：**
```python
# 根据 Agent 调整检索参数
if agent_class == "cybersecurity":
    # 网络安全问题需要更多上下文
    top_k = 10
    similarity_threshold = 0.3
elif agent_class == "artificial_intelligence":
    # AI 问题更精确
    top_k = 5
    similarity_threshold = 0.5

# 跨类别检索
if len(results) < min_results:
    # 扩展到相关类别
    related_classes = get_related_classes(agent_class)
    for related in related_classes:
        additional_results = retrieve(query, agent_class=related)
        results.extend(additional_results)
```

### 5. **用户反馈机制**

**优化方案：**
- 在前端添加"这个答案有帮助吗？"按钮
- 收集用户反馈，优化分类和路由
- 支持用户手动切换 Agent

**实现示例：**
```typescript
// 前端添加反馈按钮
<FeedbackButtons
  onHelpful={() => recordFeedback("helpful")}
  onNotHelpful={() => recordFeedback("not_helpful")}
  onWrongAgent={() => showAgentSelector()}
/>

// 用户可以手动选择 Agent
<AgentSelector
  current={currentAgent}
  onChange={(newAgent) => retryWithAgent(newAgent)}
/>
```

---

## 📝 使用说明

### 添加新文档

1. 将文档放入 `data/docs/` 目录
2. 运行分类脚本：
   ```powershell
   python scripts/add_agent_labels.py
   ```
3. 验证分类结果：
   ```powershell
   python scripts/check_agent_labels.py
   ```

### 修改分类规则

编辑 `scripts/classify_documents.py` 中的 `classify_document()` 函数：

```python
def classify_document(file_path: Path) -> str:
    name_lower = file_path.name.lower()
    path_str = str(file_path).lower()
    
    # 添加新的分类规则
    if "your_keyword" in name_lower:
        return "your_category"
    
    # ... 其他规则
```

### 测试文档过滤

```powershell
python app/services/agent_document_filter.py
```

---

## 🎉 总结

通过这次优化，我们实现了：

1. ✅ **文档分类系统** - 所有文档都有明确的领域标签
2. ✅ **自动文档过滤** - Agent 自动只检索相关领域的文档
3. ✅ **前端 Bug 修复** - 解决了黑屏问题
4. ✅ **完整的工具链** - 分类、索引、验证脚本齐全
5. ✅ **监控和分析系统** - 实时监控检索性能和使用情况

**核心优势：**
- 🎯 提高检索准确性 - 减少无关文档干扰
- ⚡ 提升检索速度 - 减少检索范围
- 🧹 降低噪音 - 避免不同领域混淆
- 🔧 易于维护 - 清晰的分类规则和工具
- 📊 数据驱动 - 实时监控和分析检索性能

**下一步：**
- 根据监控数据，调整分类规则和检索策略
- 考虑实现上述进一步优化建议
- 收集用户反馈，持续改进
