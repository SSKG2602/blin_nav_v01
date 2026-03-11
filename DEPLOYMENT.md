# Deployment

## Target production topology

BlindNav is deployed as a three-service Google Cloud Run stack:

- `blindnav-api`
- `blindnav-browser-runtime`
- `blindnav-web`

The backend remains the orchestration source of truth, the browser-runtime remains the execution and observation boundary, and the frontend remains the operator shell.

## Repo deployment assets

This repo already ships the core deployment assets for that topology:

- backend image: `infra/docker/backend.Dockerfile`
- browser-runtime image: `infra/docker/playwright.Dockerfile`
- frontend image: `infra/docker/frontend.Dockerfile`
- backend Cloud Run template: `infra/cloudrun/service.yaml`
- backend Cloud Run env sample: `infra/cloudrun/env.sample.yaml`
- backend deploy helper: `infra/cloudrun/deploy.sh`

## Service responsibilities

### `blindnav-api`

- deterministic orchestration and state transitions
- auth, session history, checkpoints, final confirmation, logs, and closure artifacts
- live websocket transport
- Gemini-backed interpretation, summarization, and multimodal assistance
- calls into the browser-runtime through `BROWSER_RUNTIME_BASE_URL`

### `blindnav-browser-runtime`

- Playwright browser service
- nopCommerce navigation, DOM interaction, screenshot capture, and observation extraction
- bounded search, product, cart, and checkout-entry actions
- private backend-facing surface where possible

### `blindnav-web`

- Next.js operator shell
- live websocket session control
- wake flow, browser-native speech capture, and browser-native spoken replies
- browser activity panel, runtime visibility, checkpoint/final-confirmation UI, and session history

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

```bash
export GOOGLE_CLOUD_PROJECT=your-project
export GOOGLE_CLOUD_REGION=your-region
export IMAGE=your-backend-image
./infra/cloudrun/deploy.sh
```

### Browser-runtime

Deploy the browser-runtime as a separate Cloud Run service from `infra/docker/playwright.Dockerfile`, then point the backend `BROWSER_RUNTIME_BASE_URL` at the deployed runtime URL or internal address.

### Frontend

Deploy the frontend as a separate Cloud Run service from `infra/docker/frontend.Dockerfile`, passing `NEXT_PUBLIC_API_BASE_URL` so the shell points at the deployed backend.

## Runtime cautions

- do not weaken checkpoints, final confirmation, recovery, or low-confidence behavior to simplify deployment
- keep browser-runtime access scoped to the backend or trusted internal callers
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
- the bounded nopCommerce flow can search, verify a supported product, add to cart, verify the cart, and recognize checkout entry
- BlindNav stops before guest checkout

## Demo merchant note

The active public demo merchant is `demo.nopcommerce.com`.

Deployment claims should stay bounded to:

- search
- product verification
- cart verification
- checkout-entry recognition
- intentional stop before guest checkout

Do not describe the deployed demo as full checkout automation.
