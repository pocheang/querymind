# 📘 QueryMind 用户手册

> QueryMind 企业级智能问答引擎完整使用指南

---

## 📖 目录

- [系统概述](#系统概述)
- [用户界面](#用户界面)
- [核心功能](#核心功能)
- [高级功能](#高级功能)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)

---

## 系统概述

### 什么是 QueryMind？

QueryMind（智询）是一个企业级智能问答引擎，专为以下场景设计：

- 🏢 **企业知识库** - 内部文档智能检索
- 📚 **技术文档助手** - API 文档、技术手册问答
- 🎓 **学习辅助工具** - 教材、论文智能分析
- 🔍 **研究工具** - 大量文献快速检索

### 核心优势

| 特性 | 说明 | 优势 |
|------|------|------|
| 🤖 **多智能体协作** | 多个专业 Agent 协同工作 | 更准确的答案生成 |
| 🔍 **混合检索** | 向量+关键词+知识图谱 | 更高的检索精度 |
| 🔐 **企业级安全** | RBAC 权限控制 | 数据安全保障 |
| 🌏 **多语言支持** | 中英文优化 | 更好的本地化体验 |
| 📊 **实时监控** | 执行过程可视化 | 透明可追溯 |

---

## 用户界面

### 主要页面

#### 1. 🔐 登录/注册页面

**功能**：
- 用户注册和登录
- 支持两种角色：
  - **Viewer** (查看者): 只能查询和查看
  - **Analyst** (分析师): 完全访问权限，包括上传文档

**操作指南**：
```
1. 访问 http://localhost:5173
2. 新用户点击"注册"
3. 输入用户名、密码，选择角色
4. 点击"注册"完成
5. 使用账号登录系统
```

#### 2. 💬 聊天界面

**功能**：
- 智能问答对话
- 查看引用来源
- 查询历史记录
- 多轮对话上下文保持

**使用技巧**：
```
✅ 好的提问方式：
- "总结文档X的核心观点"
- "文档中关于Y的技术细节是什么？"
- "比较文档A和文档B中关于Z的不同观点"

❌ 不好的提问方式：
- "什么？"（过于简短）
- "所有内容"（过于宽泛）
- 无具体上下文的代词（"它是什么？"）
```

#### 3. 📄 文档管理页面

**功能**：
- 上传新文档
- 查看文档列表
- 删除文档
- 查看文档状态

**支持的文件格式**：
- 📄 PDF (.pdf)
- 📝 纯文本 (.txt)
- 📊 Markdown (.md)
- 📃 Word 文档 (.docx)

**上传步骤**：
```
1. 点击"上传文档"按钮
2. 选择文件（支持批量上传）
3. 等待处理完成
4. 查看文档状态（处理中/已完成/失败）
```

**文档大小限制**：
- 单个文件: 最大 50MB
- PDF 页数: 建议不超过 500 页
- 批量上传: 一次最多 10 个文件

#### 4. 🕸️ 知识图谱页面

**功能**：
- 可视化实体关系
- 交互式图谱浏览
- 节点详情查看
- 关系路径探索

**操作指南**：
```
- 拖拽节点：调整视图位置
- 点击节点：查看实体详情
- 双击节点：展开相关实体
- 滚轮缩放：调整视图大小
```

#### 5. 🤖 代理追踪页面

**功能**：
- 实时查看 Agent 执行流程
- 查看每个步骤的输入输出
- 理解查询处理路径
- 性能分析

**追踪信息**：
- ✅ Agent 名称和类型
- ✅ 执行状态（运行中/完成/失败）
- ✅ 执行时间
- ✅ 输入参数
- ✅ 输出结果
- ✅ 错误信息（如有）

#### 6. 👨‍💼 管理控制台（仅 Analyst）

**功能**：
- 用户管理
- 系统配置
- 数据统计
- 日志查看

**用户管理**：
```
- 查看所有用户
- 修改用户角色
- 禁用/启用用户
- 查看用户活动
```

#### 7. 📊 性能分析页面

**功能**：
- 检索性能统计
- 查询响应时间
- 命中率分析
- 用户行为分析

---

## 核心功能

### 🔍 智能检索

#### 检索模式

QueryMind 支持多种检索模式，系统自动选择最优策略：

1. **向量检索**
   - 语义相似度匹配
   - 适合概念性查询
   - 示例: "关于机器学习的内容"

2. **关键词检索 (BM25)**
   - 精确关键词匹配
   - 适合专有名词查询
   - 示例: "BERT 模型架构"

3. **混合检索**
   - 结合向量和关键词
   - 最高检索精度
   - 自动融合排序

4. **知识图谱检索**
   - 实体关系查询
   - 多跳推理
   - 示例: "A 和 B 的关系是什么？"

#### 检索参数（可在配置中调整）

```python
# 检索数量
TOP_K = 5  # 返回前5个最相关的文档块

# 相似度阈值
SIMILARITY_THRESHOLD = 0.7  # 相似度低于0.7的结果将被过滤

# 混合检索权重
VECTOR_WEIGHT = 0.7  # 向量检索权重
BM25_WEIGHT = 0.3    # BM25检索权重
```

### 🤖 多智能体系统

#### Agent 类型

| Agent | 职责 | 何时触发 |
|-------|------|----------|
| **Router Agent** | 分析查询意图，选择执行路径 | 每次查询开始 |
| **Vector RAG Agent** | 执行向量和混合检索 | 需要检索文档时 |
| **Graph RAG Agent** | 查询知识图谱 | 涉及实体关系时 |
| **Web Research Agent** | 网络搜索（如配置） | 本地知识不足时 |
| **Synthesis Agent** | 合成答案，安全检查 | 最后生成答案 |

#### Agent 执行流程

```
用户查询
    ↓
Router Agent (意图分析)
    ↓
[并行执行]
    ├─→ Vector RAG Agent (文档检索)
    └─→ Graph RAG Agent (知识图谱)
    ↓
Synthesis Agent (答案合成)
    ↓
返回结果 + 引用来源
```

### 📚 引用溯源

每个答案都包含引用来源：

```
答案: [生成的答案内容]

引用来源:
📄 文档1 - 第3页
   "...相关文本片段..."
   
📄 文档2 - 第7页
   "...相关文本片段..."
```

**引用信息包括**：
- 文档名称
- 页码/位置
- 相关文本片段
- 相似度分数

---

## 高级功能

### 🎯 高级查询技巧

#### 1. 指定搜索范围
```
"在文档A中查找关于X的内容"
"仅从技术文档中检索Y"
```

#### 2. 对比分析
```
"比较文档A和文档B对X的观点"
"X和Y的区别是什么？"
```

#### 3. 总结归纳
```
"总结关于X的所有信息"
"列出Y的主要特点"
```

#### 4. 深度分析
```
"详细解释X的工作原理"
"分析Y的优缺点"
```

### 🔧 自定义配置

#### 配置 LLM 模型

编辑 `app/core/config.py`：

```python
# 使用 OpenAI
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4"
LLM_TEMPERATURE = 0.7

# 使用 Ollama (本地)
LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3"
LLM_TEMPERATURE = 0.7

# 使用 Anthropic Claude
LLM_PROVIDER = "anthropic"
LLM_MODEL = "claude-3-opus-20240229"
LLM_TEMPERATURE = 0.7
```

#### 配置检索参数

```python
# 向量数据库配置
CHROMA_COLLECTION_NAME = "documents"
EMBEDDING_MODEL = "text-embedding-ada-002"

# 检索配置
RETRIEVAL_TOP_K = 5
SIMILARITY_THRESHOLD = 0.7
RERANK_TOP_K = 3

# 混合检索权重
VECTOR_WEIGHT = 0.7
BM25_WEIGHT = 0.3
```

### 📊 批量操作

#### 批量上传文档

```python
# 使用 API 批量上传
import requests

files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
for file_path in files:
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(
            "http://localhost:8000/api/documents/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Uploaded {file_path}: {response.status_code}")
```

#### 批量查询

```python
# 批量查询脚本
queries = [
    "什么是机器学习？",
    "深度学习的原理",
    "神经网络的应用"
]

for query in queries:
    response = requests.post(
        "http://localhost:8000/api/chat/query",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Query: {query}")
    print(f"Answer: {response.json()['answer']}\n")
```

---

## 最佳实践

### ✅ 文档上传建议

1. **文档质量**
   - 使用清晰扫描的 PDF
   - 避免图片型 PDF（OCR 识别率低）
   - 保持文档结构完整

2. **命名规范**
   - 使用有意义的文件名
   - 避免特殊字符
   - 包含版本号（如适用）

3. **内容组织**
   - 相关文档放在一起上传
   - 定期清理过时文档
   - 维护文档元数据

### ✅ 查询优化

1. **清晰表达**
   - 使用完整句子
   - 提供上下文信息
   - 明确查询意图

2. **渐进式提问**
   ```
   第1次: "什么是 BERT？"
   第2次: "BERT 的训练方法是什么？"
   第3次: "如何在项目中使用 BERT？"
   ```

3. **利用引用**
   - 查看引用来源验证答案
   - 基于引用深入提问
   - 对比多个来源

### ✅ 系统维护

1. **定期备份**
   ```bash
   # 备份数据库
   cp -r data/chroma_db data/backup_$(date +%Y%m%d)
   
   # 备份配置
   cp app/core/config.py config_backup_$(date +%Y%m%d).py
   ```

2. **性能监控**
   - 定期检查响应时间
   - 监控内存使用
   - 查看错误日志

3. **更新升级**
   ```bash
   # 更新代码
   git pull origin main
   
   # 更新依赖
   conda activate rag-local
   pip install -r requirements.txt --upgrade
   ```

---

## 常见问题

### Q1: 为什么答案不准确？

**可能原因**：
1. 相关文档未上传
2. 文档质量不佳（扫描不清）
3. 查询表达不清晰

**解决方案**：
- 确保相关文档已上传并处理完成
- 重新表述查询，提供更多上下文
- 查看"代理追踪"了解检索过程

### Q2: 上传的文档无法检索到？

**检查步骤**：
1. 确认文档状态为"已完成"
2. 等待索引构建完成（大文档需要时间）
3. 检查文档格式是否支持
4. 查看后端日志是否有错误

### Q3: 系统响应很慢？

**优化建议**：
1. 减少 `TOP_K` 参数（减少检索数量）
2. 使用更快的 LLM 模型（如 GPT-3.5）
3. 增加服务器资源配置
4. 启用缓存机制

### Q4: 如何处理大型 PDF？

**建议方案**：
1. **分割文档**
   - 将大PDF拆分成多个小文件
   - 按章节分割

2. **优化配置**
   ```python
   # 增加处理超时时间
   PDF_PROCESSING_TIMEOUT = 600  # 10分钟
   
   # 调整块大小
   CHUNK_SIZE = 500  # 减小块大小
   CHUNK_OVERLAP = 50
   ```

3. **异步处理**
   - 使用后台任务处理大文档
   - 定期检查处理状态

### Q5: 支持哪些 LLM 模型？

**目前支持**：
- ✅ **OpenAI**: GPT-4, GPT-3.5
- ✅ **Anthropic**: Claude 3 (Opus/Sonnet/Haiku)
- ✅ **Ollama**: Llama 3, Qwen 2, Mistral 等
- ✅ **其他**: 兼容 OpenAI API 的模型

**配置示例**：
```python
# OpenAI
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4"
OPENAI_API_KEY = "sk-..."

# Ollama (本地)
LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3"
OLLAMA_BASE_URL = "http://localhost:11434"
```

---

## 🔗 相关资源

- [快速开始指南](./quick-start.md) - 新手入门
- [配置指南](./configuration.md) - 详细配置
- [API 文档](http://localhost:8000/docs) - 接口文档
- [故障排查](./troubleshooting.md) - 问题解决

---

<div align="center">

**需要更多帮助？**

[查看完整文档](../INDEX.md) · [提交问题](https://github.com/pocheang/querymind/issues) · [GitHub 仓库](https://github.com/pocheang/querymind)

</div>
