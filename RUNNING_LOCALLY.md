# Running BlindNav Locally

## Prerequisites

- Python `3.11+`
- Node.js `20+`
- npm
- Docker and Docker Compose
- Playwright runtime dependencies
- Tesseract OCR if you run backend/runtime outside containers
- Chrome or Edge for the full wake-word and browser-native TTS path

## Environment

1. Copy the root example file:

```bash
cp .env.example .env
```

2. Review the shared values that connect all three services:

- `DATABASE_URL`
- `REDIS_URL`
- `FRONTEND_ORIGIN`
- `NEXT_PUBLIC_API_BASE_URL`
- `BROWSER_RUNTIME_BASE_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL_INTENT`
- `GEMINI_MODEL_SUMMARY`
- `GEMINI_MODEL_MULTIMODAL`
- `GEMINI_MODEL_VISION`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_REGION`

The frontend reads `NEXT_PUBLIC_API_BASE_URL`. The backend reads the shared root `.env`. The browser-runtime is reached through `BROWSER_RUNTIME_BASE_URL`.

## Install dependencies

From the repo root:

```bash
make install
```

## Start infrastructure

Start PostgreSQL and Redis first:

```bash
docker compose up -d postgres redis
```

## Startup order

Recommended order for the live stack:

1. browser-runtime
2. backend API
3. frontend shell

Individual commands:

```bash
make dev-runtime
make dev-backend
make dev-frontend
```

Or start all three together:

```bash
make dev
```

## Local URLs

- frontend shell: `http://localhost:3100`
- backend health: `http://localhost:8100/health`
- backend readiness: `http://localhost:8100/health/ready`
- backend liveness: `http://localhost:8100/health/live`
- browser-runtime liveness: `http://localhost:8200/health/live`

Port `3000` is intentionally unused.

## Manual bounded smoke path

1. Open `http://localhost:3100`.
2. Create an account or sign in.
3. Start a live session.
4. Click `Wake Luminar`.
5. Confirm microphone permission appears in Chrome or Edge.
6. Say `Luminar`.
7. Speak `find one m8`.
8. Confirm the transcript panel updates immediately.
9. Confirm the backend processes the command over the live websocket as `user_text`.
10. Confirm spoken backend replies are read aloud through browser-native TTS.
11. Confirm the `Browser Activity` panel shows screenshot thumbnail, current URL, and status text.
12. Confirm the live navigation lands on `demo.nopcommerce.com`.
13. Confirm search results are summarized coherently.
14. Confirm the supported simple product is verified and added to cart.
15. Confirm cart verification is spoken coherently.
16. Confirm checkout entry is recognized.
17. Confirm BlindNav stops before guest checkout.

Optional blocker smoke:

1. search for `build your own computer`
2. confirm BlindNav blocks before add-to-cart
3. confirm the blocker reason is spoken and visible in logs

For the full operator script, use [docs/demo/OPERATOR_GUIDE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/docs/demo/OPERATOR_GUIDE.md).

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

## Notes for local voice

- the default live speech provider is `browser-native`
- wake-word capture and voice command recognition rely on browser speech recognition support
- browser-native TTS relies on `window.speechSynthesis`
- Chrome or Edge is the supported browser path for the full voice experience
- if speech recognition is unavailable, typed input remains available in the shell

## Local shutdown

If you used `make dev`, stop that process in its terminal.

If you used separate processes, stop each one individually and then stop infrastructure:

```bash
docker compose stop postgres redis
```

Use [TROUBLESHOOTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TROUBLESHOOTING.md) if startup, health checks, voice flow, or browser activity visibility fail.
