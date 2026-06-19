# 🚀 项目启动指南

**版本**: v0.4.5  
**日期**: 2026-06-17  
**状态**: ✅ 已更新并准备运行

---

## ✅ 已完成的更新

### 1. 配置文件更新 ✅
```env
# 已添加到 .env:
CACHE_TTL_FAST_TIER=300
CACHE_TTL_BALANCED_TIER=120
CACHE_TTL_DEEP_TIER=60
CACHE_TTL_USER_QUERY=180

BM25_USE_CHINESE_TOKENIZER=true

QUERY_RATE_LIMIT_ADMIN=100
QUERY_RATE_LIMIT_PREMIUM=60
QUERY_RATE_LIMIT_USER=30
```

### 2. 测试验证 ✅
```
✅ 44 tests passed
✅ 4 warnings (Pydantic deprecation, 不影响功能)
```

### 3. 数据库备份 ✅
初始备份已创建到 `data/backups/`

---

## 🚀 启动项目

### 方式1: 开发模式（推荐）

#### 1. 启动后端
```bash
# 激活环境
conda activate rag-local

# 启动FastAPI服务器（带热重载）
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-include "*.py"
```

#### 2. 启动前端（新终端）
```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

#### 3. 访问应用
- **前端**: http://localhost:5173/app
- **后端API**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

### 方式2: 生产模式

#### 1. 构建前端
```bash
cd frontend
npm run build
```

#### 2. 启动后端（生产）
```bash
conda activate rag-local
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 🔍 启动后验证

### 1. 检查后端健康状态
```bash
curl http://localhost:8000/health
# 应返回: {"status":"healthy"}
```

### 2. 测试查询分析工具
```bash
python scripts/query_analytics.py --days 7
```

### 3. 验证备份
```bash
python scripts/backup_database.py --list
```

---

## 🛠️ 常用命令

### 开发命令
```bash
# 运行所有测试
pytest -q

# 运行特定测试
pytest tests/test_custom_exceptions.py -v

# 查看代码覆盖率
pytest --cov=app --cov-report=html

# 代码检查
ruff check app/
```

### 数据库管理
```bash
# 手动备份
python scripts/backup_database.py

# 压缩备份
python scripts/backup_database.py --compress

# 查看所有备份
python scripts/backup_database.py --list

# 恢复数据库
python scripts/backup_database.py --restore data/backups/app_db_20260617_120000.db
```

### 查询分析
```bash
# 查看最近7天统计
python scripts/query_analytics.py

# 查看最近30天
python scripts/query_analytics.py --days 30

# 详细模式
python scripts/query_analytics.py --detailed

# 导出数据
python scripts/query_analytics.py --export stats.json
```

### 版本管理
```bash
# 升级版本号
python scripts/bump_version.py 0.4.6

# 查看当前版本
python -c "from app.__version__ import __version__; print(__version__)"
```

---

## 🐛 故障排查

### 后端启动失败

**问题**: `ModuleNotFoundError`
```bash
# 解决方案：确保环境激活并安装依赖
conda activate rag-local
pip install -e .
```

**问题**: `Neo4j connection failed`
```bash
# 解决方案：启动Neo4j
docker compose up -d neo4j
```

**问题**: `ChromaDB permission denied`
```bash
# 解决方案：检查data目录权限
chmod -R 755 data/
```

### 前端启动失败

**问题**: `npm: command not found`
```bash
# 解决方案：安装Node.js
# 访问 https://nodejs.org/ 下载安装
```

**问题**: `EADDRINUSE: port 5173 already in use`
```bash
# 解决方案：使用其他端口
npm run dev -- --port 5174
```

### 测试失败

**问题**: 某些测试失败
```bash
# 解决方案：检查依赖是否完整
pip install -e ".[dev]"

# 清理缓存重试
pytest --cache-clear tests/
```

---

## 📊 性能优化建议

### 1. Ollama配置（本地模型）
```bash
# 确保Ollama正在运行
ollama list

# 下载推荐模型
ollama pull qwen2.5:7b-instruct
ollama pull all-minilm
```

### 2. Redis缓存（可选）
```bash
# 启动Redis以获得更好的缓存性能
docker compose up -d redis

# 或本地安装
# Windows: https://github.com/microsoftarchive/redis/releases
# Linux: sudo apt install redis-server
```

### 3. 预热优化
```python
# 首次启动后预热jieba分词器
python -c "import jieba; jieba.initialize()"
```

---

## 🔐 安全检查清单

启动生产环境前，请确认：

- [ ] `.env`文件未被提交到Git
- [ ] `AUTH_COOKIE_SECURE=true` （生产环境）
- [ ] 修改了Neo4j默认密码
- [ ] 设置了合理的限流配置
- [ ] 配置了数据库自动备份
- [ ] 启用了HTTPS（生产环境）

---

## 📝 启动后检查

启动成功后，验证以下功能：

1. **前端访问**: http://localhost:5173/app
2. **用户注册/登录**: 创建测试账号
3. **文档上传**: 上传一个测试PDF
4. **查询测试**: 进行一次查询
5. **中文查询**: 测试中文检索效果
6. **查询统计**: 运行 `python scripts/query_analytics.py`

---

## 🎉 准备就绪

所有优化已完成并配置好，现在可以：

```bash
# 终端1: 启动后端
conda activate rag-local
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload

# 终端2: 启动前端
cd frontend
npm run dev
```

**访问**: http://localhost:5173/app

---

## 📚 更多信息

- **完整文档**: [docs/project/COMPLETE_SUMMARY.md](docs/project/COMPLETE_SUMMARY.md)
- **快速清单**: [docs/project/QUICK_CHECKLIST.md](docs/project/QUICK_CHECKLIST.md)
- **API文档**: http://localhost:8000/docs（启动后访问）

---

**版本**: v0.4.5  
**更新时间**: 2026-06-17  
**状态**: ✅ 准备就绪
