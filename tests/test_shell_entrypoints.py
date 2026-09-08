from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_and_launch_scripts_exist_and_are_executable():
    for name in ("install.sh", "launch.sh"):
        path = ROOT / name
        assert path.is_file(), f"missing {name}"
        assert os.access(path, os.X_OK), f"{name} is not executable"


def test_shell_entrypoints_have_valid_bash_syntax():
    for name in ("install.sh", "launch.sh"):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / name)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_launch_requires_local_virtualenv_and_points_to_teleop_script():
    text = (ROOT / "launch.sh").read_text(encoding="utf-8")
    assert ".venv/bin/python" in text
    assert "scripts/teleop.py" in text
    assert '"$@"' in text


def test_install_creates_venv_and_installs_project_editable():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "-m venv" in text
    assert "pip install" in text
    assert "-e ." in text


def test_windows_entrypoints_exist_and_target_local_virtualenv():
    install = ROOT / "install.bat"
    launch = ROOT / "launch.bat"
    assert install.is_file(), "missing install.bat"
    assert launch.is_file(), "missing launch.bat"

    install_text = install.read_text(encoding="utf-8")
    assert "-m venv" in install_text
    assert ".venv\\Scripts\\python.exe" in install_text
    assert "pip install" in install_text
    assert "-e ." in install_text

    launch_text = launch.read_text(encoding="utf-8")
    assert ".venv\\Scripts\\python.exe" in launch_text
    assert "scripts\\teleop.py" in launch_text
    assert "%*" in launch_text


def test_readme_documents_windows_one_click_quick_start():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "install.bat" in text
    assert "launch.bat" in text
    assert "COM3" in text
    assert "COM4" in text


def test_windows_installer_avoids_percent_errorlevel_inside_blocks():
    text = (ROOT / "install.bat").read_text(encoding="utf-8").lower()
    assert "%errorlevel%" not in text
    assert "if errorlevel 1" in text
