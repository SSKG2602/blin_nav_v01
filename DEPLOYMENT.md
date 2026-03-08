# Deployment

## Current deployment surfaces

This repo ships deployment assets for the runnable BlindNav stack:

- backend container image: `infra/docker/backend.Dockerfile`
- frontend container image: `infra/docker/frontend.Dockerfile`
- browser-runtime container image: `infra/docker/playwright.Dockerfile`
- backend Cloud Run template: `infra/cloudrun/service.yaml`
- backend Cloud Run env sample: `infra/cloudrun/env.sample.yaml`
- backend deploy helper: `infra/cloudrun/deploy.sh`

## What is actually covered here

The strongest deployment path in-repo is the backend service on Google Cloud Run. The frontend and browser runtime have Dockerfiles and can be containerized, but this repo does not pretend that a single command deploys the entire multi-service stack to production.

## Backend Cloud Run deployment

Set the required variables locally:

```bash
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_CLOUD_REGION=your-region
export IMAGE=your-image-reference
```

Then run:

```bash
./infra/cloudrun/deploy.sh
```

The deploy script expects:

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_REGION`
- `IMAGE`
- optional `SERVICE_NAME`
- optional `ENV_FILE` pointing to a Cloud Run env YAML

## Required environment and service dependencies

At deployment time, ensure the backend has access to:

- PostgreSQL
- Redis
- browser runtime base URL
- Gemini credentials and model settings
- allowed frontend origin
- optional log bucket configuration

Key settings already present in code and env examples:

- `SERVICE_NAME`
- `ENVIRONMENT`
- `FRONTEND_ORIGIN`
- `BROWSER_RUNTIME_BASE_URL`
- `DATABASE_URL`
- `REDIS_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL_INTENT`
- `GEMINI_MODEL_SUMMARY`
- `GEMINI_MODEL_MULTIMODAL`
- `GEMINI_MODEL_VISION`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_REGION`
- `LOG_BUCKET_NAME`

## Runtime cautions

- do not enable blind autonomous purchase placement without preserving existing checkpoint and final-confirmation behavior
- keep browser-runtime networking and authentication scoped to the trusted deployment environment
- keep frontend origin configuration aligned with the deployed shell host
- do not treat docs-only configuration as deployment proof; verify live health endpoints and session flow after deployment

## Suggested deployment verification

After deploy, verify:

- backend `GET /health`
- backend `GET /health/ready`
- browser-runtime liveness
- auth flow
- live session creation
- websocket connection from the deployed frontend
- checkpoint and final-confirmation flow

## Containerized local preflight

Before deploying remotely, validate the images locally:

```bash
docker compose up --build
```

Use [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md) for the checks that should pass before shipping.
