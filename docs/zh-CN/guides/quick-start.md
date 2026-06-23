# 🚀 QueryMind 快速开始指南

> 5分钟快速体验 QueryMind 企业级智能问答引擎

---

## 📋 前置要求

### 系统要求
- **操作系统**: Windows 10/11, macOS, Linux
- **Python**: 3.11 或更高版本
- **Node.js**: 16.x 或更高版本
- **内存**: 最低 8GB，推荐 16GB
- **硬盘**: 至少 10GB 可用空间

### 必需软件
- [Anaconda](https://www.anaconda.com/download) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- [Node.js](https://nodejs.org/) 和 npm
- [Git](https://git-scm.com/)

---

## 🎯 快速启动（3步）

### 第 1 步：克隆项目

```bash
git clone https://github.com/pocheang/querymind.git
cd querymind
```

### 第 2 步：环境配置

**创建 Conda 环境：**
```bash
conda create -n rag-local python=3.11 -y
conda activate rag-local
```

**安装后端依赖：**
```bash
pip install -r requirements.txt
```

**安装前端依赖：**
```bash
cd frontend
npm install
cd ..
```

### 第 3 步：启动服务

**方式 1：一键启动（Windows 推荐）**
```powershell
.\start-all.ps1
```

**方式 2：手动启动**

终端 1 - 启动后端：
```bash
conda activate rag-local
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

终端 2 - 启动前端：
```bash
cd frontend
npm run dev
```

---

## 🌐 访问应用

启动成功后，访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🎨 **前端界面** | http://localhost:5173 | 用户交互界面 |
| 🔧 **后端 API** | http://localhost:8000 | RESTful API 服务 |
| 📝 **API 文档** | http://localhost:8000/docs | Swagger 接口文档 |
| ❤️ **健康检查** | http://localhost:8000/health | 服务状态检查 |

---

## 👤 首次使用

### 1. 注册账号

访问 http://localhost:5173，点击"注册"按钮：
- **用户名**: 输入你的用户名（3-20字符）
- **密码**: 设置密码（至少6位）
- **角色**: 选择 `Viewer`（只读）或 `Analyst`（完全访问）

### 2. 登录系统

使用注册的账号登录系统。

### 3. 上传文档

1. 进入"文档管理"页面
2. 点击"上传文档"按钮
3. 选择支持的文件类型：
   - 📄 PDF
   - 📝 TXT
   - 📊 Markdown
   - 📃 Word (DOCX)

### 4. 开始提问

1. 进入"聊天"页面
2. 在输入框输入你的问题
3. 查看 AI 生成的答案和引用来源

---

## 🎨 核心功能体验

### 🔍 智能问答
```
问题示例：
- "总结文档的主要内容"
- "文档中提到了哪些关键技术？"
- "解释XXX的工作原理"
```

### 🤖 多智能体追踪
- 进入"代理追踪"页面
- 实时查看智能体执行流程
- 了解查询如何被路由和处理

### 📊 知识图谱
- 进入"知识图谱"页面
- 可视化查看实体关系
- 探索知识网络结构

### 📈 性能分析
- 进入"分析"页面
- 查看检索统计和性能指标
- 对比不同检索策略效果

---

## ⚙️ 基础配置

### API 密钥配置

如需使用云端 LLM 服务，配置 API 密钥：

**方式 1：环境变量**
```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# Anthropic Claude
export ANTHROPIC_API_KEY="your-api-key"
```

**方式 2：配置文件**

编辑 `app/core/config.py`：
```python
OPENAI_API_KEY = "your-api-key"
ANTHROPIC_API_KEY = "your-api-key"
```

### 使用本地模型（Ollama）

1. **安装 Ollama**:
   ```bash
   # macOS/Linux
   curl https://ollama.ai/install.sh | sh
   
   # Windows
   # 下载安装包: https://ollama.ai/download
   ```

2. **下载模型**:
   ```bash
   ollama pull llama3
   ollama pull qwen2
   ```

3. **配置使用**:
   在 `app/core/config.py` 中设置：
   ```python
   LLM_PROVIDER = "ollama"
   LLM_MODEL = "llama3"
   ```

---

## 🐛 常见问题

### 问题 1：后端启动失败

**症状**: `ModuleNotFoundError` 或依赖错误

**解决**:
```bash
conda activate rag-local
pip install -r requirements.txt --upgrade
```

### 问题 2：前端页面空白

**症状**: 浏览器显示空白页面

**解决**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

详细故障排查：[故障排查指南](./troubleshooting-black-screen.md)

### 问题 3：端口被占用

**症状**: `Address already in use`

**解决**:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

### 问题 4：ChromaDB 连接错误

**症状**: 向量数据库连接失败

**解决**:
```bash
# 清理并重建数据库
rm -rf data/chroma_db
python scripts/init_database.py
```

---

## 📚 下一步

### 📖 深入学习
- [完整配置指南](./CONFIGURATION_GUIDE.md) - 详细配置说明
- [API 设置指南](./API_SETTINGS_GUIDE.md) - API 配置教程
- [系统架构](./development/ARCHITECTURE.md) - 了解系统设计

### 🎨 功能探索
- [多智能体系统](../features/agents/README.md) - Agent 协作机制
- [混合检索策略](../features/rag/README.md) - RAG 技术详解
- [PDF 处理功能](../features/pdf/README.md) - PDF 文档处理

### 💻 开发进阶
- [开发环境搭建](./development/SETUP_GUIDE.md) - 开发配置
- [API 开发指南](./development/API_DEVELOPMENT.md) - 后端开发
- [前端开发指南](./development/FRONTEND_DEVELOPMENT.md) - 前端开发

---

## 🤝 获取帮助

- 📋 **问题反馈**: [GitHub Issues](https://github.com/pocheang/querymind/issues)
- 📖 **完整文档**: [文档中心](../zh-CN/INDEX.md)
- 💬 **技术交流**: 提交 Issue 或 Pull Request

---

## 📊 性能建议

### 开发环境
- CPU: 4核心或更多
- 内存: 8GB 最低，16GB 推荐
- 磁盘: SSD 存储

### 生产环境
- CPU: 8核心或更多
- 内存: 32GB 推荐
- 磁盘: NVMe SSD
- 网络: 千兆网络

---

<div align="center">

**祝你使用愉快！ 🎉**

[返回文档中心](../zh-CN/INDEX.md) · [查看更新日志](../../CHANGELOG.md) · [GitHub 仓库](https://github.com/pocheang/querymind)

</div>
