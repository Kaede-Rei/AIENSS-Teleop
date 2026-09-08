#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
RESET_SCRIPT="$ROOT_DIR/scripts/reset.py"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "[AIENSS-Teleop] Local virtual environment not found" >&2
  echo "Run ./install.sh first" >&2
  exit 1
fi

exec "$VENV_PYTHON" "$RESET_SCRIPT" "$@"
