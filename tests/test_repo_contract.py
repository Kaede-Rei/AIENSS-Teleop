from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_repository_has_no_lerobot_runtime_imports_or_dependency():
    offenders = []
    for base in (ROOT / "dm_arm_teleop", ROOT / "scripts"):
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "from lerobot" in text or "import lerobot" in text:
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert '"lerobot' not in pyproject
    assert "'lerobot" not in pyproject


def test_expected_entry_scripts_exist():
    assert (ROOT / "scripts" / "teleop.py").is_file()
    assert (ROOT / "scripts" / "leader_test.py").is_file()
    assert (ROOT / "scripts" / "follower_test.py").is_file()


def test_readme_starts_with_hardware_platform_then_quick_start_and_config_before_history():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = [
        "## 1. 硬件与平台",
        "## 2. Quick Start",
        "## 3. 配置 `config/arm.yaml`",
        "## 9. 仓库历史",
    ]
    positions = [readme.find(heading) for heading in headings]
    assert all(pos >= 0 for pos in positions), positions
    assert positions == sorted(positions)
