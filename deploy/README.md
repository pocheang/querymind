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

[ARC-01 修复计划](../docs/querymind-deep-dive/arc-01-plan.html)完成前，后端只能以 1 个 worker 运行。限流、审批令牌、执行事件流、会话写入和文档摄取已经可以共享（阶段 0–5，需 `STATE_BACKEND=shared`），但各进程的缓存还不会跨进程失效（阶段 6），多个进程同时启动时建表还会互相冲突（阶段 7）。

- 设置 `APP_WORKERS` 大于 1 时，应用拒绝启动。
- 这个检查只看 `APP_WORKERS` 这个**声明值**：用 `uvicorn --workers N` 启动却没设 `APP_WORKERS`，检查发现不了，所以两者要保持一致。
- 隔离舱和断路器将来也是每个 worker 各一份，放开多 worker 后，相关并发上限要按 worker 数平分。
- `STATE_BACKEND` 决定需要跨 worker 共享的状态放在哪里：默认 `memory`（现状）；设为 `shared` 时，启动时 `REDIS_URL` 必须能连通，否则拒绝启动。设为 `shared` 后，登录、注册、上传限流，查询守卫，OAuth state 和中间件 IP 限流都只存在 Redis 里；Redis 不可用时这些接口返回 503（带 `Retry-After`），不再退回按进程计数。审批令牌、工具审计和管理员一次性令牌的使用记录不受这个开关影响，一律存在 `app.db`。执行事件流（SSE）也走 Redis：订阅可以落在任意 worker 上。会话历史必须用 `HISTORY_BACKEND=sqlite`、会话元数据必须用 `SESSION_METADATA_BACKEND=database`，否则 `shared` 拒绝启动；原来用文件保存的会话，先运行 `python scripts/migrate_sessions_to_sqlite.py --dry-run` 查看，再去掉 `--dry-run` 导入（可重复执行，不删除原文件，不覆盖已有记录）。长期记忆不需要手动迁移：每个用户的记忆存在其 `_long_memory/memory.db` 里，旧的 JSON 文件在第一次访问时自动导入（只导入一次，原文件保留）。共享模式下还需要 Chroma 服务端（`CHROMA_SERVER_URL`，否则拒绝启动）和唯一一个 `ingest-worker`（`python -m app.ingest_worker`）：用 `-f compose.shared-state.yaml` 叠加即可。已有向量先运行 `python scripts/migrate_chroma_to_server.py --dry-run` 查看，再导入（原样复制、不重新计算、可重复执行）。重建索引现在排队执行，接口返回 202；删除仍是即时的，但若正好有写入在进行，最多等 `INDEX_LOCK_REQUEST_TIMEOUT_SECONDS`（默认 5 秒）后返回 503，稍后重试即可。`APP_WORKERS` 目前仍然必须是 1。`/agent-tracking/*` 这组调试接口按设计只能看到本 worker 的记录。当前生效的状态后端和各个 Redis 连接的状态，可以在管理员接口 `GET /ready/dependencies` 返回的 `state` 字段里查看。

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
