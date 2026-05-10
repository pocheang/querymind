"""对比测试：原版 vs 优化版."""

from app.ingestion.utils.text_structure import structure_ocr_text as structure_v1
from app.ingestion.utils.text_structure_v2 import structure_ocr_text as structure_v2
from app.ingestion.utils.text_structure_v2 import blocks_to_markdown


def compare_versions(test_name: str, text: str):
    """对比两个版本的输出."""
    print("=" * 70)
    print(f"测试: {test_name}")
    print("=" * 70)
    print(f"输入:\n{text}\n")

    # V1
    blocks_v1 = structure_v1(text)
    print(f"V1 结果 ({len(blocks_v1)} 个块):")
    for i, block in enumerate(blocks_v1, 1):
        print(f"  {i}. [{block.type:12}] {block.content[:60]}")

    # V2
    blocks_v2 = structure_v2(text)
    print(f"\nV2 结果 ({len(blocks_v2)} 个块):")
    for i, block in enumerate(blocks_v2, 1):
        print(f"  {i}. [{block.type:12}] conf={block.confidence:.2f} | {block.content[:60]}")

    # Markdown 输出对比
    print("\nV2 Markdown 输出:")
    markdown = blocks_to_markdown(blocks_v2)
    print(markdown[:300])
    print("\n")


if __name__ == "__main__":
    # 测试 1: OCR 噪声清理
    print("\n" + "🔧 测试 1: OCR 噪声清理")
    compare_versions(
        "OCR 噪声",
        """第 一 章    产 品 介 绍

1 ．  高  性  能
2 ．  低  延  迟"""
    )

    # 测试 2: 列表前缀移除
    print("\n" + "🔧 测试 2: 列表前缀移除")
    compare_versions(
        "列表前缀",
        """1. 第一项
2. 第二项
• 项目符号"""
    )

    # 测试 3: 中文顿号列表
    print("\n" + "🔧 测试 3: 中文顿号列表")
    compare_versions(
        "中文顿号",
        """一、第一章
二、第二章
三、第三章"""
    )

    # 测试 4: 段落合并边界情况
    print("\n" + "🔧 测试 4: 段落合并（空字符串保护）")
    compare_versions(
        "边界情况",
        """这是第一行

这是第二行"""
    )

    # 测试 5: 置信度计算
    print("\n" + "🔧 测试 5: 置信度计算")
    compare_versions(
        "置信度",
        """第一章 概述

INTRODUCTION

可能是标题也可能不是"""
    )

    # 测试 6: 代码块不被合并
    print("\n" + "🔧 测试 6: 代码块隔离")
    compare_versions(
        "代码块",
        """正文内容

    def hello():
        return True

继续正文"""
    )

    # 测试 7: 性能测试
    print("\n" + "⚡ 测试 7: 性能对比")
    import time

    large_text = """第一章 测试

这是一个段落。
包含多行内容。

1. 列表项一
2. 列表项二
3. 列表项三

| 表格 | 数据 |
""" * 100  # 重复 100 次

    # V1
    start = time.perf_counter()
    for _ in range(10):
        structure_v1(large_text)
    v1_time = (time.perf_counter() - start) * 1000

    # V2
    start = time.perf_counter()
    for _ in range(10):
        structure_v2(large_text)
    v2_time = (time.perf_counter() - start) * 1000

    print(f"V1 平均耗时: {v1_time/10:.2f}ms")
    print(f"V2 平均耗时: {v2_time/10:.2f}ms")
    print(f"性能提升: {((v1_time - v2_time) / v1_time * 100):.1f}%")
