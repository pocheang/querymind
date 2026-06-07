#!/usr/bin/env python3
"""
Quick launcher for all visualization tools
"""

import subprocess
import sys
from pathlib import Path


def run_visualizations():
    """Run all visualization tools"""
    project_root = Path(__file__).parent.parent
    scripts = [
        ('visualize_dashboard.py', 'Generating interactive dashboard...'),
        ('visualize_html.py', 'Generating HTML report...'),
        ('visualize_text.py', 'Generating text report...'),
        ('visualize_dependencies.py', 'Generating dependency graphs...'),
    ]

    print("=" * 80)
    print("PROJECT STRUCTURE VISUALIZATION SUITE")
    print("=" * 80)
    print()

    for script, message in scripts:
        print(f"[*] {message}")
        script_path = project_root / "scripts" / script
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode == 0:
                print(f"    [OK] Success")
            else:
                print(f"    [FAIL] Failed: {result.stderr[:100]}")
        except Exception as e:
            print(f"    [ERROR] Error: {str(e)}")
        print()

    print("=" * 80)
    print("VISUALIZATION COMPLETE!")
    print("=" * 80)
    print()
    print("Generated files:")
    print("  - docs/dashboard.html (Interactive dashboard - RECOMMENDED)")
    print("  - docs/structure_visualization.html (HTML report)")
    print("  - docs/structure_report.txt (Text report)")
    print("  - docs/visualizations/dependencies.dot (Dependency graph)")
    print("  - docs/visualizations/module_tree.dot (Module tree)")
    print()
    print("To view the dashboard, run:")
    print("  python -m webbrowser docs/dashboard.html")
    print()


if __name__ == "__main__":
    run_visualizations()
