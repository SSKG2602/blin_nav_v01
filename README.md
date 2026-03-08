# BlindNav

`blin_nav_v01` is the shippable repository bootstrap for BlindNav, a hackathon project in the UI Navigator track. The product wake name is `Luminar`.

This repository is intentionally separate from `../Gemini_Hack`. The sibling `Gemini_Hack` folder is reference-only planning material used to pin structure, stack, and deployment direction. It is not part of the runnable repo, and nothing inside it should be modified from this repository.

## Current Status

The repo now includes a working backend/runtime pipeline plus a demo-oriented web shell.

Implemented now:
- FastAPI backend with deterministic agent state machine + orchestrator
- session, log, and session-context persistence
- agent-step API, live-session API, checkpoint APIs, context API
- browser-runtime service with merchant actions + observation endpoints
- Gemini-backed services with deterministic safe fallbacks
- multimodal/control-state/trust/review/final-confirmation/post-purchase derivations
- Next.js demo shell wired to backend live/session APIs
- Docker Compose wiring for frontend + backend + browser-runtime + Redis + Postgres

Still intentionally limited:
- no fully autonomous final-purchase execution
- no polished production UI/branding
- no full multilingual voice provider stack (fallback-safe live speech boundary exists)

## Pinned Ports

| Surface | Port | Notes |
| --- | --- | --- |
| Frontend | `3100` | Next.js app |
| Backend API | `8100` | FastAPI service |
| Docs / Devtools | `4100` | Reserved for later tooling only |

Port `3000` is intentionally unused.

## Demo Target Scope

- Primary merchant demo target: `amazon.in`
- Backup logged-in contingencies only: Flipkart and Meesho
- Current bootstrap does not implement any merchant flow

## Pinned Stack

- Frontend: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui scaffold
- Backend: Python 3.11+, FastAPI, Pydantic v2
- Data plane: Redis and PostgreSQL
- Browser runtime: Playwright Python
- AI path: Google GenAI SDK and Gemini Live API
- Infra: Docker Compose, Cloud Run, Cloud Storage, GitHub Actions

## Local Startup

Install dependencies first:

```bash
make install
```

`make install` creates a local `.venv` for backend dependencies and installs frontend dependencies under `apps/web`.

Run backend + browser-runtime + frontend in one command:

```bash
make dev
```

Run individual services:

```bash
make dev-backend
make dev-runtime
make dev-frontend
```

Run backend tests:

```bash
make test-backend
```

Run browser-runtime tests:

```bash
make test-runtime
```

Run frontend checks:

```bash
./scripts/test/run-frontend-checks.sh
```

Docker-based local boot:

```bash
docker compose up --build
```

## Branch Discipline

- Use hyphenated branch names only
- Keep shared foundation work small and reviewable
- Do not use `#` in branch names
- Respect shared ownership boundaries:
  - `sskg-78`: backend, infra, browser runtime, AI integration, architecture-critical paths
  - `msms-64`: bounded frontend, docs, fixtures, smoke-oriented support paths

Examples:
- `foundation-repo-bootstrap`
- `sskg-78-backend-base`
- `msms-64-frontend-shell`

## Repository Boundary

- Edit only files inside `./blin_nav_v01`
- Treat `../Gemini_Hack` as read-only reference input
- Keep the scaffold honest: foundation first, feature modules later
