# Architecture Notes

This folder is reserved for architecture notes that belong to the runnable repo.

Current status:
- foundation only
- no canonical feature modules implemented yet
- use the sibling reference documents for planning context, not for in-repo source of truth

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
- No state machine behavior is implemented here yet; this remains a persistence-first schema spine.
