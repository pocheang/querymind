# QueryMind 垂直领域扩展与插件开发实战指南

**面向对象：** 业务研发工程师、算法工程师 · **目标：** 5 分钟构建并挂载一个全新的垂直领域智能体与受控工具包

---

## 1. 概述与核心约定

在 QueryMind 中，扩展一个新业务领域（例如代码审计 `code_audit`、财务合规 `finance`、医疗分析 `medical` 等）**严禁修改 LangGraph 编排引擎与路由核心代码**。

新增领域扩展遵循 **Provider + Agent + Bundle** 标准三步范式：
1. **定义工具提供者** (`BaseToolProvider`)：声明受控工具元数据与异步执行函数；
2. **实现领域智能体** (`BaseSpecialistAgent`)：声明意图特征词、技能决策逻辑与候选答案生成；
3. **聚合一键注册** (`DomainExtensionBundle`)：将两者打包并调用 `register()` 完成系统级热挂载。

---

## 2. 5 分钟极速实战示例：构建“代码审计”扩展包

以实现一个基于抽象语法树与静态特征分析的 **代码审计专家 (Code Audit Specialist)** 为例：

### 第一步：编写受控工具提供者 (`provider.py`)

创建工具实现并继承 `BaseToolProvider`：

```python
# app/tools/audit/provider.py
from collections.abc import Sequence
from app.mcp.contracts import ToolDefinition, ToolParameter
from app.mcp.registry import ToolExecutor
from app.tools.base import BaseToolProvider
from app.tools.category import ToolCategory


class CodeAuditToolProvider(BaseToolProvider):
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CYBERSECURITY  # 或自定义分类

    @property
    def tool_definitions(self) -> tuple[ToolDefinition, ...]:
        return (
            ToolDefinition(
                tool_id="querymind_audit_ast_scan",
                operation="read",
                risk="read_only",
                description="执行代码 AST 静态语法树漏洞扫描（SQL注入/反序列化/硬编码秘钥）",
                parameters=(ToolParameter(name="code_snippet", description="待分析的代码片段", required=True),),
                category=self.category.value,
            ),
        )

    def get_executor(self, tool_id: str) -> ToolExecutor | None:
        if tool_id == "querymind_audit_ast_scan":

            async def _scan_code(code_snippet: str = "", **kwargs) -> dict:
                # 实现沙箱受限分析逻辑
                has_sqli = "SELECT" in code_snippet and "%" in code_snippet
                return {
                    "vulnerabilities": ["CWE-89 SQL Injection"] if has_sqli else [],
                    "risk_level": "CRITICAL" if has_sqli else "SAFE",
                }

            return _scan_code
        return None
```

---

### 第二步：编写领域智能体服务 (`service.py`)

创建智能体并继承 `BaseSpecialistAgent`，声明领域意图与研判生成逻辑：

```python
# app/agents/audit/service.py
from collections.abc import Sequence
from app.agents.base import BaseSpecialistAgent
from app.domain.contracts import ToolResult
from app.domain.workflow import CandidateAnswer, ContextBundle
from app.orchestration.request import OrchestrationRequest
from app.tools.category import ToolCategory


class CodeAuditAgentService(BaseSpecialistAgent):
    @property
    def agent_class(self) -> str:
        return "code_audit"

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("ast_vulnerability_scan", "secure_code_review")

    @property
    def default_tool_category(self) -> ToolCategory:
        return ToolCategory.CYBERSECURITY

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        return ("代码审计", "静态扫描", "源码漏洞", "sql注入", "反序列化", "硬编码")

    @property
    def intent_patterns(self) -> tuple[str, ...]:
        return (r"代码.*审计", r"静态.*分析", r"漏洞.*扫描")

    def pick_skill(self, question: str) -> str:
        text = question.lower()
        if "扫描" in text or "ast" in text:
            return "ast_vulnerability_scan"
        return "secure_code_review"

    async def synthesize_candidate(
        self,
        request: OrchestrationRequest,
        context: ContextBundle,
        tool_results: Sequence[ToolResult] | tuple[ToolResult, ...] = (),
        skill: str = "secure_code_review",
    ) -> CandidateAnswer:
        # 提取工具执行结论
        findings = "; ".join(t.summary for t in tool_results) if tool_results else "未执行自动化工具"
        # 交叉比对私有知识库文档材料证据（ContextBundle）
        doc_refs = [f"[E{i}]" for i, _ in enumerate(context.evidence, start=1)]
        ref_text = f"参考规范: {', '.join(doc_refs)}" if doc_refs else ""

        report = (
            f"### 【代码安全审计报告】\n"
            f"- 分析目标: {request.question}\n"
            f"- 触发技能: {skill}\n"
            f"- 静态扫描结果: {findings}\n"
            f"- 修复建议: 严格使用参数化查询，杜绝拼接。\n"
            f"{ref_text}"
        )
        return CandidateAnswer(text=report, citations=())
```

---

### 第三步：封装领域扩展包并执行自注册 (`bundle.py`)

使用 `DomainExtensionBundle` 将两者组合并在初始化时挂载：

```python
# app/audit_bundle.py
from app.domain.extension import DomainExtensionBundle
from app.agents.audit.service import CodeAuditAgentService
from app.tools.audit.provider import CodeAuditToolProvider

audit_bundle = DomainExtensionBundle(
    domain_id="code_audit_extension",
    display_name="源代码安全与 AST 审计扩展包",
    agent=CodeAuditAgentService(),
    tool_provider=CodeAuditToolProvider(),
)

# 在系统启动时或模块导入时执行自注册：
audit_bundle.register()
```

此时系统将自动完成：
1. `audit_bundle.tool_provider` 挂载至 MCP Gateway 运行时；
2. `audit_bundle.agent` 挂载至 `DomainAgentRegistry`；
3. 路由层自动基于 `intent_keywords` 匹配用户输入为 `agent_class="code_audit"` 并提议技能；
4. LangGraph 合成节点自动反射派发至 `CodeAuditAgentService`，全流程自动闭环！

---

## 3. 自动化集成测试编写规范

为保证新增领域扩展质量，需编写自动化单元与集成回归测试：

```python
# tests/agents/test_code_audit_bundle.py
import pytest
from app.services.agent_classifier import classify_agent_class
from app.agents.router.routing import _skill_for


def test_code_audit_dynamic_routing():
    # 验证意图自动识别
    query = "请帮我对这段 DAO 层代码进行静态代码审计与 SQL 注入扫描"
    agent_class = classify_agent_class(query)
    assert agent_class == "code_audit"

    # 验证技能自适应决策
    skill = _skill_for(agent_class, query)
    assert skill == "ast_vulnerability_scan"
```

---

## 4. 上线检查清单 (Production Checklist)

- [ ] 工具参数与返回值定义严格符合 Pydantic 规范，不包含裸 dict 动态类型；
- [ ] 工具沙箱内禁止使用 `eval()`、`exec()` 与未授权系统调用；
- [ ] 专家智能体的 `intent_keywords` 避免包含与通用问答冲突的宽泛高频词（如“帮助”、“分析”），应限定在领域特色词汇；
- [ ] 专家合成 `synthesize_candidate` 需同时处理好“工具成功”、“工具失败”与“知识库无匹配证据”三种边界分支；
- [ ] 运行 `ruff check app/ tests/` 确认 0 代码异味与 0 未引用依赖。
