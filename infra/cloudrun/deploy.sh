#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-blindnav-api}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_REGION:-}"
IMAGE="${IMAGE:-}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/infra/cloudrun/env.sample.yaml}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "GOOGLE_CLOUD_PROJECT is required."
  exit 1
fi

if [[ -z "$REGION" ]]; then
  echo "GOOGLE_CLOUD_REGION is required."
  exit 1
fi

if [[ -z "$IMAGE" ]]; then
  echo "IMAGE is required."
  exit 1
fi

gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$IMAGE" \
  --platform managed \
  --port 8100 \
  --allow-unauthenticated \
  --timeout 3600 \
  --env-vars-file "$ENV_FILE"
