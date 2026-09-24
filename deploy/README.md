# 部署入口

`deploy/` 是 QueryMind 的独立部署目录，集中放置 Compose 编排、运行时初始化、健康检查和一键部署脚本。

## 一键部署

Linux/macOS/WSL：

```bash
export OPENAI_API_KEY="your-api-key"
./deploy/scripts/deploy.sh production balanced
```

PowerShell：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
.\deploy\scripts\deploy.ps1 -Environment production -Profile balanced
```

脚本会在 `.runtime/` 中生成环境配置和随机密钥，校验 Compose 配置，构建并启动服务，初始化应用数据库并执行后端健康检查。`.runtime/` 不应提交到 Git。

可选参数：`--monitoring` / `-Monitoring` 启用 Prometheus、Alertmanager、Grafana；`--with-n8n` / `-WithN8n` 启用 n8n。

## Worker 数量约束

[ARC-01 修复计划](../docs/querymind-deep-dive/arc-01-plan.html)完成前，后端只能以 1 个 worker 运行。限流器、审批令牌、执行事件流和会话锁仍在进程内，多 worker 会让限流失效、审批令牌无法兑换、SSE 返回 404。

- 设置 `APP_WORKERS` 大于 1 时，应用拒绝启动。
- 这个检查只看 `APP_WORKERS` 这个**声明值**：用 `uvicorn --workers N` 启动却没设 `APP_WORKERS`，检查发现不了，所以两者要保持一致。
- 隔离舱和断路器将来也是每个 worker 各一份，放开多 worker 后，相关并发上限要按 worker 数平分。

## 本地开发

```bash
./deploy/scripts/deploy.sh development fast
```

开发环境使用 `config/env/development.env.example` 作为覆盖层，后端在 `127.0.0.1:8000`，前端在 `127.0.0.1:5173`。本地 Conda 环境仍使用 `rag-local`。

## 配置目录

- `compose/`：生产基线、开发覆盖和监控覆盖。
- `scripts/`：配置渲染、初始化和健康检查。
- `../config/`：环境模板、运行策略、应用配置和可观测性配置。
- `../.runtime/`：仅由脚本生成的最终配置和密钥。

规范目录：deploy/compose/ 保存 Compose 编排，deploy/scripts/ 保存部署脚本。
