"""
基于 Agent 类别的文档过滤器
根据 agent_class 自动过滤相关文档，提高检索准确性
"""

from app.retrievers.corpus_store import read_corpus_records


def get_sources_by_agent_class(agent_class: str) -> list[str] | None:
    """
    根据 agent_class 获取相关文档的 source 列表

    Args:
        agent_class: Agent 类别 (cybersecurity, artificial_intelligence, pdf_text, general)

    Returns:
        文档 source 列表，如果是 general 则返回 None (不过滤)
    """
    # General agent 可以访问所有文档
    if agent_class == "general":
        return None

    # 读取所有记录
    records = read_corpus_records()

    # 过滤出匹配的文档
    sources = set()
    for record in records:
        metadata = record.get("metadata", {})
        record_agent = metadata.get("agent", "")

        # 匹配当前 agent_class 的文档
        if record_agent == agent_class:
            source = metadata.get("source", "")
            if source:
                sources.add(source)

    # Specialist agents should stay scoped to their labeled corpus even when empty.
    return list(sources)


def get_agent_filter_stats() -> dict:
    """
    获取每个 Agent 类别的文档统计

    Returns:
        统计信息字典
    """
    records = read_corpus_records()

    stats = {}
    for record in records:
        metadata = record.get("metadata", {})
        agent = metadata.get("agent", "未分类")
        source = metadata.get("source", "")

        if agent not in stats:
            stats[agent] = {"sources": set(), "chunks": 0}

        stats[agent]["chunks"] += 1
        if source:
            stats[agent]["sources"].add(source)

    # 转换为可序列化的格式
    result = {}
    for agent, data in stats.items():
        result[agent] = {
            "document_count": len(data["sources"]),
            "chunk_count": data["chunks"],
            "sources": sorted(list(data["sources"])),
        }

    return result


# 使用示例
if __name__ == "__main__":
    import json
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Agent 文档过滤器测试")
    logger.info("=" * 60)
    logger.info("")

    # 测试每个 agent_class
    for agent_class in ["cybersecurity", "artificial_intelligence", "pdf_text", "general"]:
        sources = get_sources_by_agent_class(agent_class)
        logger.info(f"{agent_class}:")
        if sources is None:
            logger.info("  → 不过滤 (访问所有文档)")
        else:
            logger.info(f"  → {len(sources)} 个文档")
            for source in sorted(sources)[:5]:  # 只显示前5个
                logger.info(f"    - {source}")
            if len(sources) > 5:
                logger.info(f"    ... 还有 {len(sources) - 5} 个")
        logger.info("")

    # 显示统计信息
    logger.info("=" * 60)
    logger.info("文档统计")
    logger.info("=" * 60)
    stats = get_agent_filter_stats()
    logger.info(json.dumps(stats, indent=2, ensure_ascii=False))
