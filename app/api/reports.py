"""
报告生成、编辑和导出功能 (Report Generation, Editing & Export)

功能需求：
1. 用户可以将Agent回答内容生成为报告
2. 用户可以编辑报告内容（所见即所得编辑器）
3. 用户可以下载报告为Markdown文件
4. 支持报告模板和格式化
5. 支持多种导出格式（MD, PDF, DOCX）

技术栈：
- 后端：FastAPI + Markdown生成
- 前端：React + Markdown编辑器
- 导出：Markdown, Pandoc (PDF/DOCX)
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ============================================================================
# 数据模型
# ============================================================================

ReportFormat = Literal["markdown", "pdf", "docx", "html"]


class ReportSection(BaseModel):
    """报告章节"""

    id: str = Field(..., description="章节唯一ID")
    title: str = Field(..., description="章节标题")
    content: str = Field(..., description="章节内容（Markdown格式）")
    order: int = Field(..., description="章节顺序")
    level: int = Field(default=1, description="标题级别 1-6")
    metadata: dict[str, Any] = Field(default_factory=dict, description="章节元数据")


class ReportMetadata(BaseModel):
    """报告元数据"""

    title: str = Field(..., description="报告标题")
    author: str = Field(default="", description="作者")
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"), description="日期")
    version: str = Field(default="1.0", description="版本号")
    tags: list[str] = Field(default_factory=list, description="标签")
    description: str = Field(default="", description="报告描述")


class Report(BaseModel):
    """完整报告"""

    id: str = Field(..., description="报告唯一ID")
    metadata: ReportMetadata = Field(..., description="报告元数据")
    sections: list[ReportSection] = Field(..., description="报告章节列表")
    template: str = Field(default="standard", description="报告模板")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class CreateReportRequest(BaseModel):
    """创建报告请求"""

    title: str = Field(..., description="报告标题")
    content: str = Field(..., description="初始内容")
    author: str = Field(default="", description="作者")
    template: str = Field(default="standard", description="模板名称")
    auto_structure: bool = Field(default=True, description="自动结构化内容")


class UpdateReportRequest(BaseModel):
    """更新报告请求"""

    metadata: ReportMetadata | None = None
    sections: list[ReportSection] | None = None


class ExportReportRequest(BaseModel):
    """导出报告请求"""

    report_id: str = Field(..., description="报告ID")
    format: ReportFormat = Field(..., description="导出格式")
    include_toc: bool = Field(default=True, description="包含目录")
    include_metadata: bool = Field(default=True, description="包含元数据")


# ============================================================================
# 报告生成器
# ============================================================================


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.templates = {
            "standard": self._standard_template,
            "technical": self._technical_template,
            "executive": self._executive_template,
            "security": self._security_template,
        }

    def create_report(
        self,
        title: str,
        content: str,
        author: str = "",
        template: str = "standard",
        auto_structure: bool = True,
    ) -> Report:
        """
        创建报告

        Args:
            title: 报告标题
            content: 初始内容
            author: 作者
            template: 模板名称
            auto_structure: 是否自动结构化

        Returns:
            Report对象
        """
        # 生成报告ID
        report_id = self._generate_report_id(title)

        # 创建元数据
        metadata = ReportMetadata(
            title=title,
            author=author,
            date=datetime.now().strftime("%Y-%m-%d"),
            version="1.0",
        )

        # 结构化内容
        if auto_structure:
            sections = self._structure_content(content)
        else:
            sections = [
                ReportSection(
                    id=f"section-{report_id}-0",
                    title="内容",
                    content=content,
                    order=0,
                    level=2,
                )
            ]

        # 创建报告
        report = Report(
            id=report_id,
            metadata=metadata,
            sections=sections,
            template=template,
        )

        return report

    def _generate_report_id(self, title: str) -> str:
        """生成报告ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_str = hashlib.md5(f"{title}{timestamp}".encode()).hexdigest()[:8]
        return f"report-{timestamp}-{hash_str}"

    def _structure_content(self, content: str) -> list[ReportSection]:
        """
        自动结构化内容为章节

        识别标题、段落、列表等结构
        """
        sections: list[ReportSection] = []

        # 按行分割
        lines = content.split("\n")

        current_section: dict[str, Any] | None = None
        section_order = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测Markdown标题
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                # 保存上一个section
                if current_section and current_section.get("content"):
                    sections.append(
                        ReportSection(
                            id=f"section-{section_order}",
                            title=current_section["title"],
                            content=current_section["content"].strip(),
                            order=section_order,
                            level=current_section["level"],
                        )
                    )
                    section_order += 1

                # 创建新section
                level = len(heading_match.group(1))
                title = heading_match.group(2)
                current_section = {
                    "title": title,
                    "content": "",
                    "level": level,
                }
            else:
                # 添加到当前section
                if current_section is None:
                    # 如果还没有section，创建一个默认的
                    current_section = {
                        "title": "概述",
                        "content": "",
                        "level": 2,
                    }

                current_section["content"] += line + "\n"

        # 保存最后一个section
        if current_section and current_section.get("content"):
            sections.append(
                ReportSection(
                    id=f"section-{section_order}",
                    title=current_section["title"],
                    content=current_section["content"].strip(),
                    order=section_order,
                    level=current_section["level"],
                )
            )

        return (
            sections
            if sections
            else [
                ReportSection(
                    id="section-0",
                    title="内容",
                    content=content,
                    order=0,
                    level=2,
                )
            ]
        )

    def _standard_template(self, report: Report) -> str:
        """标准模板"""
        return f"""# {report.metadata.title}

**作者**: {report.metadata.author or "未知"}
**日期**: {report.metadata.date}
**版本**: {report.metadata.version}

---

"""

    def _technical_template(self, report: Report) -> str:
        """技术报告模板"""
        return f"""# {report.metadata.title}

## 文档信息

| 项目 | 内容 |
|------|------|
| 作者 | {report.metadata.author or "未知"} |
| 日期 | {report.metadata.date} |
| 版本 | {report.metadata.version} |
| 标签 | {", ".join(report.metadata.tags) if report.metadata.tags else "无"} |

## 摘要

{report.metadata.description or "本文档为技术报告。"}

---

"""

    def _executive_template(self, report: Report) -> str:
        """高管报告模板"""
        return f"""# {report.metadata.title}

## 执行摘要

**编制**: {report.metadata.author or "未知"}
**日期**: {report.metadata.date}

{report.metadata.description or "本报告提供关键信息概览。"}

---

"""

    def _security_template(self, report: Report) -> str:
        """安全报告模板"""
        return f"""# {report.metadata.title}

## 安全报告

**报告编号**: {report.id}
**分析人员**: {report.metadata.author or "未知"}
**报告日期**: {report.metadata.date}
**报告版本**: {report.metadata.version}

**机密级别**: 内部使用

---

## 免责声明

本报告仅供内部参考，未经授权不得外传。

---

"""


# ============================================================================
# 报告导出器
# ============================================================================


class ReportExporter:
    """报告导出器"""

    def __init__(self):
        self.generator = ReportGenerator()

    def export_markdown(
        self,
        report: Report,
        include_toc: bool = True,
        include_metadata: bool = True,
    ) -> str:
        """
        导出为Markdown

        Args:
            report: 报告对象
            include_toc: 是否包含目录
            include_metadata: 是否包含元数据

        Returns:
            Markdown文本
        """
        md_parts: list[str] = []

        # 1. 标题和元数据（使用模板）
        if include_metadata:
            template_func = self.generator.templates.get(report.template, self.generator._standard_template)
            md_parts.append(template_func(report))
        else:
            md_parts.append(f"# {report.metadata.title}\n\n---\n\n")

        # 2. 目录
        if include_toc:
            md_parts.append(self._generate_toc(report.sections))
            md_parts.append("\n---\n\n")

        # 3. 章节内容
        for section in sorted(report.sections, key=lambda s: s.order):
            # 标题
            heading = "#" * section.level
            md_parts.append(f"{heading} {section.title}\n\n")

            # 内容
            md_parts.append(f"{section.content}\n\n")

        # 4. 页脚
        md_parts.append(self._generate_footer(report))

        return "".join(md_parts)

    def _generate_toc(self, sections: list[ReportSection]) -> str:
        """生成目录"""
        toc_lines = ["## 目录\n"]

        for section in sorted(sections, key=lambda s: s.order):
            indent = "  " * (section.level - 2) if section.level > 2 else ""
            # 生成锚点链接
            anchor = section.title.lower().replace(" ", "-")
            anchor = re.sub(r"[^\w\-]", "", anchor)
            toc_lines.append(f"{indent}- [{section.title}](#{anchor})\n")

        return "".join(toc_lines)

    def _generate_footer(self, report: Report) -> str:
        """生成页脚"""
        return f"""---

**报告信息**

- 报告ID: `{report.id}`
- 生成时间: {report.created_at.strftime("%Y-%m-%d %H:%M:%S")}
- 最后更新: {report.updated_at.strftime("%Y-%m-%d %H:%M:%S")}

---

*本报告由多智能体RAG系统生成*
"""

    def export_html(self, report: Report, **kwargs) -> str:
        """导出为HTML（使用Markdown转换）"""
        markdown_content = self.export_markdown(report, **kwargs)

        try:
            import markdown

            html_content = markdown.markdown(
                markdown_content,
                extensions=[
                    "extra",
                    "codehilite",
                    "toc",
                    "tables",
                    "fenced_code",
                ],
            )

            # 包装在HTML模板中
            return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.metadata.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
        code {{
            background-color: #f6f8fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }}
        pre {{
            background-color: #f6f8fa;
            padding: 16px;
            overflow: auto;
            border-radius: 6px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        table th, table td {{
            border: 1px solid #dfe2e5;
            padding: 6px 13px;
        }}
        table th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        blockquote {{
            border-left: 4px solid #dfe2e5;
            padding-left: 16px;
            color: #6a737d;
        }}
        a {{
            color: #0366d6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
        except ImportError:
            logger.warning("markdown库未安装，返回纯文本")
            return f"<pre>{markdown_content}</pre>"


# ============================================================================
# FastAPI路由
# ============================================================================

router = APIRouter(prefix="/api/reports", tags=["reports"])

# 内存存储（生产环境应使用数据库）
_reports_storage: dict[str, Report] = {}


@router.post("/create", response_model=Report)
async def create_report(request: CreateReportRequest):
    """
    创建新报告

    **示例请求**:
    ```json
    {
      "title": "零信任架构分析报告",
      "content": "## 概述\n\n零信任架构是...\n\n## 核心原则\n\n1. 永不信任\n2. 始终验证",
      "author": "安全分析师",
      "template": "security",
      "auto_structure": true
    }
    ```
    """
    generator = ReportGenerator()

    report = generator.create_report(
        title=request.title,
        content=request.content,
        author=request.author,
        template=request.template,
        auto_structure=request.auto_structure,
    )

    # 保存到存储
    _reports_storage[report.id] = report

    logger.info(f"Created report: {report.id}")
    return report


@router.get("/{report_id}", response_model=Report)
async def get_report(report_id: str):
    """获取报告详情"""
    if report_id not in _reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    return _reports_storage[report_id]


@router.put("/{report_id}", response_model=Report)
async def update_report(report_id: str, request: UpdateReportRequest):
    """
    更新报告

    **示例请求**:
    ```json
    {
      "metadata": {
        "title": "零信任架构分析报告 v2.0",
        "version": "2.0"
      },
      "sections": [
        {
          "id": "section-0",
          "title": "执行摘要",
          "content": "更新后的内容...",
          "order": 0,
          "level": 2
        }
      ]
    }
    ```
    """
    if report_id not in _reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    report = _reports_storage[report_id]

    # 更新元数据
    if request.metadata:
        report.metadata = request.metadata

    # 更新章节
    if request.sections:
        report.sections = request.sections

    # 更新时间
    report.updated_at = datetime.now()

    logger.info(f"Updated report: {report_id}")
    return report


@router.post("/export")
async def export_report(request: ExportReportRequest):
    """
    导出报告

    **支持格式**: markdown, html, pdf, docx

    **示例请求**:
    ```json
    {
      "report_id": "report-20260623-abc123",
      "format": "markdown",
      "include_toc": true,
      "include_metadata": true
    }
    ```
    """
    if request.report_id not in _reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    report = _reports_storage[request.report_id]
    exporter = ReportExporter()

    # 根据格式导出
    if request.format == "markdown":
        content = exporter.export_markdown(
            report,
            include_toc=request.include_toc,
            include_metadata=request.include_metadata,
        )
        media_type = "text/markdown"
        filename = f"{report.metadata.title}.md"

    elif request.format == "html":
        content = exporter.export_html(
            report,
            include_toc=request.include_toc,
            include_metadata=request.include_metadata,
        )
        media_type = "text/html"
        filename = f"{report.metadata.title}.html"

    elif request.format == "pdf":
        # PDF导出需要额外的库（pandoc）
        raise HTTPException(status_code=501, detail="PDF export requires pandoc. Use markdown and convert externally.")

    elif request.format == "docx":
        # DOCX导出需要额外的库（pandoc）
        raise HTTPException(status_code=501, detail="DOCX export requires pandoc. Use markdown and convert externally.")

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")

    # 返回文件流
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """删除报告"""
    if report_id not in _reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    del _reports_storage[report_id]
    logger.info(f"Deleted report: {report_id}")

    return {"message": "Report deleted successfully"}


@router.get("/")
async def list_reports():
    """列出所有报告"""
    reports = list(_reports_storage.values())
    # 按更新时间倒序
    reports.sort(key=lambda r: r.updated_at, reverse=True)

    return {
        "total": len(reports),
        "reports": [
            {
                "id": r.id,
                "title": r.metadata.title,
                "author": r.metadata.author,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in reports
        ],
    }


# ============================================================================
# AI辅助编辑功能
# ============================================================================

from app.services.ai_report_editor import (
    AIEditRequest,
    AIEditResponse,
    get_ai_report_editor,
)


@router.post("/ai-edit", response_model=AIEditResponse)
async def ai_edit_content(request: AIEditRequest):
    """
    AI辅助编辑内容

    **支持的操作**:
    - `polish`: 润色 - 改进语言表达，使其更专业
    - `expand`: 扩展 - 增加细节和深度，扩展到1.5-2倍
    - `summarize`: 总结 - 提炼核心要点，压缩到30-40%
    - `rewrite`: 重写 - 按指定风格重写（professional/casual/technical/executive）
    - `complete`: 补全 - 补充缺失的内容
    - `translate`: 翻译 - 翻译为指定语言
    - `custom`: 自定义 - 按用户指令编辑

    **示例请求（润色）**:
    ```json
    {
      "operation": "polish",
      "content": "零信任架构是个很好的安全模型，大家都应该用。",
      "style": "professional",
      "language": "zh"
    }
    ```

    **示例请求（自定义）**:
    ```json
    {
      "operation": "custom",
      "content": "零信任架构包括...",
      "instruction": "添加3个具体的实施步骤",
      "language": "zh"
    }
    ```
    """
    editor = get_ai_report_editor()

    try:
        result = await editor.edit(request)
        logger.info(f"AI edit completed: {request.operation}")
        return result
    except Exception as e:
        logger.error(f"AI edit failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI编辑失败: {str(e)}")


@router.post("/ai-edit-section")
async def ai_edit_report_section(report_id: str, section_id: str, request: AIEditRequest):
    """
    AI编辑报告中的特定章节

    直接编辑报告中的某个章节并保存

    **示例请求**:
    ```json
    {
      "operation": "expand",
      "content": "章节内容...",
      "style": "professional",
      "language": "zh"
    }
    ```
    """
    # 获取报告
    if report_id not in _reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    report = _reports_storage[report_id]

    # 找到目标section
    target_section = None
    for section in report.sections:
        if section.id == section_id:
            target_section = section
            break

    if not target_section:
        raise HTTPException(status_code=404, detail="Section not found")

    # AI编辑
    editor = get_ai_report_editor()
    try:
        # 设置上下文（前后章节）
        section_idx = report.sections.index(target_section)
        context_parts = []
        if section_idx > 0:
            context_parts.append(f"前一章节: {report.sections[section_idx - 1].title}")
        if section_idx < len(report.sections) - 1:
            context_parts.append(f"后一章节: {report.sections[section_idx + 1].title}")
        request.context = "\n".join(context_parts)

        result = await editor.edit(request)

        # 更新section
        target_section.content = result.edited
        report.updated_at = datetime.now()

        logger.info(f"AI edited section {section_id} in report {report_id}")

        return {
            "report_id": report_id,
            "section_id": section_id,
            "original": result.original,
            "edited": result.edited,
            "changes_summary": result.changes_summary,
        }

    except Exception as e:
        logger.error(f"AI edit section failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI编辑失败: {str(e)}")


# ============================================================================
# Report Agent集成
# ============================================================================

from app.agents.report_agent import (
    GenerateReportRequest,
    OptimizeReportRequest,
    ReviewReportRequest,
    ReviewReportResponse,
    get_report_agent,
)


@router.post("/agent/generate")
async def agent_generate_report(request: GenerateReportRequest):
    """
    使用Report Agent生成报告

    **示例请求**:
    ```json
    {
      "content": "零信任架构是...\n\nMFA是...",
      "title": "零信任架构技术报告",
      "report_type": "technical",
      "include_toc": true,
      "include_summary": true,
      "language": "zh"
    }
    ```
    """
    agent = get_report_agent()
    try:
        report_content = await agent.generate_report(request)
        logger.info("Report generated by agent")
        return {"content": report_content}
    except Exception as e:
        logger.error(f"Agent generate report failed: {e}")
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")


@router.post("/agent/review", response_model=ReviewReportResponse)
async def agent_review_report(request: ReviewReportRequest):
    """
    使用Report Agent审查报告

    **示例请求**:
    ```json
    {
      "content": "# 报告标题\n\n## 第一章...",
      "check_logic": true,
      "check_completeness": true,
      "check_quality": true
    }
    ```
    """
    agent = get_report_agent()
    try:
        review_result = await agent.review_report(request)
        logger.info(f"Report reviewed by agent: score={review_result.score}")
        return review_result
    except Exception as e:
        logger.error(f"Agent review report failed: {e}")
        raise HTTPException(status_code=500, detail=f"审查报告失败: {str(e)}")


@router.post("/agent/optimize")
async def agent_optimize_report(request: OptimizeReportRequest):
    """
    使用Report Agent优化报告

    **示例请求**:
    ```json
    {
      "content": "# 报告标题\n\n## 第一章...",
      "optimization_type": "all"
    }
    ```

    **optimization_type选项**:
    - `structure`: 优化结构（章节顺序、层级）
    - `language`: 优化语言（润色表达）
    - `completeness`: 优化完整性（补充缺失）
    - `all`: 全面优化（依次执行上述三项）
    """
    agent = get_report_agent()
    try:
        optimized_content = await agent.optimize_report(request)
        logger.info("Report optimized by agent")
        return {"content": optimized_content}
    except Exception as e:
        logger.error(f"Agent optimize report failed: {e}")
        raise HTTPException(status_code=500, detail=f"优化报告失败: {str(e)}")


@router.post("/agent/add-section")
async def agent_add_section(report_id: str, section_title: str, section_position: str = "end", after_section: str = ""):
    """
    使用Report Agent添加章节

    **示例请求**:
    ```
    POST /api/reports/agent/add-section?report_id=report-xxx&section_title=实施建议&section_position=end
    ```
    """
    # 获取报告
    if report_id not in _reports_storage:
        raise HTTPException(status_code=404, detail="Report not found")

    report = _reports_storage[report_id]

    # 导出当前报告内容
    exporter = ReportExporter()
    current_content = exporter.export_markdown(report, include_toc=False, include_metadata=False)

    # 使用Report Agent添加章节
    agent = get_report_agent()
    try:
        updated_content = await agent.add_section(
            report_content=current_content,
            section_title=section_title,
            section_position=section_position,
            after_section=after_section,
        )

        # 重新解析为sections（简化实现，实际应该更智能）
        # 这里返回更新后的内容，前端可以重新创建报告
        logger.info(f"Section added by agent: {section_title}")

        return {"content": updated_content}

    except Exception as e:
        logger.error(f"Agent add section failed: {e}")
        raise HTTPException(status_code=500, detail=f"添加章节失败: {str(e)}")
