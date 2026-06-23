#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理根目录临时文档文件
将94个临时Markdown文件移动到internal_docs目录
"""
import shutil
import sys
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent

# 目标目录
INTERNAL_DOCS = ROOT_DIR / "internal_docs"
AGENT_REPORTS = INTERNAL_DOCS / "agent_reports"
FIX_SUMMARIES = INTERNAL_DOCS / "fix_summaries"
COMPLETION_REPORTS = INTERNAL_DOCS / "completion_reports"
GUIDES = INTERNAL_DOCS / "guides"
PLANS = INTERNAL_DOCS / "plans"
REPORTS = INTERNAL_DOCS / "reports"

# 创建目标目录
for dir_path in [AGENT_REPORTS, FIX_SUMMARIES, COMPLETION_REPORTS, GUIDES, PLANS, REPORTS]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 文件分类规则
PATTERNS = {
    AGENT_REPORTS: ["AGENT_*.md"],
    FIX_SUMMARIES: ["*FIXES*.md", "*FIX_*.md", "CHUNKER_FIX_*.md"],
    COMPLETION_REPORTS: ["*COMPLETE*.md", "*COMPLETION*.md"],
    GUIDES: ["*GUIDE*.md"],
    PLANS: ["*PLAN*.md", "*IMPLEMENTATION*.md"],
    REPORTS: ["*REPORT*.md", "*SUMMARY.md", "*VERIFICATION*.md"],
}

# 保留在根目录的文件
KEEP_IN_ROOT = {
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "CLAUDE.md",
    "HIGH_PRIORITY_FIXES.md",
}

def main():
    moved_count = 0
    errors = []

    # 遍历根目录所有.md文件
    for md_file in ROOT_DIR.glob("*.md"):
        if md_file.name in KEEP_IN_ROOT:
            print(f"[KEEP] {md_file.name}")
            continue

        # 根据模式决定目标目录
        target_dir = None
        for dest_dir, patterns in PATTERNS.items():
            for pattern in patterns:
                if md_file.match(pattern):
                    target_dir = dest_dir
                    break
            if target_dir:
                break

        # 如果没有匹配规则，放到reports
        if not target_dir:
            target_dir = REPORTS

        # 执行移动
        try:
            target_path = target_dir / md_file.name
            if target_path.exists():
                print(f"[SKIP] {md_file.name} (target exists)")
            else:
                shutil.move(str(md_file), str(target_path))
                print(f"[MOVE] {md_file.name} -> {target_dir.name}/")
                moved_count += 1
        except Exception as e:
            errors.append(f"[ERROR] {md_file.name}: {e}")
            print(errors[-1])

    # 总结
    print(f"\n{'='*60}")
    print(f"Cleanup Summary:")
    print(f"  - Files moved: {moved_count}")
    print(f"  - Files kept: {len(KEEP_IN_ROOT)}")
    print(f"  - Errors: {len(errors)}")

    if errors:
        print(f"\nError details:")
        for error in errors:
            print(f"  {error}")

    print(f"\nRemaining .md files in root:")
    remaining = list(ROOT_DIR.glob("*.md"))
    for f in remaining:
        print(f"  - {f.name}")
    print(f"\nTotal: {len(remaining)} files")

if __name__ == "__main__":
    main()
