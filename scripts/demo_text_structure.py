"""OCR 文本结构化处理示例."""

from app.ingestion.utils.text_structure import (
    blocks_to_markdown,
    blocks_to_plain_text,
    structure_ocr_text,
)


def example_basic_usage():
    """基础使用示例."""
    print("=" * 60)
    print("示例 1: 基础 OCR 文本结构化")
    print("=" * 60)

    # 模拟 OCR 输出（无结构的纯文本）
    ocr_text = """产品技术手册

第一章 产品概述

本产品是一款高性能智能设备，
采用先进的处理器和算法，
能够满足各种应用场景需求。

主要特点：
• 高性能处理能力
• 低功耗设计
• 易于集成

第二章 技术规格

2.1 硬件参数

| 参数名称 | 参数值 |
| 处理器 | ARM Cortex-A72 |
| 内存 | 4GB DDR4 |
| 存储 | 64GB eMMC |

2.2 软件支持

支持以下操作系统：
1. Linux (Ubuntu 20.04+)
2. Android 11+
3. Windows 10+

代码示例：

    import device

    dev = device.connect()
    dev.initialize()
    print(dev.status())

第三章 使用说明

详细的使用说明请参考在线文档。"""

    # 结构化处理
    blocks = structure_ocr_text(ocr_text)

    print(f"\n识别到 {len(blocks)} 个文本块：\n")

    for i, block in enumerate(blocks, 1):
        print(f"{i}. 类型: {block.type:12} | 级别: {block.level} | 置信度: {block.confidence:.2f}")
        preview = block.content[:50].replace("\n", " ")
        print(f"   内容预览: {preview}...")
        print()

    # 转换为 Markdown
    print("\n" + "=" * 60)
    print("转换为 Markdown 格式：")
    print("=" * 60)
    markdown = blocks_to_markdown(blocks)
    print(markdown[:500])

    # 转换为结构化纯文本
    print("\n" + "=" * 60)
    print("转换为结构化纯文本：")
    print("=" * 60)
    plain = blocks_to_plain_text(blocks)
    print(plain[:500])


def example_chinese_english_mixed():
    """中英文混合文本示例."""
    print("\n\n" + "=" * 60)
    print("示例 2: 中英文混合文本")
    print("=" * 60)

    text = """Introduction to Machine Learning

Machine learning is a subset of artificial
intelligence that focuses on building systems
that can learn from data.

机器学习简介

机器学习是人工智能的一个子集，
专注于构建能够从数据中学习的系统。

Key Concepts:
• Supervised Learning
• Unsupervised Learning
• Reinforcement Learning

关键概念：
• 监督学习
• 无监督学习
• 强化学习"""

    blocks = structure_ocr_text(text)

    print(f"\n识别到 {len(blocks)} 个文本块\n")

    for block in blocks:
        print(f"[{block.type}] {block.content[:60]}...")


def example_table_extraction():
    """表格提取示例."""
    print("\n\n" + "=" * 60)
    print("示例 3: 表格识别")
    print("=" * 60)

    text = """性能测试结果

| 测试项目 | 结果 | 单位 |
| CPU性能 | 95.2 | 分 |
| 内存带宽 | 12.5 | GB/s |
| 存储速度 | 450 | MB/s |

测试环境：Ubuntu 22.04, 4核8线程"""

    blocks = structure_ocr_text(text)

    print("\n表格行：")
    for block in blocks:
        if block.type == "table_row":
            print(f"  {block.content}")


def example_list_hierarchy():
    """列表层级示例."""
    print("\n\n" + "=" * 60)
    print("示例 4: 多级列表")
    print("=" * 60)

    text = """项目结构：

• 后端服务
  • API 模块
    • 用户管理
    • 数据查询
  • 数据库
    • PostgreSQL
    • Redis
• 前端应用
  • React 组件
  • 状态管理"""

    blocks = structure_ocr_text(text)

    print("\n列表结构：")
    for block in blocks:
        if block.type == "list_item":
            indent = "  " * block.level
            print(f"{indent}└─ {block.content}")


def example_real_ocr_noise():
    """真实 OCR 噪声处理示例."""
    print("\n\n" + "=" * 60)
    print("示例 5: 处理 OCR 噪声")
    print("=" * 60)

    # 模拟真实 OCR 输出（有空格噪声）
    noisy_text = """第 一 章    产 品 介 绍

本  产  品  采  用  先  进  技  术  ，
具  有  以  下  优  势  ：

1 ．  高  性  能
2 ．  低  延  迟
3 ．  易  部  署"""

    print("原始 OCR 输出（有噪声）：")
    print(noisy_text[:100])

    blocks = structure_ocr_text(noisy_text)

    print("\n\n结构化后：")
    for block in blocks:
        print(f"[{block.type}] {block.content}")


def example_integration_with_chunker():
    """与现有切分器集成示例."""
    print("\n\n" + "=" * 60)
    print("示例 6: 与文档切分器集成")
    print("=" * 60)

    text = """第一章 系统架构

系统采用微服务架构，包含以下组件：

• API 网关
• 认证服务
• 业务服务
• 数据存储

第二章 部署指南

部署步骤：
1. 准备环境
2. 配置参数
3. 启动服务"""

    # 结构化处理
    blocks = structure_ocr_text(text)

    # 转换为 Markdown（更适合切分）
    markdown = blocks_to_markdown(blocks)

    print("结构化后的 Markdown：")
    print(markdown)

    print("\n说明：")
    print("- 结构化后的文本可以直接传入 split_documents()")
    print("- 标题、列表等结构会被保留")
    print("- 切分时会按语义边界分割，而不是随机截断")


if __name__ == "__main__":
    example_basic_usage()
    example_chinese_english_mixed()
    example_table_extraction()
    example_list_hierarchy()
    example_real_ocr_noise()
    example_integration_with_chunker()

    print("\n\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("""
OCR 文本结构化的优势：

1. 保留文档结构
   - 标题层级
   - 列表关系
   - 表格格式

2. 提升检索质量
   - 语义完整的块
   - 更好的上下文
   - 准确的引用

3. 改善用户体验
   - 结构化展示
   - 清晰的层级
   - 易于阅读

4. 集成方式
   - OCR → 结构化 → 切分 → 索引
   - 在 ocr_image_bytes() 中调用 structure_ocr_text()
   - 将结构化结果传入 split_documents()
    """)
