#!/usr/bin/env python3
"""
Version management utility script.

Usage:
    python scripts/bump_version.py 0.4.5
"""
import re
import sys
from pathlib import Path


def bump_version(new_version: str):
    """Update version across all project files."""

    # Validate version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print(f"❌ Invalid version format: {new_version}")
        print("   Expected format: X.Y.Z (e.g., 0.4.5)")
        sys.exit(1)

    files_updated = []

    # 1. Update app/__version__.py
    version_file = Path("app/__version__.py")
    if version_file.exists():
        version_file.write_text(f'"""Version information for multi-agent-local-rag package."""\n__version__ = "{new_version}"\n')
        files_updated.append(str(version_file))
        print(f"✅ Updated {version_file}")
    else:
        print(f"⚠️  {version_file} not found, creating...")
        version_file.write_text(f'"""Version information for multi-agent-local-rag package."""\n__version__ = "{new_version}"\n')
        files_updated.append(str(version_file))

    # 2. Update pyproject.toml
    pyproject_file = Path("pyproject.toml")
    if pyproject_file.exists():
        content = pyproject_file.read_text()
        updated_content = re.sub(
            r'version = "\d+\.\d+\.\d+"',
            f'version = "{new_version}"',
            content
        )
        pyproject_file.write_text(updated_content)
        files_updated.append(str(pyproject_file))
        print(f"✅ Updated {pyproject_file}")

    # 3. Update README.md badge
    readme_file = Path("README.md")
    if readme_file.exists():
        content = readme_file.read_text()
        updated_content = re.sub(
            r'\[!\[Version\]\(https://img\.shields\.io/badge/version-v[\d.]+-blue\.svg\)\]',
            f'[![Version](https://img.shields.io/badge/version-v{new_version}-blue.svg)]',
            content
        )

        # Also update "Latest Release" line if present
        updated_content = re.sub(
            r'\*\*Latest Release\*\*: v[\d.]+',
            f'**Latest Release**: v{new_version}',
            updated_content
        )

        readme_file.write_text(updated_content)
        files_updated.append(str(readme_file))
        print(f"✅ Updated {readme_file}")

    # 4. Update frontend package.json
    frontend_package = Path("frontend/package.json")
    if frontend_package.exists():
        content = frontend_package.read_text()
        updated_content = re.sub(
            r'"version": "\d+\.\d+\.\d+"',
            f'"version": "{new_version}"',
            content
        )
        frontend_package.write_text(updated_content)
        files_updated.append(str(frontend_package))
        print(f"✅ Updated {frontend_package}")

    print(f"\n🎉 Version bumped to {new_version}")
    print(f"📝 Files updated: {len(files_updated)}")
    print("\nNext steps:")
    print(f"  git add {' '.join(files_updated)}")
    print(f"  git commit -m 'chore: bump version to v{new_version}'")
    print(f"  git tag v{new_version}")
    print(f"  git push && git push --tags")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <version>")
        print("Example: python scripts/bump_version.py 0.4.5")
        sys.exit(1)

    bump_version(sys.argv[1])
