"""快速测试 OCR 文本结构化."""

from app.ingestion.utils.text_structure import structure_ocr_text, blocks_to_markdown


def quick_test(text: str):
    """快速测试文本结构化."""
    print("=" * 60)
    print("原始文本:")
    print("=" * 60)
    print(text)
    print()

    blocks = structure_ocr_text(text)

    print("=" * 60)
    print(f"识别结果 ({len(blocks)} 个块):")
    print("=" * 60)
    for i, block in enumerate(blocks, 1):
        print(f"{i}. [{block.type:12}] level={block.level} | {block.content[:50]}")
    print()

    print("=" * 60)
    print("Markdown 输出:")
    print("=" * 60)
    markdown = blocks_to_markdown(blocks)
    print(markdown)


if __name__ == "__main__":
    # 测试 1: 简单数字列表
    print("\n测试 1: 简单数字列表")
    quick_test("1,2,3")

    # 测试 2: 标准数字列表
    print("\n\n测试 2: 标准数字列表")
    quick_test("""1. 第一项
2. 第二项
3. 第三项""")

    # 测试 3: 逗号分隔的项目
    print("\n\n测试 3: 逗号分隔")
    quick_test("项目一, 项目二, 项目三")

    # 测试 4: 混合格式
    print("\n\n测试 4: 混合格式")
    quick_test("""任务列表：

1. 完成文档
2. 运行测试
3. 提交代码

注意事项：
• 检查格式
• 确认无误
• 及时提交""")

    # 测试 5: 中文数字
    print("\n\n测试 5: 中文数字")
    quick_test("""一、第一章
二、第二章
三、第三章""")

    # 测试 6: 括号列表
    print("\n\n测试 6: 括号列表")
    quick_test("""(1) 第一步
(2) 第二步
(3) 第三步""")
