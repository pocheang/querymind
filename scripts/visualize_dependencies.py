#!/usr/bin/env python3
"""
Generate dependency graph using Graphviz
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import ast


def analyze_imports(directory, module_filter='app'):
    """Analyze Python imports"""
    directory = Path(directory)
    imports_map = defaultdict(set)
    all_modules = set()

    for py_file in directory.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.venv' in str(py_file) or 'worktrees' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            relative_path = py_file.relative_to(directory)
            module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')

            if not module_name.startswith(module_filter):
                continue

            all_modules.add(module_name)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(module_filter):
                            imports_map[module_name].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith(module_filter):
                        imports_map[module_name].add(node.module)
        except Exception:
            pass

    return imports_map, all_modules


def generate_graphviz(project_root, output_file, module_filter='app'):
    """Generate Graphviz DOT file"""
    project_root = Path(project_root)
    imports_map, all_modules = analyze_imports(project_root, module_filter)

    # Calculate node importance (how many times imported)
    import_counts = defaultdict(int)
    for imported_modules in imports_map.values():
        for module in imported_modules:
            import_counts[module] += 1

    # Group modules by top-level package
    module_groups = defaultdict(list)
    for module in all_modules:
        parts = module.split('.')
        if len(parts) >= 2:
            group = f"{parts[0]}.{parts[1]}"
            module_groups[group].append(module)
        else:
            module_groups['root'].append(module)

    # Generate DOT file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('digraph ProjectDependencies {\n')
        f.write('  rankdir=LR;\n')
        f.write('  node [shape=box, style="rounded,filled", fontname="Arial"];\n')
        f.write('  edge [color="#666666", arrowsize=0.7];\n')
        f.write('  \n')

        # Color palette for different modules
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
        ]

        # Create subgraphs for each module group
        for i, (group, modules) in enumerate(sorted(module_groups.items())):
            color = colors[i % len(colors)]
            f.write(f'  subgraph cluster_{i} {{\n')
            f.write(f'    label="{group}";\n')
            f.write(f'    style=filled;\n')
            f.write(f'    color="{color}30";\n')
            f.write('    \n')

            for module in sorted(modules):
                # Simplify node name
                short_name = module.split('.')[-1]

                # Determine node importance
                importance = import_counts.get(module, 0)
                if importance > 5:
                    fillcolor = '#FF6B6B'
                    penwidth = 3
                elif importance > 2:
                    fillcolor = '#FFA07A'
                    penwidth = 2
                else:
                    fillcolor = '#E8F4F8'
                    penwidth = 1

                f.write(f'    "{module}" [label="{short_name}", fillcolor="{fillcolor}", penwidth={penwidth}];\n')

            f.write('  }\n')
            f.write('  \n')

        # Add edges
        f.write('  \n')
        for source, targets in sorted(imports_map.items()):
            for target in sorted(targets):
                if source != target and target in all_modules:
                    f.write(f'  "{source}" -> "{target}";\n')

        f.write('}\n')

    return output_file


def generate_simple_tree(project_root, output_file):
    """Generate simple module tree visualization"""
    project_root = Path(project_root)

    # Scan app directory
    app_dir = project_root / "app"
    if not app_dir.exists():
        print("app directory not found")
        return None

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('digraph ModuleTree {\n')
        f.write('  rankdir=TB;\n')
        f.write('  node [shape=folder, style=filled, fillcolor="#E8F4F8"];\n')
        f.write('  \n')

        # Scan directories
        for root, dirs, files in os.walk(app_dir):
            # Skip cache directories
            dirs[:] = [d for d in dirs if d != '__pycache__' and not d.startswith('.')]

            root_path = Path(root)
            relative_root = root_path.relative_to(project_root)
            parent_name = str(relative_root).replace(os.sep, '_')

            # Add directory node
            display_name = root_path.name
            f.write(f'  "{parent_name}" [label="{display_name}"];\n')

            # Add parent relationship
            if root_path != app_dir:
                parent_path = root_path.parent.relative_to(project_root)
                parent_node = str(parent_path).replace(os.sep, '_')
                f.write(f'  "{parent_node}" -> "{parent_name}";\n')

            # Add Python files
            py_files = [f for f in files if f.endswith('.py') and f != '__init__.py']
            for py_file in py_files:
                file_node = f"{parent_name}_{py_file.replace('.py', '')}"
                file_label = py_file.replace('.py', '')
                f.write(f'  "{file_node}" [label="{file_label}", shape=note, fillcolor="#C8E6C9"];\n')
                f.write(f'  "{parent_name}" -> "{file_node}";\n')

        f.write('}\n')

    return output_file


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "docs" / "visualizations"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate dependency graph
    dep_file = output_dir / "dependencies.dot"
    generate_graphviz(project_root, dep_file, 'app')
    print(f"Dependency graph generated: {dep_file}")

    # Generate module tree
    tree_file = output_dir / "module_tree.dot"
    generate_simple_tree(project_root, tree_file)
    print(f"Module tree generated: {tree_file}")

    print("\nTo generate images, run:")
    print(f"  dot -Tpng {dep_file} -o {output_dir}/dependencies.png")
    print(f"  dot -Tsvg {dep_file} -o {output_dir}/dependencies.svg")
    print(f"  dot -Tpng {tree_file} -o {output_dir}/module_tree.png")
    print(f"  dot -Tsvg {tree_file} -o {output_dir}/module_tree.svg")
    print("\nNote: You need Graphviz installed (https://graphviz.org/download/)")
