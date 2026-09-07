#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OS_NAME="$(uname -s 2>/dev/null || true)"
if [[ "$OS_NAME" != "Linux" ]]; then
  cat >&2 <<'EOF'
[AIENSS-Teleop] install.sh is intended for native Linux.
For native Windows, use the manual Python setup in README.md and configure COM ports.
EOF
  exit 2
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[AIENSS-Teleop] Python not found: $PYTHON_BIN" >&2
  echo "Install Python >= 3.10 first, or run: PYTHON_BIN=/path/to/python ./install.sh" >&2
  exit 1
fi

if ! "$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(1)
print(f"[AIENSS-Teleop] Python {sys.version.split()[0]}")
PY
then
  echo "[AIENSS-Teleop] Python >= 3.10 is required." >&2
  exit 1
fi

VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "[AIENSS-Teleop] Creating virtual environment: .venv"
  if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
    cat >&2 <<'EOF'
[AIENSS-Teleop] Failed to create .venv.
On Ubuntu/Debian, install the venv module first, for example:
  sudo apt install python3-venv
Then run ./install.sh again.
EOF
    exit 1
  fi
fi

echo "[AIENSS-Teleop] Updating pip/setuptools/wheel..."
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

echo "[AIENSS-Teleop] Installing project and runtime dependencies..."
"$VENV_PYTHON" -m pip install -e .

cat <<'EOF'

[AIENSS-Teleop] Installation complete.

Next:
  1. Edit config/arm.yaml and confirm both serial ports.
  2. Optional read-only checks:
       ./.venv/bin/python scripts/leader_test.py
       ./.venv/bin/python scripts/follower_test.py
  3. Start teleoperation:
       ./launch.sh
EOF
