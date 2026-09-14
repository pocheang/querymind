# 2026-09-14 完成总结 / Summary

## 一句话

v0.7.0.1 合并前审查发现 14 个问题（其中 4 个是隔离失效），全部修复；随后又闭环了三项遗留：
向量分数下限回退、DuckDB 实测、表格持久化，并把前端格式漂移修到位、纳入 CI。现在可以合并。

## 完成情况

| 项 | 状态 |
|---|---|
| 审查发现 14 项 | 14 / 14 已修复 |
| 额外发现：向量分数下限 0.30 | 已回退，附测量与回归测试 |
| 额外发现：SQL 改写把与表同名的列改成表名 | 已修复，附回归测试 |
| 表格持久化（重启 / 多 worker） | 已完成：SQLite 后端 + 引擎 LRU，双进程实测 |
| DuckDB 实测（用户同意安装 duckdb 1.5.5） | 完成 |
| 前端格式（116 个文件漂移 + 82 个仅 CRLF） | 已修复，CI 新增 `format:check` |
| SonarCloud 门禁（7 个阻断项） | 已通过 |
| SonarCloud 可靠性开放问题（10 × S8786 + 2 × S6772） | 已修复，逐个与旧式比对 |
| 原本失败的测试 | 11 → 0 |
| ruff 错误 / 格式问题 | 46 / 29 → 0 / 0 |
| 发布文档（CHANGELOG / 发布说明 / 版本历史 / CLAUDE.md / releases 索引 / README） | 已更正 |

## 验证结果

- **后端 `pytest -q` → 1,991 passed, 0 failed**（本日开始时 1,910 passed / 11 failed）；`test-ci` 1,985 passed / 3 skipped
- **前端**：vitest 154 passed；eslint 0 errors（19 warnings，棘轮 20）；`tsc -b --noEmit`、`format:check`、`lint:design`、`build`、`lint:classes` 全部通过
- `ruff check .` / `ruff format --check .` → 通过
- 敏感内容门禁（已跟踪 + 新文件）→ PASS
- OpenAPI 操作数 → **157**（新增 `POST /admin/graph-rag/communities/build`，基线由 156 更新）
- 实测：
  - 同租户跨用户读表：修复前 `SELECT * FROM tbl_a, tbl_b` 返回别人的行；修复后表不存在
  - DuckDB 引擎层（绕过校验直接执行）：`read_text` → `PermissionException`，`getenv` 不存在，`SET enable_external_access = true` 被拒
  - 注入检测：6 个正常问题修复前全部被拦，修复后全部放行；执行请求形式的危险命令仍被拦截
  - 向量下限：`config/eval/` 16 条查询在哈希向量下，无下限 16/16，0.2 为 6/16，0.30 为 3/16
  - 表格持久化：两个独立进程（非 pytest、DuckDB）写入 → 另一进程查询得 3000 → 其他用户 not found → 删除后下一个进程 not found；开发者 `data/app.db` 只读检查无 `structured_tables`

## 留给后续

- 预发布版本写入的图谱描述仍在节点/边上无人读取，内存模式下摄入过的表格也未落库；运维需重新摄入，或调用 `POST /admin/graph-rag/communities/build`（发布说明已写明）。
- 表格不随账号级联删除，而是随文档删除（与向量索引一致）；若将来要求"注销即清除全部数据"，需要统一设计。

## 经验教训

- **"验证可以失败"再次救场**：DuckDB 读文件风险最初只能靠推理；装上真实引擎、绕过校验直接执行，才证明防线在引擎层。
- **新加的"质量阈值"要先测**：0.30 看似温和，但分数跨 embedding 后端不可比，在默认后端上等于关掉向量检索。
- **持久化的测试写法决定它能不能发现问题**：用两个 store 实例模拟两个 worker，第一次运行就抓到了一个与持久化无关、但一直潜伏的 SQL 改写缺陷。
- **"CI 会跑"要以 workflow 为准**：CLAUDE.md 声称 CI 跑 `format:check`，实际没有，116 个文件因此漂移；Windows 下另有 82 个文件只是 CRLF 噪声。
