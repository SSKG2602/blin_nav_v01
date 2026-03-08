# BlindNav (`Luminar`)

`blin_nav_v01` is the runnable BlindNav implementation repository for the Gemini Live Agent challenge (`UI Navigator` track). The wake name is `Luminar`.

This repository is intentionally separate from `../Gemini_Hack`. The sibling `Gemini_Hack` folder is reference-only planning/architecture material and is not part of the runnable codebase.

## Current Implementation Snapshot

Implemented now:
- FastAPI backend with deterministic orchestrator + state-machine transitions
- persisted session/log/context layers (PostgreSQL-backed)
- API surface for session lifecycle, agent-step execution, live websocket flow, checkpoint/final-confirmation resolution, and runtime observation/screenshot reads
- browser-runtime service wired through backend tools/executor boundaries
- Gemini-backed interpretation/assessment path with deterministic fallbacks
- derived trust/review/multimodal/control-state/final-confirmation/post-purchase outputs in session context
- Next.js operator shell wired to live/session APIs with consent checkpoints, final confirmation handling, runtime mirror, and event stream panels
- selective prop-driven frontend presentation integration completed for the operator shell (`VoiceMicButton`, `VoiceTranscript`, `AgentSpeechBubble`, `NavigationStatusPanel`)
- Docker Compose wiring for frontend + backend + browser-runtime + Redis + Postgres

Still intentionally limited:
- no claim of fully autonomous production-grade checkout placement
- merchant coverage is demo-focused and bounded, not generalized internet autonomy
- UI is operator/demo-oriented, not production branding-complete

## Pinned Ports

| Surface | Port | Notes |
| --- | --- | --- |
| Frontend | `3100` | Next.js operator shell |
| Backend API | `8100` | FastAPI service |
| Docs / Devtools | `4100` | Reserved for supporting tooling |

Port `3000` is intentionally unused.

## Demo Scope Boundaries

- Primary merchant target: `amazon.in`
- Backup logged-in contingencies: `flipkart.com`, `meesho.com`
- Current implementation is deterministic and checkpoint-gated; it is not an unconstrained autonomous shopper.

## Stack

- Frontend: Next.js 15, TypeScript, Tailwind CSS
- Backend: Python 3.11+, FastAPI, Pydantic v2
- Data plane: Redis + PostgreSQL
- Browser runtime: Playwright Python service
- AI path: Google GenAI SDK + Gemini Live-compatible flow
- Infra: Docker Compose, Cloud Run deployment assets

## Local Startup

Install dependencies:

```bash
make install
```

Run frontend + backend + browser-runtime:

```bash
make dev
```

Run individually:

```bash
make dev-backend
make dev-runtime
make dev-frontend
```

Tests/checks:

```bash
make test-backend
make test-runtime
./scripts/test/run-frontend-checks.sh
```

Container boot:

```bash
docker compose up --build
```

## Branch Discipline

- Use hyphenated branch names only
- Do not use `#` in branch names
- Keep changes bounded and architecture-safe
- Respect ownership boundaries:
  - `sskg-78`: backend, infra, browser runtime, architecture-critical paths
  - `msms-64`: bounded frontend/docs/fixtures support paths

## Repository Boundary

- Edit only files inside `./blin_nav_v01`
- Treat `../Gemini_Hack` as read-only architecture/scope reference
- Keep implementation claims in docs aligned to actual runnable state
