# 🐛 QueryMind 故障排查指南

> 常见问题诊断与解决方案

---

## 📋 目录

- [快速诊断](#快速诊断)
- [启动问题](#启动问题)
- [运行时错误](#运行时错误)
- [性能问题](#性能问题)
- [数据库问题](#数据库问题)
- [网络问题](#网络问题)
- [日志分析](#日志分析)

---

## 快速诊断

### 系统健康检查

运行健康检查脚本：

```bash
# 检查系统状态
python scripts/health_check.py
```

**检查项目**：
- ✅ Python 环境
- ✅ 依赖包安装
- ✅ 数据库连接
- ✅ LLM API 可用性
- ✅ 端口占用情况

### 快速检查清单

| 检查项 | 命令 | 期望结果 |
|--------|------|----------|
| **后端运行** | `curl http://localhost:8000/health` | `{"status": "ok"}` |
| **前端运行** | `curl http://localhost:5173` | 返回 HTML |
| **数据库** | 检查 `data/querymind.db` 文件 | 文件存在 |
| **向量数据库** | 检查 `data/chroma_db/` 目录 | 目录存在 |
| **Python 环境** | `python --version` | `Python 3.11.x` |

---

## 启动问题

### 问题 1：后端启动失败

#### 症状
```bash
ModuleNotFoundError: No module named 'fastapi'
```

#### 原因
依赖包未安装或环境未激活

#### 解决方案

**步骤 1：确认环境激活**
```bash
conda activate rag-local
which python  # Linux/macOS
where python  # Windows
```

**步骤 2：重新安装依赖**
```bash
pip install -r requirements.txt
```

**步骤 3：验证安装**
```bash
python -c "import fastapi; print(fastapi.__version__)"
```

---

### 问题 2：前端启动失败

#### 症状
```bash
Error: Cannot find module 'react'
```

#### 原因
Node 依赖未安装或损坏

#### 解决方案

**方案 1：重新安装依赖**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**方案 2：清理缓存**
```bash
npm cache clean --force
npm install
```

**方案 3：使用 yarn（如果 npm 持续失败）**
```bash
npm install -g yarn
yarn install
yarn dev
```

---

### 问题 3：端口被占用

#### 症状
```bash
Error: listen EADDRINUSE: address already in use :::8000
```

#### 原因
端口 8000（后端）或 5173（前端）已被占用

#### 解决方案

**Windows**：
```powershell
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程（替换 <PID> 为实际进程 ID）
taskkill /PID <PID> /F
```

**Linux/macOS**：
```bash
# 查找并结束进程
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

**更改端口**：
```bash
# 后端使用不同端口
uvicorn app.api.main:app --port 8001

# 前端使用不同端口
npm run dev -- --port 5174
```

---

### 问题 4：页面显示空白

#### 症状
浏览器访问 http://localhost:5173 显示空白页面

#### 诊断步骤

**步骤 1：检查浏览器控制台**
```
F12 → Console 标签
查看是否有 JavaScript 错误
```

**步骤 2：检查网络请求**
```
F12 → Network 标签
刷新页面，查看请求是否成功
```

**步骤 3：检查后端连接**
```bash
curl http://localhost:8000/health
```

#### 解决方案

**方案 1：后端未启动**
```bash
# 启动后端
conda activate rag-local
uvicorn app.api.main:app --reload
```

**方案 2：CORS 配置错误**

编辑 `app/core/config.py`：
```python
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000"
]
```

**方案 3：前端构建问题**
```bash
cd frontend
rm -rf dist node_modules
npm install
npm run dev
```

---

## 运行时错误

### 问题 5：LLM API 错误

#### 症状
```
Error: OpenAI API key not found
```

#### 解决方案

**方案 1：设置环境变量**
```bash
# Linux/macOS
export OPENAI_API_KEY="sk-..."

# Windows PowerShell
$env:OPENAI_API_KEY="sk-..."
```

**方案 2：配置文件**

编辑 `app/core/config.py`：
```python
OPENAI_API_KEY = "sk-..."
```

**方案 3：使用 .env 文件**

创建 `.env` 文件：
```bash
OPENAI_API_KEY=sk-...
```

---

### 问题 6：文档上传失败

#### 症状
```
Error: File too large
```

#### 原因
文件超过大小限制（默认 50MB）

#### 解决方案

**方案 1：增加文件大小限制**

编辑 `app/core/config.py`：
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
```

**方案 2：分割大文件**
```bash
# 使用 PDF 分割工具
pdftk large.pdf burst output page_%02d.pdf
```

**方案 3：压缩 PDF**
```bash
# 使用 Ghostscript 压缩
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=output.pdf input.pdf
```

---

### 问题 7：查询无结果

#### 症状
查询后返回"未找到相关信息"

#### 诊断步骤

**步骤 1：检查文档是否已索引**
```bash
# 检查 ChromaDB
ls -la data/chroma_db/

# 检查数据库
sqlite3 data/querymind.db "SELECT COUNT(*) FROM documents;"
```

**步骤 2：检查相似度阈值**

编辑 `app/core/config.py`：
```python
SIMILARITY_THRESHOLD = 0.5  # 降低阈值（原值 0.7）
```

**步骤 3：查看代理追踪**
```
访问 http://localhost:5173/agent-tracking
查看检索过程和结果
```

#### 解决方案

**方案 1：重新索引文档**
```bash
python scripts/reindex_documents.py
```

**方案 2：调整检索参数**
```python
RETRIEVAL_TOP_K = 10  # 增加检索数量
SIMILARITY_THRESHOLD = 0.5  # 降低阈值
```

**方案 3：改进查询表达**
```
❌ 不好: "这个"
✅ 好: "机器学习的定义是什么？"
```

---

### 问题 8：中文检索效果差

#### 症状
中文查询返回结果不准确

#### 解决方案

**方案 1：使用中文优化的 Embedding 模型**
```python
EMBEDDING_MODEL = "text-embedding-ada-002"  # OpenAI
# 或
EMBEDDING_MODEL = "m3e-base"  # 中文优化
```

**方案 2：配置中文分词**
```python
import jieba

# 加载自定义词典
jieba.load_userdict("custom_dict.txt")
```

**方案 3：启用同义词扩展**
```python
ENABLE_SYNONYM_EXPANSION = True
SYNONYM_DICT_PATH = "data/synonyms.txt"
```

---

## 性能问题

### 问题 9：响应速度慢

#### 症状
查询响应时间超过 10 秒

#### 诊断

**检查响应时间分布**：
```bash
# 查看日志
tail -f logs/app.log | grep "Query time"
```

#### 解决方案

**方案 1：减少检索数量**
```python
RETRIEVAL_TOP_K = 3  # 从 5 降到 3
```

**方案 2：使用更快的模型**
```python
LLM_MODEL = "gpt-3.5-turbo"  # 替代 gpt-4
```

**方案 3：启用缓存**
```python
ENABLE_CACHE = True
REDIS_HOST = "localhost"
REDIS_PORT = 6379
```

**方案 4：并行处理**
```python
MAX_CONCURRENT_TASKS = 4
ENABLE_ASYNC_PROCESSING = True
```

---

### 问题 10：内存占用过高

#### 症状
系统内存占用超过 8GB

#### 解决方案

**方案 1：减少批处理大小**
```python
BATCH_SIZE = 32  # 从 64 降到 32
```

**方案 2：定期清理缓存**
```bash
# 清理 ChromaDB 缓存
rm -rf data/chroma_db/.cache
```

**方案 3：限制向量维度**
```python
EMBEDDING_DIMENSION = 768  # 使用较小的模型
```

---

## 数据库问题

### 问题 11：数据库锁定错误

#### 症状
```
sqlite3.OperationalError: database is locked
```

#### 原因
多个进程同时访问 SQLite 数据库

#### 解决方案

**方案 1：使用 PostgreSQL（推荐生产环境）**
```python
DATABASE_URL = "postgresql://user:password@localhost/querymind"
```

**方案 2：增加超时时间**
```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    connect_args={"timeout": 30}  # 增加超时
)
```

**方案 3：使用 WAL 模式**
```python
import sqlite3

conn = sqlite3.connect("querymind.db")
conn.execute("PRAGMA journal_mode=WAL")
```

---

### 问题 12：ChromaDB 数据损坏

#### 症状
```
Error: Cannot load collection
```

#### 解决方案

**方案 1：重建索引**
```bash
# 备份数据
cp -r data/chroma_db data/chroma_db_backup

# 删除并重建
rm -rf data/chroma_db
python scripts/rebuild_index.py
```

**方案 2：从备份恢复**
```bash
rm -rf data/chroma_db
cp -r data/chroma_db_backup data/chroma_db
```

---

## 网络问题

### 问题 13：API 请求超时

#### 症状
```
Error: Request timeout
```

#### 解决方案

**方案 1：增加超时时间**
```python
import httpx

client = httpx.Client(timeout=60.0)  # 60秒超时
```

**方案 2：使用代理**
```bash
export HTTP_PROXY="http://proxy:port"
export HTTPS_PROXY="http://proxy:port"
```

**方案 3：检查网络连接**
```bash
# 测试 OpenAI 连接
curl -I https://api.openai.com/v1/models

# 测试 Anthropic 连接
curl -I https://api.anthropic.com/v1/messages
```

---

### 问题 14：CORS 错误

#### 症状
浏览器控制台显示：
```
Access to fetch has been blocked by CORS policy
```

#### 解决方案

编辑 `app/api/main.py`：
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 日志分析

### 启用详细日志

**配置日志级别**：
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
```

### 常见错误日志

#### 错误 1：模型加载失败
```
ERROR: Failed to load model: llama3
```

**解决**：
```bash
ollama pull llama3
ollama list  # 验证安装
```

#### 错误 2：数据库连接失败
```
ERROR: Could not connect to database
```

**解决**：
```bash
# 检查数据库文件
ls -la data/querymind.db

# 测试连接
python -c "from app.db.database import engine; engine.connect()"
```

#### 错误 3：向量化失败
```
ERROR: Embedding generation failed
```

**解决**：
```python
# 检查 API 密钥
echo $OPENAI_API_KEY

# 测试 Embedding
python scripts/test_embedding.py
```

---

## 紧急恢复

### 完全重置系统

**⚠️ 警告：此操作将删除所有数据**

```bash
# 1. 停止所有服务
pkill -f uvicorn
pkill -f vite

# 2. 备份数据（可选）
cp -r data data_backup_$(date +%Y%m%d)

# 3. 清理所有数据
rm -rf data/querymind.db
rm -rf data/chroma_db
rm -rf logs/*.log

# 4. 重新初始化
python scripts/init_database.py

# 5. 重新启动
./start-all.ps1
```

---

## 获取帮助

### 收集诊断信息

运行诊断脚本：
```bash
python scripts/collect_diagnostics.py > diagnostics.txt
```

**包含信息**：
- Python 版本和依赖
- 系统信息
- 配置文件
- 错误日志（最近 100 行）
- 数据库状态

### 提交问题

在 GitHub Issues 中提交问题时，请包含：

1. **问题描述**：详细说明问题
2. **重现步骤**：如何触发问题
3. **期望行为**：应该发生什么
4. **实际行为**：实际发生了什么
5. **环境信息**：操作系统、Python 版本等
6. **日志文件**：相关错误日志
7. **截图**：如果有界面问题

---

## 🔗 相关资源

- [配置指南](./configuration.md) - 详细配置说明
- [快速开始](./quick-start.md) - 重新部署
- [GitHub Issues](https://github.com/pocheang/querymind/issues) - 报告问题

---

<div align="center">

**问题未解决？**

[提交 Issue](https://github.com/pocheang/querymind/issues/new) · [查看文档](../INDEX.md) · [社区讨论](https://github.com/pocheang/querymind/discussions)

</div>
