"""
版本一致性测试

确保VERSION、pyproject.toml、app/__version__.py和README中的版本号保持一致
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    """读取文件内容"""
    return (ROOT / path).read_text(encoding="utf-8")


def test_version_files_exist():
    """验证所有版本文件存在"""
    assert (ROOT / "VERSION").exists(), "VERSION file missing"
    assert (ROOT / "pyproject.toml").exists(), "pyproject.toml missing"
    assert (ROOT / "app" / "__version__.py").exists(), "app/__version__.py missing"
    assert (ROOT / "README.md").exists(), "README.md missing"


def test_version_files_match():
    """验证所有版本文件中的版本号一致"""

    # 读取VERSION文件
    version_file = _read("VERSION").strip()

    # 读取pyproject.toml中的版本
    pyproject_content = _read("pyproject.toml")
    pyproject_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', pyproject_content)
    pyproject_version = pyproject_match.group(1) if pyproject_match else None

    # 读取app/__version__.py
    version_py = _read("app/__version__.py")
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', version_py)
    app_version = version_match.group(1) if version_match else None

    # 验证VERSION和pyproject.toml一致
    assert pyproject_version is not None, "Could not parse version from pyproject.toml"
    assert version_file == pyproject_version, f"VERSION ({version_file}) != pyproject.toml ({pyproject_version})"

    # 验证VERSION和__version__.py一致
    assert app_version is not None, "Could not parse version from app/__version__.py"
    assert version_file == app_version, f"VERSION ({version_file}) != app/__version__.py ({app_version})"


def test_readme_version_badge():
    """验证README中的版本徽章与VERSION一致（如果存在）"""
    version_file = _read("VERSION").strip()
    readme = _read("README.md")

    # 查找版本徽章
    badge_match = re.search(r"badge/version-v([\d.]+)", readme)

    if badge_match:
        readme_version = badge_match.group(1)
        assert version_file == readme_version, f"VERSION ({version_file}) != README badge ({readme_version})"


def test_version_format():
    """验证版本号格式符合语义化版本规范"""
    version_file = _read("VERSION").strip()

    # 语义化版本格式：MAJOR.MINOR.PATCH
    version_pattern = r"^\d+\.\d+\.\d+$"
    assert re.match(version_pattern, version_file), (
        f"Version '{version_file}' does not match semantic versioning format (MAJOR.MINOR.PATCH)"
    )


def test_changelog_mentions_current_version():
    """验证CHANGELOG中提到了当前版本"""
    version_file = _read("VERSION").strip()
    changelog = _read("CHANGELOG.md")

    # 检查CHANGELOG中是否提到当前版本
    version_mentioned = (
        f"[{version_file}]" in changelog
        or f"## {version_file}" in changelog
        or f"# {version_file}" in changelog
        or f"v{version_file}" in changelog
    )

    assert version_mentioned, f"Current version {version_file} not found in CHANGELOG.md"
