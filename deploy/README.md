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

## 多 worker 部署

从 ARC-01 阶段 9 起，生产部署默认就是多 worker：镜像用 gunicorn 管理 `APP_WORKERS` 个 uvicorn worker（生产配置层默认 2 个，`deploy/gunicorn.conf.py`），Compose 默认 `STATE_BACKEND=shared`，同一个 `compose.yaml` 里包含 Redis、Chroma 服务端、一次性的 `init` 服务和唯一一个 `ingest-worker`。原来的 `compose.shared-state.yaml` 叠加文件已并入并删除。

**第一次部署阶段 9 之前先停栈：`docker compose down`（绝不加 `-v`，那会删掉所有数据卷），再运行部署脚本。**网络现在固定了子网，而已存在、配置没变的容器（redis、chroma）会继续指向旧网络的 ID，启动时报 `network ... not found`——验证环境里实测到过。`down` 删除的是容器和网络，数据卷全部保留。

- **拒绝启动的条件**：`APP_WORKERS` 大于 1 且 `STATE_BACKEND` 不是 `shared`。gunicorn 和 `Settings` 读的是同一个 `APP_WORKERS`，二者不会不一致。想回到单进程，在 shell 里设 `STATE_BACKEND=memory` 和 `APP_WORKERS=1` 后再 `up`（Compose 的 `environment:` 优先于 `env_file:`，所以要在 shell 里设）。
- **卡死的 worker 会被换掉**：worker 的心跳由事件循环驱动，事件循环卡住超过 `GUNICORN_TIMEOUT_SECONDS`（默认 60 秒）时 gunicorn 杀掉它并启动新的。慢请求在线程里执行，不会阻塞心跳。
- **升级不需要手动迁移**：`init` 服务先跑完 SQLite 迁移、首个管理员和旧配置清理，然后在 shared 模式下把单 worker 时代的数据搬到 shared 模式读取的位置：文件会话导入 SQLite，嵌入式 Chroma 目录里的向量原样复制到 Chroma 服务端，两者都回读核对。成功后分别在会话目录写 `.migrated-to-sqlite`、在 Chroma 目录写 `.migrated-to-chroma-server`，之后的部署直接跳过；源数据不删除。核对失败时 `init` 以非零状态退出，backend 和 ingest-worker 不会启动，原因在 `docker compose logs init` 里。要强制重跑某一项，删掉对应的标记文件。`scripts/migrate_sessions_to_sqlite.py` 和 `scripts/migrate_chroma_to_server.py` 仍然可以手动运行（支持 `--dry-run`）。
- **客户端地址**：前端 nginx 用它看到的地址**覆盖** `X-Forwarded-For`（不再追加客户端自己发来的值），后端只接受来自 `QUERYMIND_TRUSTED_PROXIES` 的这个头。Compose 把它设为 `querymind` 网络的子网 `QUERYMIND_SUBNET`（默认 `172.29.72.0/24`），与主机已有网络冲突时在 shell 里改掉；每一项必须是合法的地址或网段，写错时进程拒绝启动，而不是悄悄谁都不信任。限流、审计日志里的 IP 都来自这里。变量名不用 uvicorn 的 `FORWARDED_ALLOW_IPS`：gunicorn 在导入时也读这个变量，并且不接受网段，放子网进去所有 worker 都起不来（实测）。
- **SSE**：nginx 对执行事件流和 agent-tracking 流单独配置了 `proxy_buffering off`，事件逐条到达，不会攒成一批。事件本身存在 Redis 里，订阅落在哪个 worker 上都可以。
- **管理后台经 `/api` 可用**：生产环境 nginx 只代理 `/api/`，之前 `admin`、`user`、`model-catalog` 三组接口没有 `/api` 前缀的别名，整个管理后台在生产环境返回 404。另外 `/api` 前缀的改写现在是最外层的中间件：它原来在最内层，限流中间件看到的是 `/api/auth/register`，匹配不到任何规则——生产环境里前端发出的登录、注册请求从来没有被中间件限流过（实测：同一地址 6 次注册全部成功，修复后第 4 次起返回 429）。
- **指标**：镜像设置了 `PROMETHEUS_MULTIPROC_DIR=/tmp/querymind-metrics`，每个 worker 写自己的文件，`/metrics` 一次返回整个容器的汇总；不设置时（本地单进程）用进程内注册表。`config/observability/prometheus/alert_rules.yml` 里的每条规则都对应真实存在的指标，文件头列出了各指标与已删除的规则。运行时面板、概览的请求数字、系统日志和熔断器状态是处理本次请求的那个 worker 的，界面上标有 pid。
- **数据库初始化**：`python -m app.init_app` 把所有 SQLite 存储迁移到最新版本（版本记在各库的 `schema_versions` 表里），然后创建首个管理员、清理旧的个人模型配置。它作为一次性 `init` 服务先运行，backend 和 ingest-worker 等它成功退出后才启动；因此 **`ADMIN_USERNAME` / `ADMIN_PASSWORD` 要设置在 `init` 服务上**，自动生成的管理员密码出现在 `docker compose logs init` 里。每个后端进程启动时也会执行同一段代码作为兜底，库已是最新时只做几次读取。已有的库原地升级，不需要任何手动步骤；库的版本比代码新（回退了镜像）时拒绝启动。`deploy.sh` / `deploy.ps1` 不再单独执行初始化，由 `init` 服务负责；它失败时脚本停下并提示查看 `logs init`。
- 在镜像之外自己起进程时（例如 `uvicorn --workers N`），启动检查只看 `APP_WORKERS` 这个**声明值**，没设 `APP_WORKERS` 就发现不了，所以两者要保持一致。镜像里用 gunicorn，不存在这个问题。
- 隔离舱和断路器是每个 worker 各一份，相关并发上限要按 worker 数平分。
- `STATE_BACKEND` 决定需要跨 worker 共享的状态放在哪里：应用本身默认 `memory`（本地单进程开发），Compose 部署默认 `shared`；为 `shared` 时，启动时 `REDIS_URL` 必须能连通，否则拒绝启动。设为 `shared` 后，登录、注册、上传限流，查询守卫，OAuth state 和中间件 IP 限流都只存在 Redis 里；Redis 不可用时这些接口返回 503（带 `Retry-After`），不再退回按进程计数。审批令牌、工具审计和管理员一次性令牌的使用记录不受这个开关影响，一律存在 `app.db`。执行事件流（SSE）也走 Redis：订阅可以落在任意 worker 上。会话历史必须用 `HISTORY_BACKEND=sqlite`、会话元数据必须用 `SESSION_METADATA_BACKEND=database`，否则 `shared` 拒绝启动（Compose 已设好）。原来用文件保存的会话和嵌入式向量由 `init` 自动迁移，见上文。长期记忆不需要迁移：每个用户的记忆存在其 `_long_memory/memory.db` 里，旧的 JSON 文件在第一次访问时自动导入（只导入一次，原文件保留）。共享模式下还需要 Chroma 服务端（`CHROMA_SERVER_URL`，否则拒绝启动）和唯一一个 `ingest-worker`（`python -m app.ingest_worker`），两者都在 `compose.yaml` 里。Redis 保留 AOF 持久化：它现在存着摄取队列和待确认的审批，不只是缓存。重建索引排队执行，接口返回 202；删除仍是即时的，但若正好有写入在进行，最多等 `INDEX_LOCK_REQUEST_TIMEOUT_SECONDS`（默认 5 秒）后返回 503，稍后重试即可。`/agent-tracking/*` 这组调试接口按设计只能看到本 worker 的记录。当前生效的状态后端和各个 Redis 连接的状态，可以在管理员接口 `GET /ready/dependencies` 返回的 `state` 字段里查看。

## 本地开发

```bash
./deploy/scripts/deploy.sh development fast
```

开发环境使用 `config/env/development.env.example` 作为覆盖层，后端在 `127.0.0.1:8000`，前端在 `127.0.0.1:5173`。本地 Conda 环境仍使用 `rag-local`。

只想在本机跑 uvicorn、让 Compose 提供依赖时，`make up` 启动 Neo4j（`127.0.0.1:7474` / `7687`）、Redis（`127.0.0.1:6379`，密码是 `.runtime/development.env` 里的 `REDIS_PASSWORD`）和 Chroma 服务端（`127.0.0.1:8001`，因为 8000 留给后端）。要在本地试 shared 模式，把 `REDIS_URL` 和 `CHROMA_SERVER_URL=http://localhost:8001` 指过去。

多进程集成测试（`tests/integration/multiworker/`，ARC-01 阶段 10）自己启动 init、一个 ingest-worker 和两个 API 进程，但需要真正的 Redis 和 Chroma 服务端（fakeredis 的 TCP 服务端跨进程时阻塞读不正确）。`make up` 之后：

```bash
QM_INTEGRATION_REDIS_URL="redis://:<REDIS_PASSWORD>@127.0.0.1:6379/0" QM_INTEGRATION_CHROMA_URL=http://127.0.0.1:8001 pytest tests/integration/multiworker -q
```

不设置这两个变量时这组测试整体跳过并说明原因。每次运行使用独立的键前缀和 Chroma 集合，结束时清理，不影响同一 Redis 上的其他数据。

## 配置目录

- `compose/`：生产基线、开发覆盖和监控覆盖。
- `scripts/`：配置渲染、初始化和健康检查。
- `../config/`：环境模板、运行策略、应用配置和可观测性配置。
- `../.runtime/`：仅由脚本生成的最终配置和密钥。

规范目录：deploy/compose/ 保存 Compose 编排，deploy/scripts/ 保存部署脚本。
