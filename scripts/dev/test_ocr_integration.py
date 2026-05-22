"""集成测试：验证基于位置的 OCR 结构识别效果."""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.loaders.pdf_loader import load_pdf_image_ocr
from app.ingestion.chunker import split_documents


def test_ocr_integration(pdf_path: str):
    """测试完整的 PDF OCR 流程."""
    print("=" * 70)
    print("OCR 结构识别集成测试")
    print("=" * 70)
    print(f"\n测试文件: {pdf_path}\n")

    # 1. 加载 PDF 并 OCR
    print("步骤 1: 加载 PDF 并执行 OCR...")
    pdf_path_obj = Path(pdf_path)

    if not pdf_path_obj.exists():
        print(f"❌ 文件不存在: {pdf_path}")
        return

    try:
        docs = load_pdf_image_ocr(pdf_path_obj)
        print(f"✅ 成功提取 {len(docs)} 个文档块\n")
    except Exception as e:
        print(f"❌ OCR 失败: {e}")
        return

    if not docs:
        print("⚠️  未识别到任何文本")
        return

    # 2. 分析 OCR 结果
    print("步骤 2: 分析 OCR 结果...")
    for i, doc in enumerate(docs, 1):
        metadata = doc.metadata
        print(f"\n文档块 {i}:")
        print(f"  - OCR 引擎: {metadata.get('ocr_engine', 'unknown')}")
        print(f"  - OCR 方法: {metadata.get('ocr_method', 'unknown')}")
        print(f"  - 文本块数量: {metadata.get('text_blocks_count', 0)}")

        block_types = metadata.get('block_types', {})
        if block_types:
            print(f"  - 块类型分布:")
            for block_type, count in block_types.items():
                print(f"    • {block_type}: {count} 个")

        # 显示内容预览
        content = doc.page_content
        if '[image_ocr_structured]' in content:
            structured_part = content.split('[image_ocr_structured]')[1]
            preview = structured_part[:300].replace('\n', '\n    ')
            print(f"  - 内容预览:\n    {preview}...")

    # 3. 文档切分
    print("\n" + "=" * 70)
    print("步骤 3: 文档切分...")
    try:
        child_chunks, parent_records = split_documents(docs)
        print(f"✅ 切分完成:")
        print(f"  - 父块: {len(parent_records)} 个")
        print(f"  - 子块: {len(child_chunks)} 个")
    except Exception as e:
        print(f"❌ 切分失败: {e}")
        return

    # 4. 分析切分结果
    print("\n步骤 4: 分析切分结果...")

    # 检查是否保留了结构信息
    has_structure_info = False
    for parent in parent_records[:3]:  # 检查前3个父块
        metadata = parent.get('metadata', {})
        if 'block_types' in metadata:
            has_structure_info = True
            print(f"\n父块示例 (ID: {parent['id'][:16]}...):")
            print(f"  - 块类型: {metadata.get('block_types', {})}")
            print(f"  - 文本长度: {len(parent['text'])} 字符")
            print(f"  - 内容预览: {parent['text'][:100]}...")
            break

    if has_structure_info:
        print("\n✅ 结构信息已成功保留到切分后的块中")
    else:
        print("\n⚠️  未检测到结构信息（可能使用了 Tesseract 降级）")

    # 5. 对比分析
    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)

    # 统计使用的 OCR 引擎
    ocr_engines = {}
    for doc in docs:
        engine = doc.metadata.get('ocr_engine', 'unknown')
        ocr_engines[engine] = ocr_engines.get(engine, 0) + 1

    print(f"\nOCR 引擎使用情况:")
    for engine, count in ocr_engines.items():
        print(f"  - {engine}: {count} 个文档块")

    # 统计识别的块类型
    all_block_types = {}
    for doc in docs:
        block_types = doc.metadata.get('block_types', {})
        for block_type, count in block_types.items():
            all_block_types[block_type] = all_block_types.get(block_type, 0) + count

    if all_block_types:
        print(f"\n识别的文本块类型:")
        for block_type, count in sorted(all_block_types.items(), key=lambda x: -x[1]):
            print(f"  - {block_type}: {count} 个")

    print(f"\n切分统计:")
    print(f"  - 平均每个父块: {len(child_chunks) / len(parent_records):.1f} 个子块")
    print(f"  - 平均父块大小: {sum(len(p['text']) for p in parent_records) / len(parent_records):.0f} 字符")
    print(f"  - 平均子块大小: {sum(len(c.page_content) for c in child_chunks) / len(child_chunks):.0f} 字符")


def test_with_sample_pdf():
    """使用示例 PDF 测试."""
    # 查找测试 PDF
    test_pdfs = [
        "data/docs/sample.pdf",
        "data/uploads/test.pdf",
        "data/test.pdf",
    ]

    for pdf_path in test_pdfs:
        if Path(pdf_path).exists():
            print(f"找到测试文件: {pdf_path}\n")
            test_ocr_integration(pdf_path)
            return

    print("❌ 未找到测试 PDF 文件")
    print("\n请提供 PDF 文件路径:")
    print("  python scripts/dev/test_ocr_integration.py <pdf_path>")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        test_ocr_integration(pdf_path)
    else:
        test_with_sample_pdf()
