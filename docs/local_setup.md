# Local Setup

This guide runs BlindNav locally with Docker Compose.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Node.js `>=20` (for direct frontend runs)
- Python `3.11+` (for direct backend runs)

## Quick Start (Docker Compose)

From repository root:

```bash
docker compose up --build
```

Expected local ports:

- Frontend: `http://localhost:3100`
- Backend: `http://localhost:8100`

Websocket endpoint used by frontend:

- `ws://localhost:8100/session`

## Service Checks

1. Frontend check
- Open `http://localhost:3100`.
- Confirm Luminar voice UI loads.

2. Backend check
- Open `http://localhost:8100/docs` (if FastAPI docs are enabled).
- Confirm backend container is healthy in `docker compose ps`.

3. Realtime check
- Start frontend.
- Click mic and speak.
- Confirm timeline/status updates appear in UI as websocket events stream in.

## Common Commands

```bash
# Start detached
docker compose up -d --build

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Optional Non-Docker Run

Repository Makefile shortcuts:

```bash
make install
make dev
```

Or per service:

```bash
make dev-frontend
make dev-backend
```
