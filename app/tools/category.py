"""Taxonomy and classification of governed tools across QueryMind domains."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolCategory(StrEnum):
    """Canonical categories for governed tools."""

    CYBERSECURITY = "cybersecurity"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    DATA_ANALYSIS = "data_analysis"
    WEB_SEARCH = "web_search"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    SYSTEM = "system"
    GENERAL = "general"


@dataclass(frozen=True)
class CategoryMetadata:
    """Descriptive metadata for a tool category."""

    category: ToolCategory
    display_name: str
    description: str
    icon_tag: str


_CATEGORY_METADATA: dict[ToolCategory, CategoryMetadata] = {
    ToolCategory.CYBERSECURITY: CategoryMetadata(
        category=ToolCategory.CYBERSECURITY,
        display_name="网络安全与情报",
        description="CVE漏洞知识库、MITRE ATT&CK战术技术映射、威胁指标IoC研判与缓解建议工具",
        icon_tag="shield-alert",
    ),
    ToolCategory.ARTIFICIAL_INTELLIGENCE: CategoryMetadata(
        category=ToolCategory.ARTIFICIAL_INTELLIGENCE,
        display_name="AI与算法计算",
        description="深度学习参数规模估算、Transformer FLOPs缩放律、KV Cache显存计算与安全AST沙箱",
        icon_tag="cpu",
    ),
    ToolCategory.DATA_ANALYSIS: CategoryMetadata(
        category=ToolCategory.DATA_ANALYSIS,
        display_name="结构化数据分析",
        description="关系型表格、SQL自动生成查询与聚合统计工具",
        icon_tag="table",
    ),
    ToolCategory.WEB_SEARCH: CategoryMetadata(
        category=ToolCategory.WEB_SEARCH,
        display_name="全网实时搜索",
        description="DuckDuckGo、Tavily、Bing等第三方实时联网搜索与开放世界知识检索",
        icon_tag="globe",
    ),
    ToolCategory.KNOWLEDGE_GRAPH: CategoryMetadata(
        category=ToolCategory.KNOWLEDGE_GRAPH,
        display_name="知识图谱",
        description="Neo4j多跳实体关系遍历、路径分析与实体拓扑发现工具",
        icon_tag="git-merge",
    ),
    ToolCategory.SYSTEM: CategoryMetadata(
        category=ToolCategory.SYSTEM,
        display_name="系统与集成",
        description="第三方连接器配置、凭证生命周期管理与系统运维治理工具",
        icon_tag="settings",
    ),
    ToolCategory.GENERAL: CategoryMetadata(
        category=ToolCategory.GENERAL,
        display_name="通用工具",
        description="通用基础辅助工具",
        icon_tag="tool",
    ),
}


def get_category_metadata(category: ToolCategory | str) -> CategoryMetadata:
    """Retrieve metadata descriptor for a given tool category."""
    try:
        cat_enum = ToolCategory(category) if isinstance(category, str) else category
        return _CATEGORY_METADATA.get(cat_enum, _CATEGORY_METADATA[ToolCategory.GENERAL])
    except ValueError:
        return _CATEGORY_METADATA[ToolCategory.GENERAL]


__all__ = [
    "CategoryMetadata",
    "ToolCategory",
    "get_category_metadata",
]
