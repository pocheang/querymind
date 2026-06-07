"""
Interactive Project Structure Dashboard
Generates a comprehensive HTML dashboard with multiple visualizations
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import ast
import json


def analyze_project_comprehensive(project_root):
    """Comprehensive project analysis"""
    project_root = Path(project_root)

    data = {
        'files': [],
        'modules': defaultdict(lambda: {'files': 0, 'lines': 0, 'tests': 0}),
        'imports': defaultdict(set),
        'functions': defaultdict(list),
        'classes': defaultdict(list),
        'complexity': []
    }

    for py_file in project_root.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.venv' in str(py_file) or 'worktrees' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.count('\n') + 1

            relative_path = py_file.relative_to(project_root)
            module = str(relative_path.parts[0]) if relative_path.parts else 'root'

            # Update module stats
            data['modules'][module]['files'] += 1
            data['modules'][module]['lines'] += lines
            if 'test' in py_file.name:
                data['modules'][module]['tests'] += 1

            # File info
            data['files'].append({
                'path': str(relative_path),
                'module': module,
                'lines': lines,
                'is_test': 'test' in py_file.name
            })

            # Parse AST for detailed analysis
            try:
                tree = ast.parse(content)

                # Count functions and classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        data['functions'][module].append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        data['classes'][module].append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            data['imports'][str(relative_path)].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            data['imports'][str(relative_path)].add(node.module)

            except:
                pass

        except Exception:
            pass

    return data


def generate_interactive_dashboard(project_root, output_file):
    """Generate comprehensive interactive HTML dashboard"""

    data = analyze_project_comprehensive(project_root)

    # Calculate statistics
    total_files = len(data['files'])
    total_lines = sum(f['lines'] for f in data['files'])
    test_files = sum(1 for f in data['files'] if f['is_test'])
    total_functions = sum(len(funcs) for funcs in data['functions'].values())
    total_classes = sum(len(classes) for classes in data['classes'].values())

    # Module data for charts
    module_names = list(data['modules'].keys())
    module_files = [data['modules'][m]['files'] for m in module_names]
    module_lines = [data['modules'][m]['lines'] for m in module_names]

    # Top files by size
    top_files = sorted(data['files'], key=lambda x: x['lines'], reverse=True)[:15]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Structure Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .dashboard {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            color: #667eea;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.2em;
            color: #666;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}

        .stat-card .icon {{
            font-size: 3em;
            margin-bottom: 10px;
        }}

        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}

        .stat-card .label {{
            font-size: 1em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}

        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}

        .chart-container h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        .table-container {{
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}

        .table-container h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        tr:hover {{
            background: #f5f5f5;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            background: #667eea;
            color: white;
        }}

        .footer {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🎯 Project Structure Dashboard</h1>
            <p>Multi-Agent RAG System - Comprehensive Code Analysis</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="icon">📁</div>
                <div class="number">{total_files}</div>
                <div class="label">Python Files</div>
            </div>
            <div class="stat-card">
                <div class="icon">📝</div>
                <div class="number">{total_lines:,}</div>
                <div class="label">Lines of Code</div>
            </div>
            <div class="stat-card">
                <div class="icon">🧪</div>
                <div class="number">{test_files}</div>
                <div class="label">Test Files</div>
            </div>
            <div class="stat-card">
                <div class="icon">⚡</div>
                <div class="number">{total_functions}</div>
                <div class="label">Functions</div>
            </div>
            <div class="stat-card">
                <div class="icon">🏗️</div>
                <div class="number">{total_classes}</div>
                <div class="label">Classes</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h2>📊 Module Distribution by Files</h2>
                <canvas id="moduleFilesChart"></canvas>
            </div>
            <div class="chart-container">
                <h2>📈 Module Distribution by Lines</h2>
                <canvas id="moduleLinesChart"></canvas>
            </div>
        </div>

        <div class="table-container">
            <h2>📄 Largest Files</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>File Path</th>
                        <th>Module</th>
                        <th>Lines</th>
                    </tr>
                </thead>
                <tbody>
"""

    for i, file_info in enumerate(top_files, 1):
        html += f"""
                    <tr>
                        <td><span class="badge">#{i}</span></td>
                        <td>{file_info['path']}</td>
                        <td>{file_info['module']}</td>
                        <td><strong>{file_info['lines']}</strong></td>
                    </tr>
"""

    html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generated by Project Structure Visualizer | Multi-Agent RAG System</p>
        </div>
    </div>

    <script>
"""

    # Chart data
    html += f"""
        // Module Files Chart
        const moduleFilesCtx = document.getElementById('moduleFilesChart').getContext('2d');
        new Chart(moduleFilesCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(module_names)},
                datasets: [{{
                    label: 'Number of Files',
                    data: {json.dumps(module_files)},
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(255, 107, 107, 0.8)',
                        'rgba(78, 205, 196, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ],
                    borderColor: [
                        'rgb(102, 126, 234)',
                        'rgb(118, 75, 162)',
                        'rgb(255, 107, 107)',
                        'rgb(78, 205, 196)',
                        'rgb(255, 159, 64)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // Module Lines Chart
        const moduleLinesCtx = document.getElementById('moduleLinesChart').getContext('2d');
        new Chart(moduleLinesCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(module_names)},
                datasets: [{{
                    label: 'Lines of Code',
                    data: {json.dumps(module_lines)},
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(255, 107, 107, 0.8)',
                        'rgba(78, 205, 196, 0.8)',
                        'rgba(255, 159, 64, 0.8)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_file


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    output_file = project_root / "docs" / "dashboard.html"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    result = generate_interactive_dashboard(project_root, output_file)
    print(f"Interactive dashboard generated: {result}")
    print(f"Open in browser to view comprehensive visualizations")
