# 2026-09-18 实现记录 / Implementation

分支 `claude/backend-config-issues-frrwir`，PR #25，七个 commit。

## 代码改动

| 文件 | 改动 |
|---|---|
| `app/evaluation/metrics.py` | 分级相关性（`_grades`）、修正 `ndcg_at_k`、新增 `precision_ceiling_at_k` 与 `complete_at_k`，去掉 sklearn |
| `app/evaluation/models.py` | `TestQuery.relevance` 可选分级映射 + `graded_relevance()` |
| `app/evaluation/retrieval_eval.py` | `RetrievalScore` 增加 recall/ndcg/ceiling/complete/missing；`measure()` 可配 sources 与 rerank；`KNOWN_INCOMPLETE_CROSSDOC` |
| `app/evaluation/preflight.py` | **新增**：全链路评测的拒绝条件 |
| `scripts/eval_retrieval.py` | `--queries`、报告重排序、印出缺失文档、`query_set_path` 路径容器 |
| `scripts/eval_full_pipeline.py` | **新增**：向量 + BM25 + 重排，缺模型则退出 2 |
| `config/eval/retrieval_corpus.jsonl` | 15 → 30 篇（新增 15 篇 `role: secondary`） |
| `config/eval/retrieval_queries_crossdoc.json` | **新增**：8 个跨文档问题 |
| `config/eval/retrieval_queries.graded.example.json` | **新增**：分级标注样例 |
| `Makefile` | `eval-crossdoc`、`eval-full-pipeline` |

## 测得的数字

```
            主集合            跨文档集合
recall@5    1.0000（钉死）    0.8958
MRR         0.9167            0.9375
nDCG@5      0.9375            0.8459
complete@5  1.0000            0.7500   ← 八题里两题答不了
P@5         0.2000 = 上限     0.4000 < 上限 0.4500
```

## `ndcg_at_k` 的两处错误（改动前实测）

```
3 篇相关，命中 1 篇在第 1 位  ->  报 1.0,    正确 0.4693
1 篇相关，命中在第 2 位       ->  报 0.4871, 正确 0.6309
1 篇相关，命中在第 1 位       ->  报 1.0,    正确 1.0
```

理想排序是拿**检索到的** label 排的，所以完全漏掉的相关文档进不了分母；
另外 `ndcg_score(y_true, y_score)` 被喂了排序后的 label 当 `y_true`。
只有第三行是对的，而现有语料几乎全是那个形状。该指标是活的：
`POST /api/evaluation/run` 经 `calculate_all_metrics` 会走到。

## 干扰文档暴露的缺陷

`q-13` 从第 1 掉到第 3，`q-15` 从 2 掉到 3，三个候选的 RRF 分紧挨着（1/61、1/62、1/63）。

机制是 **BM25 长度归一化**：gold 是长的那篇，因为真正回答问题比提一嘴它的主题要多用字。
`q-07` 是证明这一点的对照组——它是 `q-13` 加上「可以结转吗」，而「结转」全语料只有一篇有，
gold 立刻跳回第 1。

同一个缺陷在跨文档集合上变成硬失败：`x-08` 丢的正是 `nianjia.md`，掉出前五，问题直接答不了。

## 验证

- `pytest -q -p scripts.ci_import_environment`：2,470 passed / 3 skipped / 2 xfailed
- `ruff check` / `ruff format --check` 干净；敏感内容闸门 PASS
- 认知复杂度：`app/` 与 `scripts/` 无函数 > 15
- 覆盖率 60.6%（基线 60.2%，容差内）
