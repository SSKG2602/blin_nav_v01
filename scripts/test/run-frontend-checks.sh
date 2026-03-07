#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR/apps/web"

if [[ ! -d node_modules ]]; then
  echo "Frontend dependencies are missing. Run: npm install --prefix apps/web"
  exit 1
fi

npm run typecheck
exec npm run build
