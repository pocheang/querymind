# Graph RAG + PDF 优化总结

## 日期
2026-06-17

## 当前结论
这批 Graph RAG + PDF 优化已经从“原型代码存在”推进到“主链路可启用、关键降级可验证、脚本反馈更清晰”的状态，但仍然不适合宣称为生产级完成。

更准确地说：

- 增强版 Graph RAG 已接入主调用链路，并可通过配置开关启用
- 常规图检索路径和增强版 hybrid 路径都能消费向量检索返回的 PDF 上下文
- 低质量 PDF 现在可以触发跳过图谱查询的降级逻辑
- PDF 实体抽取已补上中英文噪声过滤，明显减少章节词、长中文句段误判
- `stats` 命令在 Neo4j 不可用时会明确提示“服务不可用 + 下一步动作”
- 真实效果增益、吞吐影响和生产数据验证仍未完成

---

## 已完成修复

### 1. 主链路已真正接入增强版

已完成接入的文件包括：

- `app/agents/graph_rag_agent.py`
- `app/graph/nodes/safe_wrappers.py`
- `app/graph/streaming/safe_wrappers.py`
- `app/graph/nodes/graph_node.py`
- `app/graph/streaming/stream_processor.py`
- `app/graph/nodes/vector_node.py`
- `app/core/config.py`
- `.env.example`

当前配置：

```env
GRAPH_RAG_ENHANCED=false
GRAPH_RAG_MIN_PDF_QUALITY=0.3
```

行为说明：

- `GRAPH_RAG_ENHANCED=false` 时，继续走原始 Graph RAG
- `GRAPH_RAG_ENHANCED=true` 时，启用 PDF 感知增强版
- 当检索到的文档质量低于 `GRAPH_RAG_MIN_PDF_QUALITY` 时，会跳过图谱查询并返回降级结果

### 2. hybrid 路径已能利用向量结果作为图谱上下文

当前行为：

- 增强版开启时，hybrid 路径采用“先向量、后图谱”的上下文增强模式
- 图谱阶段会消费向量结果中的 `citations`，从而得到 PDF 质量分析和实体上下文
- 增强版关闭时，仍保留原先的并行 hybrid 路径

这解决了此前 hybrid 图谱分支看不到 PDF 检索上下文的问题。

### 3. PDF 实体抽取质量已做一轮实质收敛

已修复文件：

- `app/agents/graph_rag_agent_enhanced.py`
- `tests/test_graph_rag_agent_enhanced.py`

本轮修复内容：

- 增加英文章节噪声过滤，避免把 `Introduction`、`Overview`、`Description`、`References` 之类词误判为实体
- 增加中文技术术语优先提取，优先识别如“大语言模型”“自然语言处理”“检索增强生成”“智能客服系统”
- 限制中文宽匹配，减少把长句片段直接当实体的情况
- 保持去重且尽量保留出现顺序

当前结论：

- 相比之前明显更适合作为查询增强候选
- 但本质上仍是启发式候选提取，不等同于严格的 NER

### 4. 优化脚本已改为更真实的 Neo4j 不可用反馈

已修复文件：

- `scripts/optimize_graph_rag_accuracy.py`
- `tests/test_graph_rag_optimizer_script.py`

修复后：

- `analyze` / `extract` 仍可在未启动 Neo4j 时运行
- `stats` 在 Neo4j 不可用时不再输出“像成功但没数据”的空统计
- 现在会明确输出：
  - `status: unavailable`
  - 具体错误类型
  - “请先启动 Neo4j”的提示
  - 建议动作 `docker compose up -d neo4j`

### 5. Windows 下的脚本与示例输出已可稳定运行

已修复文件：

- `scripts/test_graph_rag_optimization.py`
- `examples/graph_rag_optimization_quickstart.py`
- `scripts/optimize_graph_rag_accuracy.py`

修复内容：

- 增加 UTF-8 stdout/stderr 配置
- 避免控制台编码导致脚本打印阶段直接失败

---

## 已完成验证

### pytest

本轮通过：

- `tests/test_graph_rag_agent_enhanced.py`
- `tests/test_graph_rag_agent.py`
- `tests/test_workflow_fixes.py`
- `tests/test_streaming_detected_language.py`
- `tests/test_graph_rag_optimizer_script.py`
- `tests/test_streaming_analytics_logging.py`
- `tests/test_graph_tools_enhancement.py`

结果：`30 passed`

### 脚本验证

已验证可运行：

- `python scripts/test_graph_rag_optimization.py`
- `python scripts/optimize_graph_rag_accuracy.py stats`

当前 `stats` 在 Neo4j 未启动时会明确输出不可用状态和下一步建议，而不是空结果。

---

## 仍然存在的问题

### 1. 实体抽取仍然是启发式，不是生产级识别

虽然本轮已经修掉最明显的章节词和长句误判，但当前方案依然主要依赖规则和术语模式：

- 适合做 Graph RAG 查询增强
- 不适合宣传为“已经解决实体识别准确率问题”

### 2. 增强版 hybrid 仍以正确性优先

增强版 hybrid 当前采用串联模式，因此权衡仍然存在：

- 上下文质量更高
- 图谱阶段能真正利用 PDF 文档信号
- 但不再保留原并行路径的最低延迟特征

### 3. 缺少真实业务数据上的基准结论

目前仍未完成：

- 真实 PDF 数据集的 A/B 对比
- 真实召回率 / 准确率统计
- 生产负载下的延迟基准

因此以下说法仍不能当作已验证结论：

- “高质量 PDF 提升 15-25%”
- “减少 20-30% 不必要图谱查询”
- “总增量开销仅 15-35ms”

这些最多只能算待验证假设。

---

## 建议口径

建议把当前状态描述为：

> Graph RAG + PDF 增强能力已完成主链路接入、配置开关控制、关键降级与脚本反馈修复，并已完成定向测试验证；但实体抽取仍属启发式增强，真实效果收益、性能表现与生产级验证仍待补齐。

---

## 下一步建议

### 优先级高

1. 给增强版补一组真实 PDF 样本回归测试
2. 在真实数据上做召回率、准确率和延迟 A/B
3. 评估是否需要把增强版 hybrid 做成“正确性优先 / 延迟优先”双模式

### 优先级中

1. 用更稳的中文术语/实体抽取方案替换当前纯规则方法
2. 把 `GRAPH_RAG_ENHANCED` 与 `GRAPH_RAG_MIN_PDF_QUALITY` 写入更完整的用户文档
3. 逐步把 `scripts/test_graph_rag_optimization.py` 中的 demo 检查迁移为正式 pytest

---

## 状态

`部分完成，已接入并可验证，关键问题已收敛，待真实数据与生产验证`
