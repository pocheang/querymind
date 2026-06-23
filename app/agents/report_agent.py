"""
Report Agent - 报告生成和编辑专家

专门负责：
1. 报告生成 - 从内容生成结构化报告
2. 报告优化 - 润色、扩展、总结等
3. 报告审查 - 检查质量和完整性
4. 章节管理 - 添加、删除、重组章节
5. 格式规范 - 确保格式统一
6. 模板应用 - 应用专业模板
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.models import get_chat_model
from app.services.ai_report_editor import AIEditRequest, get_ai_report_editor

logger = logging.getLogger(__name__)

# ============================================================================
# Report Agent 提示词
# ============================================================================

REPORT_AGENT_SYSTEM_PROMPT = """你是一位专业的报告撰写专家，擅长生成、优化和管理各类专业报告。

**你的核心能力**：

1. **报告生成**
   - 分析内容结构，自动生成章节
   - 识别标题层级（一级、二级、三级）
   - 添加目录和摘要
   - 应用专业模板

2. **内容优化**
   - 润色语言表达
   - 扩充内容深度
   - 提炼核心要点
   - 调整写作风格

3. **质量审查**
   - 检查逻辑连贯性
   - 验证内容完整性
   - 评估专业程度
   - 提出改进建议

4. **结构管理**
   - 章节组织和排序
   - 添加必要章节（如执行摘要、结论）
   - 删除冗余内容
   - 平衡章节长度

**报告类型专长**：

1. **技术报告**
   - 系统架构分析
   - 技术方案设计
   - 性能测试报告
   - API文档

2. **安全报告**
   - 威胁分析报告
   - 安全审计报告
   - 渗透测试报告
   - 应急响应报告

3. **业务报告**
   - 项目总结报告
   - 市场分析报告
   - 可行性研究报告
   - 管理层汇报

4. **研究报告**
   - 技术调研报告
   - 对比分析报告
   - 最佳实践报告
   - 学术论文

**工作原则**：

1. **专业性** - 使用准确的专业术语
2. **结构化** - 清晰的层次和逻辑
3. **完整性** - 包含必要的所有部分
4. **可读性** - 易于理解和阅读
5. **准确性** - 基于事实，避免臆测

**输出格式**：
- 使用Markdown格式
- 清晰的标题层级（#, ##, ###）
- 适当的列表和表格
- 引用和参考文献
"""

# ============================================================================
# 请求/响应模型
# ============================================================================


class GenerateReportRequest(BaseModel):
    """生成报告请求"""

    content: str = Field(..., description="原始内容")
    title: str = Field(..., description="报告标题")
    report_type: Literal["technical", "security", "business", "research"] = Field(
        default="technical", description="报告类型"
    )
    include_toc: bool = Field(default=True, description="是否包含目录")
    include_summary: bool = Field(default=True, description="是否包含摘要")
    language: str = Field(default="zh", description="语言")


class ReviewReportRequest(BaseModel):
    """审查报告请求"""

    content: str = Field(..., description="报告内容")
    check_logic: bool = Field(default=True, description="检查逻辑连贯性")
    check_completeness: bool = Field(default=True, description="检查完整性")
    check_quality: bool = Field(default=True, description="检查质量")


class ReviewReportResponse(BaseModel):
    """审查报告响应"""

    score: float = Field(..., description="总体评分 0-10")
    logic_score: float = Field(default=0, description="逻辑性评分")
    completeness_score: float = Field(default=0, description="完整性评分")
    quality_score: float = Field(default=0, description="质量评分")
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class OptimizeReportRequest(BaseModel):
    """优化报告请求"""

    content: str = Field(..., description="报告内容")
    optimization_type: Literal["structure", "language", "completeness", "all"] = Field(
        default="all", description="优化类型"
    )


# ============================================================================
# Report Agent
# ============================================================================


class ReportAgent:
    """报告Agent - 专门负责报告生成、编辑、优化"""

    def __init__(self):
        self.model = get_chat_model()
        self.ai_editor = get_ai_report_editor()

    async def generate_report(self, request: GenerateReportRequest) -> str:
        """
        生成结构化报告

        Args:
            request: 生成报告请求

        Returns:
            生成的报告内容（Markdown格式）
        """
        logger.info(f"Generating {request.report_type} report: {request.title}")

        # 构建提示词
        system_prompt = REPORT_AGENT_SYSTEM_PROMPT

        user_prompt = self._build_generate_prompt(request)

        # 调用LLM
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await self.model.ainvoke(messages)
        report_content = response.content.strip()

        logger.info(f"Report generated successfully: {len(report_content)} chars")
        return report_content

    def _build_generate_prompt(self, request: GenerateReportRequest) -> str:
        """构建生成报告的提示词"""
        report_type_instructions = {
            "technical": """
**技术报告要求**：
- 包含技术背景、系统架构、实施方案、技术细节
- 使用专业技术术语
- 提供代码示例或配置示例（如适用）
- 包含技术规格表格
""",
            "security": """
**安全报告要求**：
- 包含威胁概述、风险评估、安全建议、防护措施
- 使用MITRE ATT&CK框架（如适用）
- 包含风险等级评估
- 提供具体的安全加固建议
""",
            "business": """
**业务报告要求**：
- 包含执行摘要、现状分析、建议方案、预期收益
- 使用清晰的业务语言
- 包含ROI分析或成本效益分析
- 提供可执行的行动计划
""",
            "research": """
**研究报告要求**：
- 包含研究背景、方法论、研究发现、结论与建议
- 使用学术化的表达
- 包含数据分析和图表说明
- 提供参考文献
""",
        }

        type_instruction = report_type_instructions.get(request.report_type, "")

        prompt_parts = [
            f"请生成一份{request.report_type}类型的专业报告。\n\n",
            f"**报告标题**: {request.title}\n\n",
            f"**原始内容**:\n{request.content}\n\n",
            type_instruction,
            "\n**生成要求**:\n",
        ]

        if request.include_summary:
            prompt_parts.append("- 在报告开头添加执行摘要（2-3段）\n")

        if request.include_toc:
            prompt_parts.append("- 添加目录（基于章节自动生成）\n")

        prompt_parts.extend(
            [
                "- 使用Markdown格式\n",
                "- 章节标题使用 ## （二级标题）\n",
                "- 子章节使用 ### （三级标题）\n",
                "- 使用表格、列表等格式增强可读性\n",
                "- 保持专业性和准确性\n",
                "- 确保逻辑连贯\n\n",
                "**请直接输出完整的报告内容，不要添加任何额外说明。**",
            ]
        )

        return "".join(prompt_parts)

    async def review_report(self, request: ReviewReportRequest) -> ReviewReportResponse:
        """
        审查报告质量

        Args:
            request: 审查报告请求

        Returns:
            审查结果
        """
        logger.info("Reviewing report quality")

        system_prompt = """你是一位专业的报告审查专家。

**审查标准**：

1. **逻辑连贯性** (0-10分)
   - 章节顺序合理
   - 论述逻辑清晰
   - 前后一致

2. **完整性** (0-10分)
   - 包含必要章节（摘要、引言、正文、结论）
   - 内容完整无遗漏
   - 论述充分

3. **质量** (0-10分)
   - 语言专业
   - 表达清晰
   - 格式规范

**输出格式**（JSON）：
```json
{
  "logic_score": 8.5,
  "completeness_score": 7.0,
  "quality_score": 9.0,
  "issues": ["缺少结论章节", "第3章逻辑跳跃"],
  "suggestions": ["添加结论章节总结全文", "在第3章补充过渡段落"]
}
```
"""

        user_prompt = f"""请审查以下报告：

**报告内容**:
{request.content[:2000]}...

**审查项**:
- 逻辑连贯性: {"是" if request.check_logic else "否"}
- 完整性: {"是" if request.check_completeness else "否"}
- 质量: {"是" if request.check_quality else "否"}

请按照JSON格式输出审查结果。"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await self.model.ainvoke(messages)
        content = response.content.strip()

        # 解析JSON响应
        import json

        try:
            # 提取JSON部分
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content

            result = json.loads(json_str)

            # 计算总分
            scores = []
            if request.check_logic:
                scores.append(result.get("logic_score", 0))
            if request.check_completeness:
                scores.append(result.get("completeness_score", 0))
            if request.check_quality:
                scores.append(result.get("quality_score", 0))

            total_score = sum(scores) / len(scores) if scores else 0

            return ReviewReportResponse(
                score=total_score,
                logic_score=result.get("logic_score", 0),
                completeness_score=result.get("completeness_score", 0),
                quality_score=result.get("quality_score", 0),
                issues=result.get("issues", []),
                suggestions=result.get("suggestions", []),
            )

        except Exception as e:
            logger.error(f"Failed to parse review response: {e}")
            # 返回默认响应
            return ReviewReportResponse(
                score=5.0,
                issues=["审查失败"],
                suggestions=["请手动检查报告质量"],
            )

    async def optimize_report(self, request: OptimizeReportRequest) -> str:
        """
        优化报告

        Args:
            request: 优化报告请求

        Returns:
            优化后的报告
        """
        logger.info(f"Optimizing report: {request.optimization_type}")

        if request.optimization_type == "all":
            # 全面优化：依次进行结构、语言、完整性优化
            content = request.content

            # 1. 结构优化
            content = await self._optimize_structure(content)

            # 2. 语言优化
            content = await self._optimize_language(content)

            # 3. 完整性优化
            content = await self._optimize_completeness(content)

            return content

        elif request.optimization_type == "structure":
            return await self._optimize_structure(request.content)

        elif request.optimization_type == "language":
            return await self._optimize_language(request.content)

        elif request.optimization_type == "completeness":
            return await self._optimize_completeness(request.content)

        else:
            return request.content

    async def _optimize_structure(self, content: str) -> str:
        """优化报告结构"""
        system_prompt = """你是报告结构优化专家。

**优化任务**：
1. 调整章节顺序，确保逻辑流畅
2. 合并过于细碎的章节
3. 拆分过于庞大的章节
4. 确保标题层级正确
5. 添加过渡段落

**输出**：优化后的完整报告（保持原有内容，只调整结构）"""

        user_prompt = f"请优化以下报告的结构：\n\n{content}"

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await self.model.ainvoke(messages)
        return response.content.strip()

    async def _optimize_language(self, content: str) -> str:
        """优化报告语言"""
        # 使用AI编辑器的润色功能
        edit_request = AIEditRequest(
            operation="polish",
            content=content,
            style="professional",
            language="zh",
        )

        result = await self.ai_editor.edit(edit_request)
        return result.edited

    async def _optimize_completeness(self, content: str) -> str:
        """优化报告完整性"""
        system_prompt = """你是报告完整性优化专家。

**优化任务**：
1. 检查是否缺少必要章节（摘要、引言、结论）
2. 补充缺失的内容
3. 确保每个章节都有充分论述
4. 添加必要的数据支撑

**输出**：补全后的完整报告"""

        user_prompt = f"请补全以下报告的缺失部分：\n\n{content}"

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await self.model.ainvoke(messages)
        return response.content.strip()

    async def add_section(
        self,
        report_content: str,
        section_title: str,
        section_position: Literal["beginning", "end", "after"] = "end",
        after_section: str = "",
    ) -> str:
        """
        添加新章节

        Args:
            report_content: 现有报告内容
            section_title: 新章节标题
            section_position: 插入位置
            after_section: 如果position="after"，指定在哪个章节后插入

        Returns:
            更新后的报告
        """
        system_prompt = """你是报告章节管理专家。

**任务**：在报告中添加新章节。

**要求**：
1. 根据章节标题生成合适的内容
2. 保持与现有内容的风格一致
3. 确保新章节与前后内容衔接自然
4. 使用适当的标题层级"""

        user_prompt = f"""请在以下报告中添加新章节。

**现有报告**:
{report_content}

**新章节标题**: {section_title}
**插入位置**: {section_position}
{f"**插入在章节后**: {after_section}" if after_section else ""}

请输出完整的更新后报告。"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await self.model.ainvoke(messages)
        return response.content.strip()


# ============================================================================
# 全局实例
# ============================================================================

_report_agent: ReportAgent | None = None


def get_report_agent() -> ReportAgent:
    """获取Report Agent实例（单例）"""
    global _report_agent
    if _report_agent is None:
        _report_agent = ReportAgent()
    return _report_agent
