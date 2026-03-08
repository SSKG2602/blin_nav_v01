# Architecture Notes

This folder is reserved for architecture notes that belong to the runnable repo.

Current status:
- backend/runtime production path exists for deterministic agent orchestration
- browser-runtime action + observation services are wired to backend tools layer
- live-session websocket gateway is available for demo shell integration
- use sibling reference documents as architecture source of truth for scope and behavior

## Backend infra v1

- Configuration uses Pydantic settings (`app/core/config.py`) with `.env` and OS environment variable loading.
- Database wiring is prepared through SQLAlchemy engine + session factory (`app/db/session.py`) and shared base (`app/db/base.py`).
- Redis wiring is prepared through a minimal client helper (`app/core/redis.py`).
- Health endpoint semantics:
  - `GET /health`: process heartbeat only, no infra calls.
  - `GET /health/live`: liveness heartbeat only, no infra calls.
  - `GET /health/ready`: readiness with DB and Redis checks and aggregate status (`ok`, `degraded`, `down`).

### Session & Log Contracts v1

- Sessions are represented via schema contracts:
  - `SessionCreate`
  - `SessionSummary`
  - `SessionDetail`
- Per-step agent activity is represented via `AgentLogEntry`.
- These contracts are shared across API, browser runtime integration boundaries, and future Gemini prompt formats.
- Contracts now have DB persistence in SQLAlchemy ORM models under `app/models/session.py`.
- Repositories in `app/repositories/session_repo.py` form the persistence boundary and convert between ORM rows and Pydantic schemas.
- Future HTTP API and state-machine modules should call repositories rather than accessing ORM models directly.
- Session HTTP endpoints now sit above this repository boundary and delegate persistence operations without embedding ORM access in route handlers.
- State-machine, orchestrator, and evidence/context derivation layers now execute above this spine.

## Live Gateway + Locale Path

- `/api/live/sessions` and websocket stream endpoints provide a session-bound live interface.
- Locale is normalized at ingress (`en-IN`, `hi-IN`) and propagated through:
  - speech provider boundary
  - live websocket event payloads
  - spoken summary output.
- Current speech provider defaults are deterministic fallback-safe; provider-specific STT/TTS integrations remain pluggable via dependency overrides.
