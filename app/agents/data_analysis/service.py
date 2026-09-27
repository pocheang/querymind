"""Data-analysis specialist: numbers computed over the user's own tables.

Everything this specialist answers with comes from its two tools
(`app/tools/data_analysis/tables.py`): `table_list` finds the table, `table_query` runs
the SQL. It has no extraction of its own and one answer shape,
`data_analysis_report` -- conclusion, how it was computed (table and SQL), the
result table, and what limits it (sample size, empty values, truncation).

A table question about a PDF belongs here rather than to `pdf_text`: this
specialist has the table tools, and `pdf_text` can only quote (routing eval
edge-04, decided 2026-09-27).
"""

from __future__ import annotations

from app.agents.base import BaseSpecialistAgent
from app.agents.catalog import AgentClass
from app.tools.category import ToolCategory

PIPELINE_SKILLS: dict[str, str] = {"data_analysis_report": "data_analysis_report"}


class DataAnalysisAgentService(BaseSpecialistAgent):
    """Specialist for aggregations and lookups over structured tables."""

    @property
    def agent_class(self) -> str:
        return AgentClass.DATA_ANALYSIS

    @property
    def supported_skills(self) -> tuple[str, ...]:
        return ("data_analysis_report",)

    def pick_skill(self, question: str) -> str:
        del question
        return "data_analysis_report"

    @property
    def default_tool_category(self) -> ToolCategory:
        return ToolCategory.DATA_ANALYSIS

    @property
    def intent_keywords(self) -> tuple[str, ...]:
        # Words that name a table or a computation over one. Not "数据" or
        # "统计" alone: "数据泄露" is a security question and "统计学习" an AI one.
        # Not "表": as a substring it is in 代表, 表示 and 发表.
        return (
            "表格",
            "数据表",
            "报表",
            "电子表格",
            "数据分析",
            "合计",
            "求和",
            "汇总",
            "平均值",
            "占比",
            "同比",
            "环比",
            "透视表",
            "excel",
            "csv",
            "xlsx",
            "spreadsheet",
            "pivot",
            "group by",
            "data analysis",
        )

    pipeline_skills = PIPELINE_SKILLS
    fallback_pipeline_skill = "data_analysis_report"


__all__ = ["PIPELINE_SKILLS", "DataAnalysisAgentService"]
