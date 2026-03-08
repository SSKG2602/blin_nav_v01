#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

cd "$ROOT_DIR/browser-runtime"
exec "$PYTHON_BIN" -m uvicorn browser_runtime.main:app \
  --app-dir "$ROOT_DIR/browser-runtime" \
  --host 0.0.0.0 \
  --port "${BROWSER_RUNTIME_PORT:-8200}" \
  --reload
