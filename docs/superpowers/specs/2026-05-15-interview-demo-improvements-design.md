# 面试展示改进计划设计文档

**日期**: 2026-05-15  
**版本**: 1.0  
**状态**: 设计阶段

---

## 1. 概述

### 1.1 目标

为多智能体 RAG 系统添加面试展示功能，全面展示算法能力、工程实践和应用价值。

### 1.2 目标岗位

- AI/大模型算法工程师
- 后端/全栈工程师  
- AI 应用工程师

### 1.3 核心改进方向

1. **Agent 执行流程可视化**（高优先级）- 展示多智能体协作
2. **性能对比展示**（高优先级）- 展示系统优势
3. **中文 NLP 优化**（中优先级）- 展示本地化能力
4. **创新 RAG 技术**（中优先级）- 展示技术前瞻性

### 1.4 设计原则

- **非侵入式**：新功能作为独立模块，不修改现有核心逻辑
- **模块化**：每个服务独立，单文件 150-300 行
- **可插拔**：通过配置开关控制功能启用
- **数据驱动**：所有改进都有量化指标支撑

---

## 2. 整体架构

### 2.1 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端展示层                              │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ Agent流程可视化   │  │ 性能对比仪表板    │             │
│  │ (AgentFlow)      │  │ (Performance)    │             │
│  └──────────────────┘  └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│                   后端服务层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 执行追踪服务  │  │ 评估对比服务  │  │ 中文NLP服务   │  │
│  │ (Tracing)    │  │ (Evaluation) │  │ (ChineseNLP) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐                                       │
│  │ 创新RAG服务   │                                       │
│  │ (Advanced)   │                                       │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────┐
│              现有的多智能体RAG核心                         │
│  Router → Vector RAG → Graph RAG → Synthesis            │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 阶段一：性能对比框架（Day 1-2）

### 3.1 演示数据集

**目录结构**：
```
data/demo/
├── enterprise/          # 企业知识库场景
│   ├── hr_policy.pdf   # 人力资源政策
│   ├── it_guide.pdf    # IT操作指南
│   └── finance.pdf     # 财务制度
├── technical/          # 技术文档场景
│   ├── fastapi_docs.md # FastAPI文档
│   ├── langgraph.md    # LangGraph教程
│   └── rag_papers.pdf  # RAG相关论文
└── evaluation/
    ├── test_queries.json    # 测试查询集（20-30个）
    └── ground_truth.json    # 标准答案和相关文档
```

**测试查询示例**：
- 企业场景："年假申请流程是什么？"、"如何申请设备采购？"
- 技术场景："FastAPI如何实现流式响应？"、"Self-RAG的核心思想是什么？"

### 3.2 基线实现

**对比方案**（3个基线 + 1个完整系统）：

#### Baseline 1: 纯向量检索
- **文件**：`app/services/baseline_vector_only.py` (~150行)
- **功能**：仅使用 ChromaDB 向量检索，top_k=5
- **用途**：展示最基础的RAG效果

#### Baseline 2: 向量 + BM25
- **文件**：`app/services/baseline_hybrid.py` (~180行)
- **功能**：向量和BM25混合，简单加权融合
- **用途**：展示混合检索的提升

#### Baseline 3: 混合 + 重排序
- **文件**：`app/services/baseline_rerank.py` (~200行)
- **功能**：在Baseline 2基础上加重排序
- **用途**：展示重排序的价值

#### 完整系统
- 现有的多智能体系统

### 3.3 评估服务

**文件**：`app/services/evaluation_service.py` (~250行)

**核心功能**：
```python
class EvaluationService:
    def run_comparison(self, queries: List[Query]) -> ComparisonResult:
        """运行完整对比评估"""
        
    def evaluate_retrieval(self, retrieved_docs, ground_truth) -> Metrics:
        """计算检索指标：精确率、召回率、F1"""
        
    def evaluate_latency(self, system_name: str) -> LatencyStats:
        """测量响应时间：P50, P95, P99"""
        
    def evaluate_cost(self, system_name: str) -> CostStats:
        """统计成本：API调用次数、Token消耗"""
```

**评估指标**：
- **准确率指标**：Precision, Recall, F1, MRR
- **性能指标**：响应时间（P50, P95, P99）、吞吐量
- **成本指标**：API调用次数、Token消耗、估算成本

**API端点**：
- `POST /api/evaluation/run` - 运行评估
- `GET /api/evaluation/results` - 获取结果
- `GET /api/evaluation/compare` - 对比分析

**文件**：`app/api/routes/evaluation.py` (~150行)

---

## 4. 阶段二：Agent 执行流程可视化（Day 3-4）

### 4.1 执行追踪服务

**文件**：`app/services/agent_execution_tracker.py` (~200行)

**核心功能**：
```python
class AgentExecutionTracker:
    def start_execution(self, query: str) -> str:
        """开始追踪，返回execution_id"""
        
    def record_agent_step(self, execution_id: str, step: AgentStep):
        """记录每个Agent的执行步骤"""
        
    def get_execution_trace(self, execution_id: str) -> ExecutionTrace:
        """获取完整的执行轨迹"""
```

**数据结构**：
```python
@dataclass
class AgentStep:
    agent_name: str          # "router", "vector_rag", "graph_rag", etc.
    start_time: float
    end_time: float
    input_data: dict         # 输入参数
    output_data: dict        # 输出结果
    decision: str            # Agent的决策
    metadata: dict           # 额外信息
    status: str              # "success", "failed", "skipped"
```

**集成方式**（非侵入式）：
```python
@track_agent_execution("router")
def router_node(state: GraphState) -> GraphState:
    # 现有逻辑保持不变
    ...
```

### 4.2 前端可视化组件

**文件结构**：
```
frontend/src/components/agent-visualization/
├── AgentFlowVisualization.tsx      (~200行，主容器)
├── AgentTimeline.tsx               (~150行，时间轴)
├── AgentStepDetail.tsx             (~120行，步骤详情)
└── types.ts                        (~50行，类型定义)
```

**AgentFlowVisualization 组件**：
- 实时显示 Agent 执行流程
- 支持两种视图：流程图视图 + 时间轴视图
- 显示每个 Agent 的输入输出、执行时间、决策依据

**实时更新机制**：
- 使用 Server-Sent Events (SSE)
- 后端推送执行进度，前端实时渲染
- 支持历史查询的回放功能

### 4.3 API 端点

**文件**：`app/api/routes/agent_tracking.py` (~150行)

**端点**：
- `GET /api/agent-tracking/stream/{execution_id}` - SSE 实时推送
- `GET /api/agent-tracking/trace/{execution_id}` - 获取完整轨迹
- `GET /api/agent-tracking/history` - 历史执行记录

---

## 5. 阶段三：中文 NLP 优化（Day 5）

### 5.1 中文 NLP 服务

**文件**：`app/services/chinese_nlp_service.py` (~280行)

**核心功能模块**：

#### 1. 中文分词优化（~80行）
```python
class ChineseTokenizer:
    def __init__(self):
        self.jieba = jieba
        self.load_custom_dict()
        
    def tokenize(self, text: str) -> List[str]:
        """智能分词，支持自定义词典"""
        
    def add_domain_words(self, words: List[str]):
        """添加领域专有词汇"""
```

#### 2. 实体识别（~80行）
```python
class ChineseEntityRecognizer:
    def extract_entities(self, text: str) -> List[Entity]:
        """提取命名实体"""
        
    def extract_technical_terms(self, text: str) -> List[str]:
        """提取技术术语"""
```

#### 3. 同义词扩展（~80行）
```python
class ChineseSynonymExpander:
    def expand_query(self, query: str) -> List[str]:
        """查询扩展：年假 → [年假, 年度假期, 带薪休假]"""
        
    def load_synonyms(self) -> Dict[str, List[str]]:
        """加载同义词词典"""
```

#### 4. 语义相似度（~40行）
```python
class ChineseSemanticMatcher:
    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算中文语义相似度"""
```

### 5.2 数据文件

**领域词典**：`data/chinese_nlp/domain_dict.txt`
```
FastAPI
LangGraph
RAG
向量数据库
知识图谱
大语言模型
```

**同义词词典**：`data/chinese_nlp/synonyms.json`
```json
{
  "年假": ["年度假期", "带薪休假", "年休假"],
  "报销": ["费用报销", "财务报销"],
  "API": ["接口", "应用程序接口"]
}
```

### 5.3 集成方式

**配置开关**：
```python
ENABLE_CHINESE_NLP = True

if ENABLE_CHINESE_NLP and is_chinese_query(query):
    query = chinese_nlp.optimize_query(query)
```

**效果提升**：
- 召回率提升：15-25%
- 特别适用于中文企业文档场景

---

## 6. 阶段四：创新 RAG 技术（Day 6-7）

### 6.1 高级 RAG 服务

**文件**：`app/services/advanced_rag_service.py` (~280行)

### 6.2 Query Decomposition（查询分解）

**模块**（~140行）：
```python
class QueryDecomposer:
    def decompose(self, complex_query: str) -> List[SubQuery]:
        """将复杂查询分解为多个子查询"""
        
    def is_complex_query(self, query: str) -> bool:
        """判断是否需要分解"""
        
    def merge_results(self, sub_results: List[str]) -> str:
        """合并子查询结果"""
```

**适用场景**：
- 对比类查询："A和B有什么区别？"
- 多方面查询："从性能、安全、成本三个角度分析..."
- 复合查询："如何配置X并且确保Y？"

**示例**：
```
输入: "FastAPI和Flask在性能和易用性上有什么区别？"
输出: [
    "FastAPI的性能特点",
    "Flask的性能特点",
    "FastAPI的易用性",
    "Flask的易用性"
]
```

### 6.3 Self-RAG（自我评估）

**模块**（~140行）：
```python
class SelfRAGEvaluator:
    def evaluate_retrieval_relevance(
        self, 
        query: str, 
        documents: List[Document]
    ) -> List[RelevanceScore]:
        """评估检索文档的相关性"""
        
    def evaluate_answer_quality(
        self,
        query: str,
        answer: str,
        documents: List[Document]
    ) -> QualityScore:
        """评估生成答案的质量"""
        
    def should_retrieve_more(self, quality_score: QualityScore) -> bool:
        """判断是否需要额外检索"""
```

**工作流程**：
```
1. 初始检索 → 获取文档
2. Self-RAG评估 → 文档相关性评分
3. 过滤低分文档 → 保留高质量文档
4. 生成答案
5. Self-RAG评估答案质量
6. 如果质量不足 → 补充检索 → 重新生成
7. 返回最终答案
```

**效果**：
- 准确率提升：+10-15%
- 减少无关文档干扰
- 自动识别需要补充信息的情况

### 6.4 配置开关

```python
# .env
ENABLE_QUERY_DECOMPOSITION=true
ENABLE_SELF_RAG=true
SELF_RAG_RELEVANCE_THRESHOLD=0.6
QUERY_DECOMPOSITION_MAX_SUBQUERIES=4
```

### 6.5 性能影响

**Query Decomposition**：
- 额外延迟：+500-800ms
- 准确率提升：复杂查询 +15-20%
- 适用场景：20-30%的查询

**Self-RAG**：
- 额外延迟：+300-500ms
- 准确率提升：+10-15%
- API调用增加：+2-3次/查询

---

## 7. 性能对比展示界面

### 7.1 性能对比仪表板

**文件**：`frontend/src/components/performance-dashboard/PerformanceDashboard.tsx` (~250行)

**核心功能**：

#### 1. 系统对比视图（~80行）
- 展示4个系统的关键指标对比
- 可视化：雷达图 + 柱状图

#### 2. 详细指标面板（~80行）
- 检索质量：Precision, Recall, F1, MRR
- 响应时间：P50, P95, P99, 平均值
- 成本分析：API调用次数、Token消耗
- 缓存效率：命中率、节省的调用次数

#### 3. 查询案例对比（~90行）
- 并排展示同一查询在不同系统下的结果

### 7.2 图表库

**使用 Recharts**（轻量级，React友好）：
- 雷达图：展示多维度指标对比
- 柱状图：展示响应时间分布
- 折线图：展示精确率-召回率曲线

### 7.3 API 端点

**文件**：`app/api/routes/performance_comparison.py` (~180行)

**端点**：
- `GET /api/performance/summary` - 获取对比摘要
- `GET /api/performance/detailed/{system_name}` - 获取详细指标
- `GET /api/performance/query-examples` - 获取查询案例对比
- `POST /api/performance/run-live-comparison` - 实时运行对比测试

### 7.4 数据持久化

**目录**：`data/evaluation/results/`
```
results/
├── comparison_2026-05-15.json      # 对比结果
├── query_examples.json             # 查询案例
└── historical_trends.json          # 历史趋势
```

---

## 8. 完整文件清单

### 8.1 后端服务（7个文件）

1. `app/services/baseline_vector_only.py` (~150行)
2. `app/services/baseline_hybrid.py` (~180行)
3. `app/services/baseline_rerank.py` (~200行)
4. `app/services/evaluation_service.py` (~250行)
5. `app/services/agent_execution_tracker.py` (~200行)
6. `app/services/chinese_nlp_service.py` (~280行)
7. `app/services/advanced_rag_service.py` (~280行)

### 8.2 后端API（3个文件）

8. `app/api/routes/evaluation.py` (~150行)
9. `app/api/routes/agent_tracking.py` (~150行)
10. `app/api/routes/performance_comparison.py` (~180行)

### 8.3 前端组件（6个文件）

11. `frontend/src/components/agent-visualization/AgentFlowVisualization.tsx` (~200行)
12. `frontend/src/components/agent-visualization/AgentTimeline.tsx` (~150行)
13. `frontend/src/components/agent-visualization/AgentStepDetail.tsx` (~120行)
14. `frontend/src/components/agent-visualization/types.ts` (~50行)
15. `frontend/src/components/performance-dashboard/PerformanceDashboard.tsx` (~250行)
16. `frontend/src/pages/DemoPage.tsx` (~180行)

### 8.4 数据文件（4个）

17. `data/demo/` - 演示数据集
18. `data/chinese_nlp/domain_dict.txt` - 领域词典
19. `data/chinese_nlp/synonyms.json` - 同义词词典
20. `data/evaluation/test_queries.json` - 测试查询集

**总计**：~20个文件，每个文件 50-280 行

---

## 9. 实施时间线

| 阶段 | 时间 | 任务 | 交付物 |
|------|------|------|--------|
| 1 | Day 1-2 | 性能对比框架 | 评估服务 + 基线实现 + 数据集 |
| 2 | Day 3-4 | Agent 可视化 | 执行追踪 + 前端组件 + API |
| 3 | Day 5 | 中文 NLP 优化 | 中文服务 + 词典 + 集成 |
| 4 | Day 6-7 | 创新 RAG 技术 | Query Decomposition + Self-RAG |
| 总计 | 7天 | 完整改进 | 20个文件 + 完整演示 |

---

## 10. 面试展示亮点

### 10.1 算法能力

- **创新 RAG 技术**：Query Decomposition, Self-RAG
- **混合检索策略**：向量 + BM25 + 重排序
- **中文 NLP 优化**：分词、实体识别、同义词扩展

### 10.2 工程能力

- **模块化设计**：单文件 150-300 行，职责清晰
- **非侵入式集成**：不修改核心逻辑
- **完整的评估体系**：多维度指标、基线对比
- **性能监控**：实时追踪、历史趋势

### 10.3 应用能力

- **实际场景**：企业知识库 + 技术文档
- **可视化展示**：Agent 流程、性能对比
- **量化效果**：准确率提升 15-25%，可视化对比

### 10.4 视频展示结构（5-8分钟）

1. **开场（30秒）**：问题背景 + 解决方案
2. **核心技术（3分钟）**：多智能体协作 + 混合检索 + 知识图谱
3. **创新点（2分钟）**：分层执行 + 中文优化 + 创新RAG
4. **实际效果（2分钟）**：复杂查询演示 + 性能对比
5. **工程实践（1分钟）**：测试覆盖 + CI/CD + 安全性

---

## 11. 技术栈

### 11.1 后端

- **框架**：FastAPI
- **LLM 编排**：LangGraph
- **中文 NLP**：jieba
- **评估**：自研评估框架

### 11.2 前端

- **框架**：React + TypeScript
- **图表**：Recharts
- **实时通信**：Server-Sent Events (SSE)
- **状态管理**：React Hooks

### 11.3 依赖

```python
# 新增依赖
jieba>=0.42.1
```

```json
// 新增依赖
{
  "recharts": "^2.10.0"
}
```

---

## 12. 配置项

```bash
# .env 新增配置

# 中文 NLP
ENABLE_CHINESE_NLP=true
CHINESE_DOMAIN_DICT_PATH=data/chinese_nlp/domain_dict.txt
CHINESE_SYNONYMS_PATH=data/chinese_nlp/synonyms.json

# 创新 RAG
ENABLE_QUERY_DECOMPOSITION=true
ENABLE_SELF_RAG=true
SELF_RAG_RELEVANCE_THRESHOLD=0.6
QUERY_DECOMPOSITION_MAX_SUBQUERIES=4

# 评估
EVALUATION_DATA_DIR=data/demo
EVALUATION_RESULTS_DIR=data/evaluation/results

# Agent 追踪
ENABLE_AGENT_TRACKING=true
AGENT_TRACKING_STORAGE=data/agent_traces
```

---

## 13. 风险和缓解

### 13.1 风险

**R1: 时间压力**
- 缓解：按优先级实施，核心功能优先

**R2: 性能开销**
- 缓解：所有新功能都有开关，可按需启用

**R3: 数据准备**
- 缓解：使用小规模高质量数据集（10-20个文档）

**R4: 集成复杂度**
- 缓解：非侵入式设计，独立模块

### 13.2 回滚计划

- 所有新功能都有配置开关
- 可以快速禁用任何模块
- 不影响现有核心功能

---

## 14. 成功指标

### 14.1 功能完整性

- ✅ 4个基线系统实现
- ✅ Agent 执行流程可视化
- ✅ 性能对比仪表板
- ✅ 中文 NLP 优化
- ✅ 2个创新 RAG 技术

### 14.2 性能提升

- 准确率提升：15-25%（相比纯向量检索）
- 中文查询召回率提升：15-25%
- 复杂查询准确率提升：15-20%

### 14.3 代码质量

- 单文件代码量：150-300 行
- 模块化设计：职责清晰
- 非侵入式：不修改核心逻辑

---

## 15. 后续扩展

### 15.1 短期（1-2周）

- 添加更多评估指标（NDCG, MAP）
- 支持更多语言（英文优化）
- 添加 A/B 测试框架

### 15.2 中期（1-2月）

- 集成更多创新 RAG 技术（RAPTOR, HyDE）
- 添加用户反馈收集
- 优化性能（缓存、并发）

### 15.3 长期（3-6月）

- 多模态支持（图片、表格）
- 自动化评估流水线
- 生产环境部署

---

## 附录 A：参考资料

- Self-RAG: https://arxiv.org/abs/2310.11511
- Query Decomposition: https://arxiv.org/abs/2205.10625
- LangGraph: https://langchain-ai.github.io/langgraph/
- Recharts: https://recharts.org/

---

**文档版本**: 1.0  
**最后更新**: 2026-05-15  
**作者**: AI Assistant  
**审核状态**: 待审核
