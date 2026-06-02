"""
文档分类脚本 - 根据文档内容和文件名自动分类到对应的 Agent 类别
"""
import os
import sys
from pathlib import Path

# 设置 UTF-8 编码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings

# Agent 类别定义
AGENT_CATEGORIES = {
    "cybersecurity": {
        "keywords": [
            "security", "threat", "vulnerability", "attack", "defense",
            "incident", "malware", "exploit", "penetration", "firewall",
            "encryption", "authentication", "authorization", "compliance",
            "安全", "威胁", "漏洞", "攻击", "防御", "事件", "恶意软件"
        ],
        "patterns": [
            "*security*", "*threat*", "*vulnerability*", "*cybersecurity*",
            "*安全*", "*威胁*"
        ]
    },
    "artificial_intelligence": {
        "keywords": [
            "rag", "llm", "model", "training", "inference", "embedding",
            "vector", "agent", "prompt", "fine-tuning", "transformer",
            "neural", "machine learning", "deep learning", "ai",
            "人工智能", "大模型", "向量", "智能体", "提示词", "训练"
        ],
        "patterns": [
            "*rag*", "*llm*", "*ai*", "*model*", "*artificial_intelligence*",
            "*machine_learning*", "*deep_learning*", "*人工智能*"
        ]
    },
    "pdf_text": {
        "keywords": [
            "pdf", "document", "text extraction", "ocr", "image",
            "文档", "提取", "图像"
        ],
        "patterns": [
            "*.pdf", "*document*", "*文档*"
        ]
    },
    "general": {
        "keywords": [],  # 默认类别
        "patterns": []
    }
}


def classify_by_filename(filename: str) -> str:
    """根据文件名分类"""
    filename_lower = filename.lower()

    for category, config in AGENT_CATEGORIES.items():
        if category == "general":
            continue

        # 检查文件名中的关键词
        for keyword in config["keywords"]:
            if keyword.lower() in filename_lower:
                return category

    return "general"


def classify_by_content(content: str, filename: str) -> str:
    """根据内容分类"""
    content_lower = content.lower()

    # 先尝试文件名分类
    filename_category = classify_by_filename(filename)
    if filename_category != "general":
        return filename_category

    # 统计每个类别的关键词匹配数
    category_scores = {}

    for category, config in AGENT_CATEGORIES.items():
        if category == "general":
            continue

        score = 0
        for keyword in config["keywords"]:
            if keyword.lower() in content_lower:
                score += content_lower.count(keyword.lower())

        category_scores[category] = score

    # 返回得分最高的类别
    if category_scores:
        best_category = max(category_scores.items(), key=lambda x: x[1])
        if best_category[1] > 0:
            return best_category[0]

    return "general"


def classify_documents_in_directory(data_dir: Path = None):
    """分类目录中的所有文档"""
    if data_dir is None:
        settings = get_settings()
        data_dir = Path(settings.data_dir)

    print(f"扫描目录: {data_dir}")
    print("-" * 60)

    classifications = {}

    # 遍历所有支持的文档
    for file_path in data_dir.rglob("*"):
        if not file_path.is_file():
            continue

        # 跳过隐藏文件和特殊文件
        if file_path.name.startswith("."):
            continue

        ext = file_path.suffix.lower()
        if ext not in [".md", ".txt", ".pdf"]:
            continue

        try:
            # 读取文件内容（仅文本文件）
            if ext in [".md", ".txt"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                category = classify_by_content(content, file_path.name)
            else:
                # PDF 文件仅根据文件名分类
                category = classify_by_filename(file_path.name)

            relative_path = file_path.relative_to(data_dir)
            classifications[str(relative_path)] = category

            print(f"📄 {relative_path}")
            print(f"   分类: {category}")
            print()

        except Exception as e:
            print(f"❌ 处理文件失败: {file_path}")
            print(f"   错误: {e}")
            print()

    return classifications


def organize_documents_by_category(data_dir: Path = None, dry_run: bool = True):
    """将文档组织到对应的类别目录"""
    if data_dir is None:
        settings = get_settings()
        data_dir = Path(settings.data_dir)

    classifications = classify_documents_in_directory(data_dir)

    print("\n" + "=" * 60)
    print("文档分类统计")
    print("=" * 60)

    # 统计每个类别的文档数量
    category_counts = {}
    for category in classifications.values():
        category_counts[category] = category_counts.get(category, 0) + 1

    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count} 个文档")

    if dry_run:
        print("\n⚠️  这是预览模式，没有实际移动文件")
        print("   要实际执行，请使用 --execute 参数")
    else:
        print("\n开始组织文档...")
        import shutil

        moved_count = 0
        skipped_count = 0
        failed_count = 0

        for file_path, category in classifications.items():
            try:
                source = data_dir / file_path

                # 检查源文件是否存在
                if not source.exists():
                    print(f"⚠️  源文件不存在: {file_path}")
                    skipped_count += 1
                    continue

                # 创建目标目录
                target_dir = data_dir / "classified" / category
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / source.name

                # 检查目标文件是否已存在
                if target.exists():
                    print(f"⚠️  跳过（目标已存在）: {file_path}")
                    skipped_count += 1
                    continue

                # 移动文件
                shutil.move(str(source), str(target))
                moved_count += 1
                print(f"✅ 已移动: {file_path} -> classified/{category}/")

            except Exception as e:
                failed_count += 1
                print(f"❌ 移动失败: {file_path} - {e}")

        print(f"\n移动完成: 成功 {moved_count}, 跳过 {skipped_count}, 失败 {failed_count}")

    return classifications


def update_document_metadata(classifications: dict, data_dir: Path = None):
    """更新数据库中的文档元数据

    使用JSON文件存储文档分类元数据，便于后续查询和管理。
    """
    import json
    from datetime import datetime

    print("\n" + "=" * 60)
    print("更新文档元数据")
    print("=" * 60)

    try:
        if data_dir is None:
            settings = get_settings()
            data_dir = Path(settings.data_dir)

        # 元数据文件路径
        metadata_file = data_dir / "document_metadata.json"

        # 读取现有元数据
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            print(f"📄 已加载现有元数据: {len(metadata)} 条记录")
        else:
            metadata = {}
            print("📄 创建新的元数据文件")

        # 更新分类信息
        updated_count = 0
        for file_path, category in classifications.items():
            metadata[file_path] = {
                "category": category,
                "classified_at": datetime.now().isoformat(),
                "auto_classified": True,
                "file_name": Path(file_path).name
            }
            updated_count += 1
            print(f"✅ 更新: {file_path} -> {category}")

        # 保存更新后的元数据
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 元数据更新完成: {updated_count} 条记录")
        print(f"📁 保存位置: {metadata_file}")

    except Exception as e:
        print(f"❌ 更新失败: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="文档分类工具")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="文档目录路径（默认使用配置中的 DATA_DIR）"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="实际执行文档组织（默认为预览模式）"
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="更新数据库中的文档元数据"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("RAG 文档分类工具")
    print("=" * 60)
    print()

    # 分类文档
    classifications = organize_documents_by_category(
        data_dir=args.data_dir,
        dry_run=not args.execute
    )

    # 更新数据库
    if args.update_db:
        update_document_metadata(classifications)

    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
