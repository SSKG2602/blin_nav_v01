# Deployment

## Target production topology

BlindNav is deployed as a three-service Google Cloud Run stack:

- `blindnav-api`
- `blindnav-browser-runtime`
- `blindnav-web`

Each service has its own container image and its own runtime concerns. The backend remains the orchestration source of truth, the browser-runtime remains the execution/observation boundary, and the frontend remains the operator shell.

## Repo deployment assets

This repo already ships the core deployment assets needed for that topology:

- backend image: `infra/docker/backend.Dockerfile`
- browser-runtime image: `infra/docker/playwright.Dockerfile`
- frontend image: `infra/docker/frontend.Dockerfile`
- backend Cloud Run template: `infra/cloudrun/service.yaml`
- backend Cloud Run env sample: `infra/cloudrun/env.sample.yaml`
- backend deploy helper: `infra/cloudrun/deploy.sh`

The backend has first-class Cloud Run manifests in the repo today. The browser-runtime and frontend are documented as separate Cloud Run services built from the existing Dockerfiles and wired through environment configuration.

## Service responsibilities

### `blindnav-api`

- FastAPI backend
- deterministic orchestration and state transitions
- auth, session history, checkpoints, final confirmation, logs, and closure artifacts
- live websocket transport
- Gemini 2.5 Flash-backed interpretation, summarization, and multimodal assistance
- calls into the browser-runtime through `BROWSER_RUNTIME_BASE_URL`

### `blindnav-browser-runtime`

- Playwright browser service
- merchant navigation, DOM interaction, screenshot capture, and observation extraction
- cart, checkout, latest-order, and bounded cancellation actions
- remains private to the backend-facing network surface where possible

### `blindnav-web`

- Next.js operator shell
- live websocket session control
- voice wake flow, browser-native speech capture, and browser-native spoken replies
- browser activity panel, runtime visibility, checkpoint/final-confirmation UI, cart/order actions, and session history

## Environment wiring

### Backend

The backend service must be configured with:

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

The docs target Gemini 2.5 Flash as the deployed model family for those Gemini model variables.

### Browser-runtime

The browser-runtime service must:

- expose port `8200`
- be reachable from the backend at `BROWSER_RUNTIME_BASE_URL`
- run in a trusted environment because it holds merchant browsing state
- preserve screenshot and observation routes used by the frontend visibility layer through the backend

### Frontend

The frontend service must be configured with:

- `NEXT_PUBLIC_API_BASE_URL`

The deployed frontend origin must match the backend `FRONTEND_ORIGIN` CORS setting.

## Cloud Run deployment shape

### Backend

The backend already has a repo-local Cloud Run template and env sample. A typical backend deploy still uses:

```bash
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_CLOUD_REGION=your-region
export IMAGE=your-backend-image
./infra/cloudrun/deploy.sh
```

### Browser-runtime

Deploy the browser-runtime as a separate Cloud Run service from `infra/docker/playwright.Dockerfile`, then point the backend `BROWSER_RUNTIME_BASE_URL` at the deployed runtime URL or a private internal address if you are using service-to-service networking.

### Frontend

Deploy the frontend as a separate Cloud Run service from `infra/docker/frontend.Dockerfile`, passing `NEXT_PUBLIC_API_BASE_URL` at build or deploy time so the shell points to the deployed backend.

## Runtime cautions

- do not weaken checkpoints, final confirmation, or low-confidence behavior to simplify deployment
- keep browser-runtime access scoped to the backend or trusted internal callers
- keep live order context and browser state within controlled environments
- verify screenshot, observation, and websocket flows after deploy instead of treating container startup as proof
- keep frontend and backend origins aligned so websocket and auth flows work correctly

## Suggested deployment verification

After all three services are deployed, verify:

- backend `GET /health`
- backend `GET /health/live`
- backend `GET /health/ready`
- browser-runtime `GET /health/live`
- frontend shell can sign in and create a live session
- websocket connection succeeds from the deployed frontend
- wake flow, spoken reply playback, and browser activity panel behave correctly
- demo-store search/product/cart flow, latest-order loading, and bounded order cancellation remain reachable where implemented
- checkpoint and final-confirmation paths still pause and resume correctly

## Containerized local preflight

Before deploying remotely, validate the three-service stack locally:

```bash
docker compose up --build
```

Use [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md) for the checks that should pass before shipping.

## Demo Merchant Note

Phase 1 deploys BlindNav against a single rehearsed public merchant at `demo.nopcommerce.com`.
The deployed story should present search, product detail, cart, and runtime visibility as
the active bounded demo path. Do not claim robust end-to-end nopCommerce checkout reliability
unless later phases validate that behavior.
