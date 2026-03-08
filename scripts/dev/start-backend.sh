#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

cd "$ROOT_DIR/apps/api"
export LIVE_SPEECH_PROVIDER="${LIVE_SPEECH_PROVIDER:-browser-native}"
export LIVE_ENABLE_BROWSER_TTS="${LIVE_ENABLE_BROWSER_TTS:-true}"
export OCR_ENABLED="${OCR_ENABLED:-true}"
exec "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT:-8100}" --reload
