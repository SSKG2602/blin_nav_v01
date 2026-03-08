# Running BlindNav Locally

## Prerequisites

- Python `3.11+`
- Node.js `20+`
- npm
- Docker and Docker Compose
- Playwright runtime dependencies
- Tesseract OCR available locally if you run the backend outside Docker

## Environment

1. Copy the example file:

```bash
cp .env.example .env
```

2. Fill in the values required for your local environment. At minimum, review:

- `DATABASE_URL`
- `REDIS_URL`
- `FRONTEND_ORIGIN`
- `NEXT_PUBLIC_API_BASE_URL`
- `BROWSER_RUNTIME_BASE_URL`
- `GEMINI_API_KEY`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_REGION`

The backend loads `.env` from `apps/api/app/core/config.py`. The frontend reads `NEXT_PUBLIC_API_BASE_URL`.

## Install dependencies

From the repo root:

```bash
make install
```

That creates a root virtual environment, installs backend and browser-runtime Python dependencies, and installs frontend dependencies under `apps/web`.

## Start infrastructure

Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

## Startup order

Recommended order:

1. browser runtime
2. backend
3. frontend

Individual start commands:

```bash
make dev-runtime
make dev-backend
make dev-frontend
```

Or run all three together:

```bash
make dev
```

Equivalent helper scripts:

- `scripts/dev/start-browser-runtime.sh`
- `scripts/dev/start-backend.sh`
- `scripts/dev/start-frontend.sh`
- `scripts/dev/start-local.sh`

## Local URLs

- frontend shell: `http://localhost:3100`
- backend health: `http://localhost:8100/health`
- backend readiness: `http://localhost:8100/health/ready`
- browser runtime liveness: `http://localhost:8200/health/live`

Port `3000` is intentionally unused.

## Minimal smoke path

1. open the shell at `http://localhost:3100`
2. create an account or sign in
3. start a live session
4. submit a shopping request by voice or text
5. verify transcript updates, runtime mirror updates, and state progression
6. confirm checkpoint and final-confirmation surfaces appear when required
7. verify session history, cart context, and latest-order controls are reachable

## Docker Compose option

For containerized local execution:

```bash
docker compose up --build
```

The compose stack includes:

- frontend
- backend
- browser-runtime
- postgres
- redis

## Notes for local speech

- the default live speech provider is `browser-native`
- browser-native mode uses the client/browser surface for transcript hints and TTS playback behavior
- microphone permission must be granted in the browser when testing live voice input

## Local shutdown

If you used `make dev`, stop the running process in that terminal.

If you used separate processes, stop each one individually and then stop infrastructure:

```bash
docker compose stop postgres redis
```

Use [TROUBLESHOOTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TROUBLESHOOTING.md) if startup or health checks fail.
