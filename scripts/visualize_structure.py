#!/usr/bin/env python3
"""
代码结构可视化工具
提供多种方式可视化项目的代码结构
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import ast
import json


def generate_tree(directory, prefix="", max_depth=None, current_depth=0, ignore_patterns=None):
    """生成目录树结构"""
    if ignore_patterns is None:
        ignore_patterns = {
            '__pycache__', '.pyc', '.git', '.venv', 'node_modules',
            '.ruff_cache', '.pytest_cache', '.tmp', '.claude/worktrees'
        }

    if max_depth is not None and current_depth >= max_depth:
        return []

    lines = []
    directory = Path(directory)

    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        return lines

    # 过滤掉忽略的文件/目录
    items = [item for item in items if not any(pattern in str(item) for pattern in ignore_patterns)]

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        next_prefix = "    " if is_last else "│   "

        if item.is_dir():
            lines.append(f"{prefix}{current_prefix}[D] {item.name}/")
            lines.extend(generate_tree(
                item,
                prefix + next_prefix,
                max_depth,
                current_depth + 1,
                ignore_patterns
            ))
        else:
            icon = "[PY]" if item.suffix == ".py" else "[F]"
            lines.append(f"{prefix}{current_prefix}{icon} {item.name}")

    return lines


def analyze_imports(directory):
    """分析Python文件的导入关系"""
    directory = Path(directory)
    imports_map = defaultdict(set)

    for py_file in directory.rglob("*.py"):
        # 跳过测试文件和缓存
        if '__pycache__' in str(py_file) or '.venv' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            relative_path = py_file.relative_to(directory)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports_map[str(relative_path)].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports_map[str(relative_path)].add(node.module)
        except Exception as e:
            pass

    return imports_map


def analyze_structure(directory):
    """分析项目的整体结构"""
    directory = Path(directory)
    stats = {
        'total_py_files': 0,
        'total_lines': 0,
        'modules': defaultdict(int),
        'test_files': 0,
        'largest_files': []
    }

    for py_file in directory.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.venv' in str(py_file):
            continue

        stats['total_py_files'] += 1

        if 'test' in py_file.name:
            stats['test_files'] += 1

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                stats['total_lines'] += lines

                # 记录模块
                relative_path = py_file.relative_to(directory)
                module = str(relative_path.parts[0]) if relative_path.parts else 'root'
                stats['modules'][module] += 1

                # 记录大文件
                stats['largest_files'].append((str(relative_path), lines))
        except Exception:
            pass

    # 排序最大的文件
    stats['largest_files'].sort(key=lambda x: x[1], reverse=True)
    stats['largest_files'] = stats['largest_files'][:10]

    return stats


def generate_module_summary(directory):
    """生成模块摘要"""
    directory = Path(directory)
    modules = {}

    # 主要模块目录
    main_dirs = ['app', 'tests', 'scripts']

    for main_dir in main_dirs:
        dir_path = directory / main_dir
        if not dir_path.exists():
            continue

        module_info = {
            'files': [],
            'subdirs': []
        }

        try:
            for item in dir_path.iterdir():
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue

                if item.is_dir():
                    # 统计子目录中的文件数
                    py_files = list(item.rglob("*.py"))
                    py_files = [f for f in py_files if '__pycache__' not in str(f)]
                    module_info['subdirs'].append({
                        'name': item.name,
                        'files': len(py_files)
                    })
                elif item.suffix == '.py':
                    module_info['files'].append(item.name)
        except PermissionError:
            pass

        modules[main_dir] = module_info

    return modules


def print_structure_visualization(project_root):
    """打印完整的结构可视化"""
    project_root = Path(project_root)

    print("=" * 80)
    print("项目代码结构可视化")
    print("=" * 80)
    print()

    # 1. 项目目录树
    print("[目录树结构] (深度限制: 3)")
    print("-" * 80)
    tree_lines = generate_tree(project_root, max_depth=3)
    for line in tree_lines[:100]:  # 限制输出行数
        print(line)
    if len(tree_lines) > 100:
        print(f"... (还有 {len(tree_lines) - 100} 行)")
    print()

    # 2. 项目统计
    print("[项目统计]")
    print("-" * 80)
    stats = analyze_structure(project_root)
    print(f"总Python文件数: {stats['total_py_files']}")
    print(f"总代码行数: {stats['total_lines']:,}")
    print(f"测试文件数: {stats['test_files']}")
    print()

    print("各模块文件分布:")
    for module, count in sorted(stats['modules'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {module}: {count} 个文件")
    print()

    print("最大的10个文件:")
    for file_path, lines in stats['largest_files']:
        print(f"  {file_path}: {lines} 行")
    print()

    # 3. 模块摘要
    print("[主要模块结构]")
    print("-" * 80)
    modules = generate_module_summary(project_root)
    for module_name, module_info in modules.items():
        print(f"\n{module_name}/")
        if module_info['subdirs']:
            print("  子模块:")
            for subdir in sorted(module_info['subdirs'], key=lambda x: x['files'], reverse=True):
                print(f"    - {subdir['name']}/  ({subdir['files']} 个文件)")
        if module_info['files']:
            print(f"  根文件: {len(module_info['files'])} 个")
    print()

    # 4. 核心模块依赖关系
    print("[导入关系分析] (app 目录)")
    print("-" * 80)
    app_dir = project_root / "app"
    if app_dir.exists():
        imports = analyze_imports(app_dir)

        # 找出最常被导入的内部模块
        internal_imports = defaultdict(int)
        for file, imported_modules in imports.items():
            for module in imported_modules:
                if module.startswith('app.'):
                    internal_imports[module] += 1

        print("最常被导入的内部模块 (Top 10):")
        for module, count in sorted(internal_imports.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {module}: 被导入 {count} 次")
    print()

    print("=" * 80)
    print("可视化完成!")
    print("=" * 80)


def generate_graphviz_dot(project_root, output_file="structure.dot"):
    """生成Graphviz DOT文件用于可视化"""
    project_root = Path(project_root)
    app_dir = project_root / "app"

    if not app_dir.exists():
        print("app目录不存在")
        return

    imports = analyze_imports(app_dir)

    # 生成DOT文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("digraph ProjectStructure {\n")
        f.write("  rankdir=LR;\n")
        f.write("  node [shape=box, style=rounded];\n\n")

        # 定义节点
        nodes = set()
        for file in imports.keys():
            module_name = str(Path(file).with_suffix('').as_posix()).replace('/', '.')
            nodes.add(module_name)
            f.write(f'  "{module_name}";\n')

        f.write("\n")

        # 定义边（只包含内部导入）
        for file, imported_modules in imports.items():
            source = str(Path(file).with_suffix('').as_posix()).replace('/', '.')
            for module in imported_modules:
                if module.startswith('app.'):
                    # 简化模块名
                    target = module
                    if source != target:
                        f.write(f'  "{source}" -> "{target}";\n')

        f.write("}\n")

    print(f"[OK] Graphviz DOT 文件已生成: {output_file}")
    print("   使用以下命令生成可视化图片:")
    print(f"   dot -Tpng {output_file} -o structure.png")
    print(f"   dot -Tsvg {output_file} -o structure.svg")


if __name__ == "__main__":
    # 获取项目根目录
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = Path(__file__).parent.parent

    # 打印结构可视化
    print_structure_visualization(project_root)

    # 生成Graphviz文件
    output_dir = Path(project_root) / "docs" / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)

    dot_file = output_dir / "structure.dot"
    generate_graphviz_dot(project_root, dot_file)

    print(f"\n[提示] 可视化文件已保存到 {output_dir}")
