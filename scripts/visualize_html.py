#!/usr/bin/env python3
"""
Generate HTML visualization of project structure
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import ast
import json


def analyze_structure(directory):
    """Analyze project structure"""
    directory = Path(directory)
    stats = {
        'total_py_files': 0,
        'total_lines': 0,
        'modules': defaultdict(int),
        'test_files': 0,
        'largest_files': [],
        'file_details': []
    }

    for py_file in directory.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.venv' in str(py_file) or 'worktrees' in str(py_file):
            continue

        stats['total_py_files'] += 1

        if 'test' in py_file.name:
            stats['test_files'] += 1

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                stats['total_lines'] += lines

                relative_path = py_file.relative_to(directory)
                module = str(relative_path.parts[0]) if relative_path.parts else 'root'
                stats['modules'][module] += 1

                stats['file_details'].append({
                    'path': str(relative_path),
                    'lines': lines,
                    'module': module
                })

                stats['largest_files'].append((str(relative_path), lines))
        except Exception:
            pass

    stats['largest_files'].sort(key=lambda x: x[1], reverse=True)
    stats['largest_files'] = stats['largest_files'][:20]

    return stats


def get_tree_structure(directory, max_depth=3):
    """Get tree structure as nested dict"""
    directory = Path(directory)
    ignore_patterns = {
        '__pycache__', '.pyc', '.git', '.venv', 'node_modules',
        '.ruff_cache', '.pytest_cache', '.tmp', 'worktrees'
    }

    def build_tree(path, current_depth=0):
        if max_depth is not None and current_depth >= max_depth:
            return None

        tree = {'name': path.name, 'type': 'dir' if path.is_dir() else 'file', 'children': []}

        if path.is_dir():
            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                items = [item for item in items if not any(pattern in str(item) for pattern in ignore_patterns)]

                for item in items:
                    child = build_tree(item, current_depth + 1)
                    if child:
                        tree['children'].append(child)
            except PermissionError:
                pass

        return tree

    return build_tree(directory)


def analyze_imports(directory):
    """Analyze Python imports"""
    directory = Path(directory)
    imports_map = defaultdict(set)

    for py_file in directory.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.venv' in str(py_file) or 'worktrees' in str(py_file):
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
        except Exception:
            pass

    return imports_map


def generate_html(project_root, output_file):
    """Generate HTML visualization"""
    project_root = Path(project_root)

    # Analyze project
    stats = analyze_structure(project_root)
    tree = get_tree_structure(project_root, max_depth=4)

    app_dir = project_root / "app"
    imports = {}
    internal_imports = defaultdict(int)

    if app_dir.exists():
        imports = analyze_imports(app_dir)
        for file, imported_modules in imports.items():
            for module in imported_modules:
                if module.startswith('app.'):
                    internal_imports[module] += 1

    # Generate HTML
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Structure Visualization</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .content {
            padding: 30px;
        }

        .section {
            margin-bottom: 40px;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            font-size: 1.8em;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .stat-card .number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }

        .stat-card .label {
            color: #666;
            font-size: 1em;
        }

        .tree {
            font-family: 'Courier New', monospace;
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            line-height: 1.6;
            max-height: 600px;
            overflow-y: auto;
        }

        .tree-item {
            padding: 2px 0;
        }

        .tree-dir {
            color: #66d9ef;
            font-weight: bold;
        }

        .tree-file {
            color: #a6e22e;
        }

        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }

        .bar {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }

        .bar-label {
            min-width: 200px;
            font-weight: 500;
            color: #555;
        }

        .bar-graph {
            flex-grow: 1;
            background: #e0e0e0;
            height: 30px;
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }

        .bar-fill {
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 10px;
            color: white;
            font-weight: bold;
            transition: width 1s ease;
        }

        .table {
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            margin-top: 20px;
        }

        .table table {
            width: 100%;
            border-collapse: collapse;
        }

        .table th {
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }

        .table td {
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }

        .table tr:hover {
            background: #f5f5f5;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            background: #667eea;
            color: white;
        }

        .module-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .module-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .module-card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
        }

        .module-card .count {
            font-size: 2em;
            font-weight: bold;
            color: #764ba2;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Project Structure Visualization</h1>
            <p>Multi-Agent RAG System - Code Analysis</p>
        </div>

        <div class="content">
"""

    # Statistics section
    html += """
            <div class="section">
                <h2>📊 Project Statistics</h2>
                <div class="stats-grid">
"""

    html += f"""
                    <div class="stat-card">
                        <div class="number">{stats['total_py_files']}</div>
                        <div class="label">Python Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{stats['total_lines']:,}</div>
                        <div class="label">Lines of Code</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{stats['test_files']}</div>
                        <div class="label">Test Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="number">{len(stats['modules'])}</div>
                        <div class="label">Modules</div>
                    </div>
"""

    html += """
                </div>
            </div>
"""

    # Module distribution
    html += """
            <div class="section">
                <h2>📦 Module Distribution</h2>
                <div class="chart-container">
"""

    max_files = max(stats['modules'].values()) if stats['modules'] else 1
    for module, count in sorted(stats['modules'].items(), key=lambda x: x[1], reverse=True)[:10]:
        width = (count / max_files) * 100
        html += f"""
                    <div class="bar">
                        <div class="bar-label">{module}</div>
                        <div class="bar-graph">
                            <div class="bar-fill" style="width: {width}%">{count}</div>
                        </div>
                    </div>
"""

    html += """
                </div>
            </div>
"""

    # Largest files
    html += """
            <div class="section">
                <h2>📄 Largest Files</h2>
                <div class="table">
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>File Path</th>
                                <th>Lines</th>
                            </tr>
                        </thead>
                        <tbody>
"""

    for i, (file_path, lines) in enumerate(stats['largest_files'][:15], 1):
        html += f"""
                            <tr>
                                <td><span class="badge">#{i}</span></td>
                                <td>{file_path}</td>
                                <td><strong>{lines}</strong></td>
                            </tr>
"""

    html += """
                        </tbody>
                    </table>
                </div>
            </div>
"""

    # Import analysis
    if internal_imports:
        html += """
            <div class="section">
                <h2>🔗 Most Imported Internal Modules</h2>
                <div class="chart-container">
"""

        max_imports = max(internal_imports.values()) if internal_imports else 1
        for module, count in sorted(internal_imports.items(), key=lambda x: x[1], reverse=True)[:15]:
            width = (count / max_imports) * 100
            html += f"""
                    <div class="bar">
                        <div class="bar-label">{module}</div>
                        <div class="bar-graph">
                            <div class="bar-fill" style="width: {width}%">{count}</div>
                        </div>
                    </div>
"""

        html += """
                </div>
            </div>
"""

    # Footer
    html += """
        </div>
    </div>

    <script>
        // Animate bars on load
        window.addEventListener('load', function() {
            const fills = document.querySelectorAll('.bar-fill');
            fills.forEach(fill => {
                const width = fill.style.width;
                fill.style.width = '0%';
                setTimeout(() => {
                    fill.style.width = width;
                }, 100);
            });
        });
    </script>
</body>
</html>
"""

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_file


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    output_file = project_root / "docs" / "structure_visualization.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    result_file = generate_html(project_root, output_file)

    print(f"HTML visualization generated: {result_file}")
    print(f"Open it in your browser to view the interactive visualization")
