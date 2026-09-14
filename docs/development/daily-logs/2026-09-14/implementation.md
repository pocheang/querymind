# 2026-09-14 实现记录 / Implementation

## 审查发现 → 修复对照

| # | 问题 | 修复位置 | 回归测试 |
|---|---|---|---|
| 1 | 认证默认值被调弱 | `app/core/config.py` | 既有 auth 测试 |
| 2 | API Key / URL 可在管理台编辑并回显 | `app/core/config_schema.py` | `tests/core/test_config_schema.py`（原本失败） |
| 3 | 表格跨用户读取、跨表 JOIN、删文档不删表 | `app/services/tables/store.py`、`app/mcp/runtime.py`、`app/services/documents/{ingest,index_manager}.py` | `tests/tables/test_table_sql_engine.py` 新增 6 项 |
| 4 | DuckDB 可读服务器文件 | `app/services/tables/engine.py` | 同上，参数化 5 种函数 + 字面量测试 |
| 5 | 注入检测误拦正常问题 | `app/services/security/injection_defense.py` | 误拦清单 9 项 + 执行请求 3 项 |
| 6 | NL2SQL 同步调用阻塞事件循环 | `app/mcp/runtime.py`（`asyncio.to_thread`） | — |
| 7 | 社区摘要 / 实体描述跨租户 | `app/graph/knowledge/{client,community}.py` | `tests/graph/test_rich_graph_rag.py` 新增跨来源测试 |
| 8 | 生成失败静默改用离线模型 | `app/agents/synthesizer/generation.py` | — |
| 9 | 管理端社区构建阻塞事件循环 | `app/api/routes/admin/graph_rag.py` | — |
| 10 | 规划预算被抬高 | `app/agents/knowledge/service.py` | `test_retrieval_width.py`（原 2 项失败 + 新增 1 项） |
| 11 | provider 缓存不随重载失效 | `app/api/application/config_reload.py` | — |
| 12 | xlsx 合并单元格 DoS | `app/ingestion/loaders/office_loader.py` | `tests/ingestion/test_xlsx_merged_range_guard.py`（4 项） |
| 13 | 检索内容决定图谱查询实体 | `app/knowledge/adapters.py`、`app/agents/rag/{graph,enhanced_graph}.py`、`app/tools/graph/enhanced.py` | `tests/hybrid/test_graph_table_hybrid.py` 改写 |
| 14 | `sanitize_answer` 报告形状变化、图片外链子串绕过 | `app/services/answer_safety.py`、`injection_defense.py` | `test_answer_safety.py`（原 3 项失败）+ 主机判定 4 项 |
| + | 聊天链路向量分数下限 0.30 | `app/knowledge/adapters.py`、`app/retrievers/stores/vector.py`、`config.py` | `tests/knowledge/test_vector_source_has_no_score_floor.py`（2 项） |
| + | 表格只在进程内存（重启清空、多 worker 不一致） | `app/services/tables/store.py`（SQLite 后端 + 引擎 LRU） | `tests/tables/test_table_store_persistence.py`（6 项） |
| + | SQL 改写把与表同名的列也改成表名（`SUM(sales)` → `SUM("tbl_sales")`） | `app/services/tables/store.py`（只改写 FROM / JOIN 位置） | `test_a_column_that_shares_its_tables_name_is_not_rewritten` |
| + | 前端 116 个文件格式漂移，CI 从未跑 `format:check` | `frontend/.prettierrc`（`endOfLine: auto`）、116 个文件、`.github/workflows/ci.yml` | CI 新增 Format check 步骤 |

## 推送前 `make test-ci` 发现的问题

按 CLAUDE.md「推送前跑 `make test-ci`」执行（本机无 `make`，直接跑同一条命令），并把 `CHROMA_PERSIST_DIR` /
`APP_DB_PATH` 指向全新的临时目录，模拟 CI 的干净检出：

| 问题 | 修复 |
|---|---|
| `openpyxl` / `pandas` / `xlrd` / `duckdb` 不在 `requirements/ci.txt`，两个新测试文件在模块顶层 `from openpyxl import Workbook`，CI 会在收集阶段报错 | 加入 `scripts/ci_import_environment.py` 的 `BLOCKED_IMPORTS`；Excel 场景改为 `pytest.importorskip`，CSV / Markdown 场景照常运行 |
| 真实场景测试把表格写进开发者的 `data/chroma`（本机是 1024 维 BGE 库，CI 模拟用 384 维哈希向量，维度冲突） | 自动 fixture 用记录型替身替换 `get_named_vector_store` |
| 4 个既有测试同样因本机 Chroma 维度失败 | 用全新数据目录重跑 30/30 通过——属本机环境，与本次改动无关 |
| `query_table_with_graph_entities` 测试非密封：自然语言问题落到本机配置的模型（开发机可能是真实远程模型） | 测试打桩 `get_chat_model`；实现的兜底 SQL 改为在所有文本列上匹配实体（原来只查第一列，通常是 ID 列） |

结果：CI 模拟 1,960 passed / 3 skipped（Excel 场景）/ 0 failed。

## 表格持久化的实测

- 两个独立进程（非 pytest，真实 `get_table_store()`，DuckDB 1.5.5，`APP_DB_PATH` 指向会话临时库）：
  写进程保存 → 读进程查询得到 `3000`；其他用户 `not found`；读进程删除后，再起一个进程查询为 `not found`。
- 只读检查开发者的 `data/app.db`：没有 `structured_tables` 表——测试与验证都没有写入它。

## 关键实现细节

- **xlsx 守卫**：openpyxl 全量模式在加载时就为每个合并单元格创建 `MergedCell`，我们自己的守卫来不及执行。
  现在先从压缩包里**流式**扫描 `<mergeCell ref=...>` 求声明面积（每块 1MB、跨块保留 256 字节尾巴、
  扫描上限 256MB 防解压炸弹），超过 20 万单元格或文件超过 20MB 就走只读模式、不做前向填充。
- **关系描述分隔符**：`_DESC_SEP = "\x1f"`。第一次写入时控制字符以原始字节落盘（可用但不可见），已改成转义写法。
- **社区 ID**：`comm_{sha256(source)[:12]}_{序号}`，同一来源重建前先删除旧社区，避免序号缩减时残留节点和 `BELONGS_TO` 边。
- **格式化**：29 个文件 `ruff format`；前端只对本次改动的 6 个文件跑 prettier（全仓 198 个文件的历史格式问题不在本次范围）。

## 遇到的问题

- 沙箱禁止写 `%TEMP%\pytest-of-pocheang`，使用 `tmp_path` 的 4 个测试报 `PermissionError`；用 `--basetemp` 指向会话临时目录后全部通过。属于环境问题，不是代码问题。
- `conda run python -c` 不支持多行脚本，改为写脚本文件执行。
