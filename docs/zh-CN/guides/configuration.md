# ⚙️ QueryMind 配置指南

> QueryMind 系统完整配置说明文档

---

## 📋 目录

- [环境配置](#环境配置)
- [后端配置](#后端配置)
- [前端配置](#前端配置)
- [数据库配置](#数据库配置)
- [LLM 模型配置](#llm-模型配置)
- [检索配置](#检索配置)
- [安全配置](#安全配置)
- [性能优化](#性能优化)

---

## 环境配置

### Python 环境

**推荐配置**：
```bash
# 创建虚拟环境
conda create -n rag-local python=3.11 -y
conda activate rag-local

# 安装核心依赖
pip install fastapi uvicorn sqlalchemy chromadb langchain
```

**环境变量**：

创建 `.env` 文件：
```bash
# Python 路径
PYTHON_PATH=/path/to/python

# 项目根目录
PROJECT_ROOT=/path/to/querymind

# 运行环境
ENVIRONMENT=development  # development / production
```

### Node.js 环境

**版本要求**：
- Node.js: >= 16.x
- npm: >= 8.x

**安装依赖**：
```bash
cd frontend
npm install
```

---

## 后端配置

### 核心配置文件

**位置**: `app/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """系统配置"""
    
    # ============ 应用配置 ============
    APP_NAME: str = "QueryMind"
    APP_VERSION: str = "0.5.0"
    DEBUG: bool = False
    
    # ============ 服务器配置 ============
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True  # 开发模式自动重载
    
    # ============ 数据库配置 ============
    DATABASE_URL: str = "sqlite:///./data/querymind.db"
    
    # ============ 向量数据库配置 ============
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "documents"
    
    # ============ LLM 配置 ============
    LLM_PROVIDER: str = "openai"  # openai / anthropic / ollama
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    
    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # ============ Embedding 配置 ============
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    EMBEDDING_DIMENSION: int = 1536
    
    # ============ 检索配置 ============
    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    RERANK_TOP_K: int = 3
    
    # 混合检索权重
    VECTOR_WEIGHT: float = 0.7
    BM25_WEIGHT: float = 0.3
    
    # ============ 文档处理配置 ============
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # ============ 安全配置 ============
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    
    # ============ Neo4j 配置 ============
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # ============ Redis 配置（可选）============
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 环境变量优先级

配置加载顺序（后者覆盖前者）：
1. 代码中的默认值
2. `.env` 文件
3. 系统环境变量
4. 命令行参数

**示例**：
```bash
# 通过环境变量覆盖配置
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3
export DEBUG=true

# 启动服务
uvicorn app.api.main:app --reload
```

---

## 前端配置

### Vite 配置

**位置**: `frontend/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
    chunkSizeWarningLimit: 1000
  }
})
```

### 环境变量

**位置**: `frontend/.env`

```bash
# API 地址
VITE_API_BASE_URL=http://localhost:8000

# 应用配置
VITE_APP_TITLE=QueryMind
VITE_APP_VERSION=0.5.0

# 功能开关
VITE_ENABLE_GRAPH=true
VITE_ENABLE_AGENT_TRACKING=true
```

**使用方式**：
```typescript
const apiUrl = import.meta.env.VITE_API_BASE_URL
```

---

## 数据库配置

### SQLite（默认）

**配置**：
```python
DATABASE_URL = "sqlite:///./data/querymind.db"
```

**初始化**：
```python
from app.db.database import engine, Base

# 创建所有表
Base.metadata.create_all(bind=engine)
```

### PostgreSQL（生产推荐）

**安装驱动**：
```bash
pip install psycopg2-binary
```

**配置**：
```python
DATABASE_URL = "postgresql://user:password@localhost:5432/querymind"
```

**连接池配置**：
```python
from sqlalchemy import create_engine

engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # 连接池大小
    max_overflow=20,        # 最大溢出连接数
    pool_timeout=30,        # 连接超时时间
    pool_recycle=3600       # 连接回收时间（秒）
)
```

### ChromaDB 向量数据库

**持久化配置**：
```python
import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="./data/chroma_db",
    anonymized_telemetry=False
))

collection = client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)
```

**内存模式**（开发）：
```python
client = chromadb.Client()
```

### Neo4j 知识图谱

**Docker 启动**：
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v $PWD/data/neo4j:/data \
  neo4j:latest
```

**配置连接**：
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "password")
)
```

---

## LLM 模型配置

### OpenAI

**配置**：
```python
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4"
OPENAI_API_KEY = "sk-..."
```

**可用模型**：
- `gpt-4` - 最强性能
- `gpt-4-turbo` - 更快速度
- `gpt-3.5-turbo` - 成本优化

**高级配置**：
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    max_tokens=2000,
    request_timeout=60,
    max_retries=3
)
```

### Anthropic Claude

**配置**：
```python
LLM_PROVIDER = "anthropic"
LLM_MODEL = "claude-3-opus-20240229"
ANTHROPIC_API_KEY = "sk-ant-..."
```

**可用模型**：
- `claude-3-opus-20240229` - 最强能力
- `claude-3-sonnet-20240229` - 平衡性能
- `claude-3-haiku-20240307` - 快速响应

### Ollama（本地部署）

**安装 Ollama**：
```bash
# macOS / Linux
curl https://ollama.ai/install.sh | sh

# Windows
# 下载安装包: https://ollama.ai/download
```

**下载模型**：
```bash
# Llama 3 (8B)
ollama pull llama3

# Qwen 2 (7B) - 中文优化
ollama pull qwen2

# Mistral (7B)
ollama pull mistral
```

**配置**：
```python
LLM_PROVIDER = "ollama"
LLM_MODEL = "llama3"
OLLAMA_BASE_URL = "http://localhost:11434"
```

**高级配置**：
```python
from langchain_community.llms import Ollama

llm = Ollama(
    model="llama3",
    base_url="http://localhost:11434",
    temperature=0.7,
    num_ctx=4096,  # 上下文长度
    num_predict=2000  # 最大生成长度
)
```

---

## 检索配置

### 向量检索参数

```python
# 检索数量
RETRIEVAL_TOP_K = 5  # 返回前5个结果

# 相似度阈值
SIMILARITY_THRESHOLD = 0.7  # 过滤低相关度结果

# 距离度量
DISTANCE_METRIC = "cosine"  # cosine / l2 / ip
```

### BM25 检索参数

```python
# BM25 参数
BM25_K1 = 1.5  # 词频饱和参数
BM25_B = 0.75  # 文档长度归一化

# 中文分词
TOKENIZER = "jieba"  # jieba / pkuseg
```

### 混合检索权重

```python
# 权重配置（总和应为1.0）
VECTOR_WEIGHT = 0.7   # 向量检索权重
BM25_WEIGHT = 0.3     # BM25检索权重

# 融合方法
FUSION_METHOD = "rrf"  # rrf / weighted_sum
```

### 重排序配置

```python
# 启用重排序
ENABLE_RERANK = True

# 重排序模型
RERANK_MODEL = "ms-marco-MiniLM-L-12-v2"

# 重排序数量
RERANK_TOP_K = 3
```

### 文档分块配置

```python
# 分块大小（字符）
CHUNK_SIZE = 1000

# 重叠大小（字符）
CHUNK_OVERLAP = 200

# 分块策略
CHUNK_STRATEGY = "recursive"  # recursive / fixed / semantic

# 分隔符
SEPARATORS = ["\n\n", "\n", "。", "！", "？", ". ", " "]
```

---

## 安全配置

### JWT 认证

```python
# 密钥配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

# Token 过期时间
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30天
```

**生成安全密钥**：
```python
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)
```

### CORS 配置

```python
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://your-domain.com"
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
```

### 速率限制

```python
# 每分钟请求限制
RATE_LIMIT_PER_MINUTE = 60

# 每小时请求限制
RATE_LIMIT_PER_HOUR = 1000
```

---

## 性能优化

### 缓存配置

**Redis 缓存**：
```python
# 启用缓存
ENABLE_CACHE = True

# Redis 配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# 缓存过期时间（秒）
CACHE_TTL = 3600  # 1小时
```

### 并发配置

**Uvicorn 工作进程**：
```bash
# 单进程（开发）
uvicorn app.api.main:app --reload

# 多进程（生产）
uvicorn app.api.main:app --workers 4 --host 0.0.0.0 --port 8000
```

**工作进程数量建议**：
```
workers = (CPU核心数 * 2) + 1
```

### 异步处理

**后台任务配置**：
```python
from fastapi import BackgroundTasks

# 文档处理任务队列
TASK_QUEUE_SIZE = 100

# 并发任务数
MAX_CONCURRENT_TASKS = 4
```

---

## 配置文件示例

### 开发环境 `.env.development`

```bash
# 应用配置
ENVIRONMENT=development
DEBUG=true

# 数据库
DATABASE_URL=sqlite:///./data/querymind.db

# LLM（使用 Ollama 本地模型）
LLM_PROVIDER=ollama
LLM_MODEL=llama3
OLLAMA_BASE_URL=http://localhost:11434

# 向量数据库
CHROMA_PERSIST_DIRECTORY=./data/chroma_db

# 前端地址
CORS_ORIGINS=["http://localhost:5173"]
```

### 生产环境 `.env.production`

```bash
# 应用配置
ENVIRONMENT=production
DEBUG=false

# 数据库
DATABASE_URL=postgresql://user:password@db-host:5432/querymind

# LLM（使用 OpenAI）
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-...

# Redis 缓存
ENABLE_CACHE=true
REDIS_HOST=redis-host
REDIS_PORT=6379

# 安全配置
SECRET_KEY=your-production-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 前端地址
CORS_ORIGINS=["https://your-domain.com"]

# 性能配置
WORKERS=4
MAX_CONCURRENT_TASKS=8
```

---

## 验证配置

### 检查配置

```python
# 运行配置检查脚本
python scripts/check_config.py
```

**输出示例**：
```
✅ 数据库连接正常
✅ LLM 配置正确
✅ 向量数据库可用
✅ Neo4j 连接成功
⚠️  Redis 未配置（可选）
```

### 测试连接

```bash
# 测试后端健康
curl http://localhost:8000/health

# 测试前端
curl http://localhost:5173
```

---

## 🔗 相关资源

- [快速开始](./quick-start.md) - 快速部署
- [API 文档](http://localhost:8000/docs) - 接口说明
- [性能优化](../../guides/PDF_PERFORMANCE_TUNING.md) - 优化指南

---

<div align="center">

**配置问题？**

[查看故障排查](./troubleshooting.md) · [提交问题](https://github.com/pocheang/querymind/issues)

</div>
