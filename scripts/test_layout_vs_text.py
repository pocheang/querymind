"""测试基于位置的结构识别效果."""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image
from app.ingestion.utils.layout_structure import integrate_with_paddleocr


def test_with_real_image(image_path: str):
    """使用真实图片测试."""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print("❌ PaddleOCR 未安装")
        print("安装命令: pip install paddleocr")
        return

    # 初始化 OCR
    print("初始化 PaddleOCR...")
    ocr = PaddleOCR(use_angle_cls=True, lang='ch')

    # 读取图片
    print(f"读取图片: {image_path}")
    image = Image.open(image_path)
    width, height = image.size
    print(f"图片尺寸: {width}x{height}")

    # OCR 识别
    print("\n执行 OCR...")
    result = ocr.ocr(image_path, cls=True)

    if not result or not result[0]:
        print("❌ OCR 未识别到文字")
        return

    print(f"✅ 识别到 {len(result[0])} 个文本框\n")

    # 方案 1：纯文本结构识别
    print("=" * 60)
    print("方案 1：纯文本结构识别")
    print("=" * 60)

    from app.ingestion.utils.text_structure import structure_ocr_text

    # 提取纯文本
    text_only = "\n".join([line[1][0] for line in result[0]])
    blocks_v1 = structure_ocr_text(text_only)

    for i, block in enumerate(blocks_v1, 1):
        print(f"{i:2}. [{block.type:12}] level={block.level} | {block.content[:50]}")

    # 方案 2：基于位置的结构识别
    print("\n" + "=" * 60)
    print("方案 2：基于位置的结构识别")
    print("=" * 60)

    blocks_v2 = integrate_with_paddleocr(result[0], width, height)

    for i, block in enumerate(blocks_v2, 1):
        bbox_info = f"({block.bbox[0][0]:.0f},{block.bbox[0][1]:.0f})" if block.bbox else ""
        print(f"{i:2}. [{block.type:12}] level={block.level} {bbox_info:12} | {block.text[:50]}")

    # 对比分析
    print("\n" + "=" * 60)
    print("对比分析")
    print("=" * 60)

    v1_types = [b.type for b in blocks_v1]
    v2_types = [b.type for b in blocks_v2]

    print(f"方案 1 识别: {len(blocks_v1)} 个块")
    print(f"  - 标题: {v1_types.count('title')} 个")
    print(f"  - 段落: {v1_types.count('paragraph')} 个")
    print(f"  - 列表: {v1_types.count('list_item')} 个")

    print(f"\n方案 2 识别: {len(blocks_v2)} 个块")
    print(f"  - 标题: {v2_types.count('title')} 个")
    print(f"  - 小标题: {v2_types.count('heading')} 个")
    print(f"  - 段落: {v2_types.count('paragraph')} 个")
    print(f"  - 列表: {v2_types.count('list_item')} 个")
    print(f"  - 表格: {v2_types.count('table_cell')} 个")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python test_layout_vs_text.py <图片路径>")
        print("\n示例:")
        print("  python scripts/test_layout_vs_text.py data/test_images/document.jpg")
        print("\n建议测试文档类型:")
        print("  1. 产品手册（有大标题、章节、列表）")
        print("  2. 技术文档（有多级标题）")
        print("  3. 表格文档（有表格布局）")
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"❌ 文件不存在: {image_path}")
        sys.exit(1)

    test_with_real_image(image_path)
