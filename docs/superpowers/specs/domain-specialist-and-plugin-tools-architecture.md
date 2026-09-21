# QueryMind 领域智能体与插件化工具架构设计规范

**文档状态：** 正式规范 · **系统版本：** v0.7.1 · **所属子系统：** 领域智能体编排与受控工具总线

---

## 1. 架构愿景与设计原则

QueryMind 作为一个企业级 Agentic RAG 与多智能体协同系统，旨在解决通用大模型在垂直企业场景（如网络安全研判、AI 与算法推演、财务与数据分析、合规审计等）中的专业度不足、工具调用失控与无法严谨对齐私有文档证据的核心痛点。

针对系统的长期可演进性与未来垂直领域无侵入扩展，架构严格遵循以下设计原则：

1. **开闭原则 (Open-Closed Principle, OCP)**：对新增垂直领域扩展完全开放，对核心 LangGraph 编排引擎与 MCP 运行时源码完全封闭。新增领域智能体及其专属工具时，无需修改任何核心路由、规划或合成节点代码。
2. **双层插件化 (Dual-layer Plugin Architecture)**：在“工具层 (Tool Layer)”与“智能体层 (Agent Layer)”建立对齐的抽象契约与中心化自省注册表，支持单体独立插拔与成对聚合打包。
3. **证据盲区安全模型 (Evidence-Blind Security Model)**：工具选择过程严格隔离自私有检索文档（防止 Prompt Injection 与间接越狱），工具执行沙箱严格受限（AST 语法树白名单，禁用 eval/exec），多租户数据权限在首节点前置固化。
4. **双流交叉研判闭环 (Dual-Stream Cross-Verification)**：垂直专家合成必须同时对齐**私有知识库文档证据（Document RAG Context）**与**实时受控工具结果（Governed Tool Results）**，形成双源事实相互印证与严格可溯源的证据引用体系。

---

## 2. 领域扩展核心实体与类图

系统通过领域驱动设计（DDD）划分核心边界，建立如下标准化抽象层：

```
                           ┌─────────────────────────────────────┐
                           │       DomainExtensionBundle         │
                           │  (领域扩展包: Agent + ToolProvider) │
                           └──────────────────┬──────────────────┘
                                              │ bundle.register()
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
      ┌─────────────────────────────┐                   ┌─────────────────────────────┐
      │     DomainAgentRegistry     │                   │     DomainToolRegistry      │
      │  (专家 Agent 统一单例注册中心)│                   │   (工具 Provider 统一注册中心)│
      └──────────────┬──────────────┘                   └──────────────┬──────────────┘
                     │                                                 │
                     ▼ get_agent(agent_class)                          ▼ register_all_into()
      ┌─────────────────────────────┐                   ┌─────────────────────────────┐
      │  LangGraph synthesizer Node │                   │   MCP ToolRegistry 运行时    │
      │  (动态多态策略派发，零 if/else)│                   │      (受控受限工具执行)      │
      └─────────────────────────────┘                   └─────────────────────────────┘
```

### 2.1 工具层契约与分类 (Tool Layer)
- **`ToolCategory(StrEnum)`**：标准化的领域分类枚举，涵盖：
  - `CYBERSECURITY`: 网络安全与威胁情报（CVE、ATT&CK、IoC）
  - `ARTIFICIAL_INTELLIGENCE`: AI 与算法计算（FLOPs、显存预估、超参）
  - `DATA_ANALYSIS`: 数据分析与统计（SQL 沙箱、指标计算）
  - `WEB_SEARCH`: 互联网合规检索
  - `KNOWLEDGE_GRAPH`: 知识图谱与实体关联
  - `SYSTEM`: 系统状态监控与探针
  - `GENERAL`: 通用基础工具
- **`BaseToolProvider(ABC)`**：工具插件提供者基类，规范了 `category`、`tool_definitions`、`get_executor(tool_id)` 与 `register_into(registry)`。
- **`DomainToolRegistry`**：全局线程安全注册中心，负责维护各分类的 Provider 列表并统一向 MCP Gateway 运行时导出所有受控工具。

### 2.2 智能体层契约与意图 (Agent Layer)
- **`BaseSpecialistAgent(ABC)`**：垂直领域专家智能体基类，规范了：
  - `agent_class`: 领域标识字符串（如 `"cybersecurity"`、`"artificial_intelligence"`）；
  - `supported_skills`: 专家能够处理的技能标识元组；
  - `default_tool_category`: 默认关联的工具分类枚举；
  - `intent_keywords` / `intent_patterns`: 领域意图特征词与正则，供路由层动态识别；
  - `pick_skill(question)`: 专家自主根据问题语义提议最适技能；
  - `synthesize_candidate(request, context, tool_results, skill)`: 融合文档证据与工具结果的深度专业生成。
- **`DomainAgentRegistry`**：全局单例专家注册中心，负责维护专家集合、技能倒排索引，并提供 `match_agent_class(question)` 与 `pick_skill_for_agent(agent_class, question)` 动态分发。

### 2.3 领域聚合包 (DomainExtensionBundle)
- **`DomainExtensionBundle`**：高内聚领域包，封装了一个专家的 `agent` 与对应的 `tool_provider`。第三方只需执行 `bundle.register()`，即实现工具上架 MCP、智能体挂载注册表与路由动态识别的一体化交付。

---

## 3. 端到端全生命周期执行闭环

当终端用户发起一次业务请求时，系统各节点协同流转如下：

```
 1. 用户提问 (含潜在注入或 PII)
      │
      ▼
┌───────────────────────────────────────┐
│ SecurityGuardrail (统一前置安全护栏)   │ ──> 字符反混淆 / Prompt Injection 防御 / PII 掩码脱敏
└──────────────────┬────────────────────┘
                   │ 安全清洗输入
                   ▼
┌───────────────────────────────────────┐
│ RouterAgentService (动态路由分类)     │ ──> 动态扫描 DomainAgentRegistry 元数据
└──────────────────┬────────────────────┘     判定 agent_class 与自主选择最适 skill
                   │ 意图与技能决策
                   ▼
┌───────────────────────────────────────┐
│ Planner & Knowledge (知识与规划层)    │ ──> 并行召回企业私有知识库文档切片 (ContextBundle)
└──────────────────┬────────────────────┘     自适应感知工具权能并分配 tool 预算 (PlannedTask)
                   │ 文档证据流
                   ▼
┌───────────────────────────────────────┐
│ ToolAgentService (受控工具执行层)     │ ──> ToolSelector 依据用户词句决策受控工具 (Evidence-Blind)
└──────────────────┬────────────────────┘     MCP 沙箱安全执行，返回结构化结果 (ToolResult)
                   │ 工具证据流
                   ▼
┌───────────────────────────────────────┐
│ SpecialistAgent (领域专家合成层)      │ ──> LangGraph 多态反射分发至目标领域专家
└──────────────────┬────────────────────┘     双流交叉比对文档 [E1] 与工具发现，产出研判报告
                   │ 结构化候选答案
                   ▼
┌───────────────────────────────────────┐
│ Verifier & Finalizer (验证与交付层)   │ ──> NLI 事实一致性核验、思维链防泄露过滤、最终交付
└───────────────────────────────────────┘
```

---

## 4. 安全防护与隔离机制 (Security & Isolation)

1. **输入防御与脱敏闭环**：
   - 采用 `TextDeobfuscator` 执行同形字攻击检测与 Unicode NFKC 归一化；
   - 在图执行首节点对所有输入进行 OWASP LLM01 注入威胁分析；
   - 自动识别手机号、身份证、API Key 与密码哈希，打上 `[REDACTED]` 标签。
2. **受限执行沙箱**：
   - 所有数学与算力计算必须通过 AST 白名单沙箱（严禁 Python `eval()`、`exec()` 或外部 `import`），杜绝执行逃逸。
3. **多租户数据隔离 (AccessScope)**：
   - 用户角色权限（Admin、Analyst、Viewer）通过不可伪造的上下文传递，知识库检索强制携带 Scope 下沉过滤，杜绝越权访问。
