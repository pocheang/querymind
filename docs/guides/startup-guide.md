# 项目启动指南

## 快速启动

### 方式 1：一键启动（推荐）
```powershell
.\start-all.ps1
```
会自动启动前后端服务，打开两个 PowerShell 窗口。

### 方式 2：分别启动

**启动后端：**
```powershell
.\start-backend.ps1
```

**启动前端：**
```powershell
.\start-frontend.ps1
```

## 服务地址

- **前端**：http://localhost:5173
- **后端**：http://localhost:8000
- **后端健康检查**：http://localhost:8000/health
- **后端 API 文档**：http://localhost:8000/docs

## 环境要求

### 后端
- Python 环境：`C:\Users\pocheang\anaconda3\envs\rag-local`
- 主要依赖：FastAPI, Uvicorn, LangChain

### 前端
- Node.js 和 npm
- 主要依赖：React, Vite, TypeScript

## 故障排查

### 后端启动失败

1. **检查 Python 环境**
   ```powershell
   C:\Users\pocheang\anaconda3\envs\rag-local\python.exe --version
   ```

2. **检查依赖是否安装**
   ```powershell
   C:\Users\pocheang\anaconda3\envs\rag-local\python.exe -m pip list
   ```

3. **手动启动测试**
   ```powershell
   cd c:\Users\pocheang\Desktop\llm\multi_agent_rag_local_v4
   C:\Users\pocheang\anaconda3\envs\rag-local\python.exe -m uvicorn app.api.main:app --reload
   ```

### 前端启动失败

1. **重新安装依赖**
   ```powershell
   cd frontend
   Remove-Item -Recurse -Force node_modules
   npm install
   ```

2. **清理缓存**
   ```powershell
   npm cache clean --force
   ```

### 端口被占用

**检查端口占用：**
```powershell
# 检查 8000 端口（后端）
netstat -ano | findstr :8000

# 检查 5173 端口（前端）
netstat -ano | findstr :5173
```

**结束占用进程：**
```powershell
# 替换 <PID> 为实际进程 ID
Stop-Process -Id <PID> -Force
```

## 配置文件位置

- **后端配置**：`app/core/config.py`
- **前端配置**：`frontend/vite.config.ts`
- **环境变量**：`.env` 文件（如果存在）

## 开发模式特性

### 后端（Uvicorn）
- 自动重载：代码修改后自动重启
- 热重载：无需手动重启服务

### 前端（Vite）
- 热模块替换（HMR）：代码修改后即时更新
- 快速冷启动：秒级启动速度

## 停止服务

- **方式 1**：关闭 PowerShell 窗口
- **方式 2**：在窗口中按 `Ctrl+C`

## 注意事项

1. **不要同时运行多个实例**：确保端口 5173 和 8000 没有被占用
2. **首次启动**：前端首次启动会自动安装依赖，需要等待几分钟
3. **网络要求**：前端需要访问后端 API，确保两个服务都在运行
4. **数据持久化**：数据存储在本地，重启服务不会丢失数据

## 生产部署

生产环境部署请参考：
- 后端：使用 Gunicorn + Uvicorn workers
- 前端：运行 `npm run build` 生成静态文件

详细部署文档请查看项目根目录的 `DEPLOYMENT.md`（如果存在）。
