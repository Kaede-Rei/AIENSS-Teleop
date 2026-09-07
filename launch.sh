#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OS_NAME="$(uname -s 2>/dev/null || true)"
if [[ "$OS_NAME" != "Linux" ]]; then
  cat >&2 <<'EOF'
[AIENSS-Teleop] launch.sh is intended for native Linux.
For native Windows, run scripts/teleop.py with .venv\\Scripts\\python and COM ports as documented in README.md.
EOF
  exit 2
fi

VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "[AIENSS-Teleop] Missing .venv. Run ./install.sh first." >&2
  exit 1
fi

exec "$VENV_PYTHON" "$ROOT_DIR/scripts/teleop.py" "$@"
