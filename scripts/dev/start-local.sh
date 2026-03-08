#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT_DIR/scripts/dev/start-backend.sh" &
BACKEND_PID=$!

"$ROOT_DIR/scripts/dev/start-browser-runtime.sh" &
RUNTIME_PID=$!

"$ROOT_DIR/scripts/dev/start-frontend.sh" &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$RUNTIME_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$RUNTIME_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait "$BACKEND_PID" "$RUNTIME_PID" "$FRONTEND_PID"
