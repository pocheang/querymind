#!/usr/bin/env python3
"""
Simple text-based project structure analyzer
Outputs pure ASCII to avoid encoding issues
"""

import os
from pathlib import Path
from collections import defaultdict


def analyze_project(project_root):
    """Analyze project and output text report"""
    project_root = Path(project_root)

    # Statistics
    stats = {
        'total_py_files': 0,
        'total_lines': 0,
        'modules': defaultdict(int),
        'test_files': 0,
        'largest_files': []
    }

    for py_file in project_root.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.venv' in str(py_file) or 'worktrees' in str(py_file):
            continue

        stats['total_py_files'] += 1

        if 'test' in py_file.name:
            stats['test_files'] += 1

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                stats['total_lines'] += lines

                relative_path = py_file.relative_to(project_root)
                module = str(relative_path.parts[0]) if relative_path.parts else 'root'
                stats['modules'][module] += 1
                stats['largest_files'].append((str(relative_path), lines))
        except Exception:
            pass

    stats['largest_files'].sort(key=lambda x: x[1], reverse=True)

    # Output report
    output = []
    output.append("=" * 80)
    output.append("PROJECT CODE STRUCTURE ANALYSIS")
    output.append("=" * 80)
    output.append("")

    # Basic stats
    output.append("[PROJECT STATISTICS]")
    output.append("-" * 80)
    output.append(f"Total Python Files: {stats['total_py_files']}")
    output.append(f"Total Lines of Code: {stats['total_lines']:,}")
    output.append(f"Test Files: {stats['test_files']}")
    output.append(f"Number of Modules: {len(stats['modules'])}")
    output.append("")

    # Module distribution
    output.append("[MODULE DISTRIBUTION]")
    output.append("-" * 80)
    for module, count in sorted(stats['modules'].items(), key=lambda x: x[1], reverse=True):
        bar = "#" * (count // 2)
        output.append(f"{module:20s} | {count:3d} files | {bar}")
    output.append("")

    # Top 20 largest files
    output.append("[TOP 20 LARGEST FILES]")
    output.append("-" * 80)
    output.append(f"{'Rank':<6} {'Lines':<8} {'File Path'}")
    output.append("-" * 80)
    for i, (file_path, lines) in enumerate(stats['largest_files'][:20], 1):
        output.append(f"#{i:<5} {lines:<8} {file_path}")
    output.append("")

    # Directory structure
    output.append("[DIRECTORY STRUCTURE]")
    output.append("-" * 80)

    # Scan main directories
    for main_dir in ['app', 'tests', 'scripts']:
        dir_path = project_root / main_dir
        if dir_path.exists():
            output.append(f"\n{main_dir}/")
            subdirs = [d for d in dir_path.iterdir() if d.is_dir() and d.name != '__pycache__' and not d.name.startswith('.')]
            for subdir in sorted(subdirs):
                py_files = list(subdir.rglob("*.py"))
                py_files = [f for f in py_files if '__pycache__' not in str(f)]
                output.append(f"  {subdir.name}/ ({len(py_files)} files)")

    output.append("")
    output.append("=" * 80)
    output.append("ANALYSIS COMPLETE")
    output.append("=" * 80)

    return "\n".join(output)


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent

    # Generate report
    report = analyze_project(project_root)

    # Save to file
    output_file = project_root / "docs" / "structure_report.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(report)
    print(f"\nReport saved to: {output_file}")
