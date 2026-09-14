# 2026-09-14 技术决策 / Decisions

## D1 表格按属主隔离，而不是按租户

- **背景**：`TableStore` 以租户为键，`querymind_table_query` 是 read 工具（无需审批），同租户任何人都能查别人的私有表。
- **决定**：每张表记录 `owner_user_id / visibility / source`；每次读取都要求关键字参数 `user_id`（无默认值）。可读规则照搬向量库的 `_owner_clause`：属主、公开文档、共享语料。
- **理由**：同一份文档的两种索引必须同一套可见性规则；不设默认值，漏传就是 `TypeError` 而不是悄悄放宽——与检索链路上 `owner` 的做法一致。
- **代价**：不可见与不存在都返回 "not found"，调用方无法区分；这是有意的，区分会泄露别人持有这张表。

## D2 一张表一个内存引擎

- **背景**：每租户共用一个引擎时，`SELECT * FROM tbl_a, tbl_b` 能通过自己可见的表读到别人的表。
- **决定**：每张表独立 `TableEngine`。
- **否决方案**：在 SQL 里解析表名做白名单——SQL 解析是攻击面本身，结构上做不到才可靠。

## D3 DuckDB 关闭外部访问 + 函数黑名单两层

- `duckdb.connect(":memory:", config={"enable_external_access": False})` 是主防线，数据库打开后不可重新开启。
- `_FORBIDDEN_FUNCTIONS` 是与引擎无关的第二层，SQLite 回退路径同样受益。
- 实测 duckdb 1.5.5（用户同意安装）：`read_text` 抛 `PermissionException`，`getenv` 不存在，`SET enable_external_access = true` 被拒。

## D4 图谱描述按来源存、按来源读

- **背景**：实体节点与 `RELATED` 边按名称跨租户共享，单一 `e.description` 会把 A 的描述给 B 看。
- **决定**：实体描述放在 `MENTIONED_IN` 边上；关系描述放在 `r.source_descriptions`（`来源\x1f文本`，因为关系属性不能存 map）。
- **社区**：按来源构建，记录 `c.sources`，范围读取要求**全部**来源都在授权内；无归属的社区永不返回。
- **迁移**：不做自动迁移。旧描述留在节点/边上无人读取；运维重新摄入或调用 `POST /admin/graph-rag/communities/build`。

## D5 注入检测：判断意图，而不是词汇

- 规则要求指令对象是助手本身（"你进入开发者模式"、"act as DAN"），"忽略规则"需要限定词，危险命令需要显式执行请求。
- 理由：本系统有 `incident_response_playbook`、`cyber_attack_analysis` 技能，询问 `vssadmin delete shadows` 如何检测是本职问题。

## D6 删除聊天链路上的向量分数下限

- **测量**：`config/eval/` 16 条查询、哈希向量（新检出默认）、Chroma 自带相关度函数——无下限 16/16 保留结果，0.2 为 6/16，0.30 为 3/16。
- **决定**：`_retrieve_vector` 不设下限，删除 `similarity_search` 的 `score_threshold` 参数，`VECTOR_SIMILARITY_THRESHOLD` 默认值恢复 0.2（仅旧混合检索路径使用，且它有 0.05 的放宽重试）。
- **理由**：RRF 按名次融合、reranker 负责排序；分数跨 embedding 后端不可比，下限只会删证据。

## D7 恢复安全默认值，放宽写在环境层

- `AUTH_EXPOSE_TOKEN_IN_RESPONSE=false`、`AUTH_COOKIE_SECURE=true`、`AUTH_COOKIE_SAMESITE=strict` 恢复为代码默认；`config/env/development.env.example`、`test.env.example` 本来就放宽了，那才是放宽的位置。

## D9 表格持久化到 SQLite，引擎只是缓存

- **背景**：`TableStore` 在进程内存里：重启清空；多 worker 时只有摄入它的那个 worker 能查到，同一个问题这次能答、下次"not found"。
- **决定**：行与归属写入 `APP_DB_PATH` 的 `structured_tables` 表（每次调用自开自关连接，与仓库其他存储一致）；内存引擎是 64 个的 LRU，未命中时从数据库重建。
- **关键**：归属与版本（`updated_at`，纳秒）**每次**读取都从 SQLite 取；缓存引擎只在版本一致时使用。否则 worker A 删除后 worker B 还会继续用缓存回答。
- **测试**：pytest 下全局 store 保持内存模式（与管理员引导同一条规则：测试不写开发者的 `data/app.db`）；持久化用临时库单独测试，两个 store 实例模拟两个 worker / 重启前后。
- **否决**：外键 `REFERENCES users ON DELETE CASCADE`——共享语料没有属主，且文档本身的索引也不随账号级联；表格跟随文档删除（`delete_file_index`）而不是跟随账号。

## D10 前端格式：修到位并纳入 CI

- 198 个 prettier 告警中 82 个只是 Windows `core.autocrlf=true` 带来的 CRLF；其余 116 个是真实格式漂移。
- `.prettierrc` 改为 `endOfLine: auto`，本地与 Linux CI 结论一致；116 个文件执行 prettier；CI 增加 `npm run format:check`——CLAUDE.md 早就声称 CI 会跑它，现在才是真的。

## D8 不静默替换模型

- 删除生成失败时改用 `LocalEvidenceChatModel` 的兜底。失败就是 `generation_failed`，由合成服务给出明确标注的"证据摘要"。
