# API Docs

Current backend surface:
- `GET /health` - process heartbeat (`status=ok`), no infra dependency checks
- `GET /health/live` - liveness probe (`status=ok`), no infra dependency checks
- `GET /health/ready` - readiness probe with dependency checks (`checks.db`, `checks.redis`) and aggregate status (`ok`, `degraded`, `down`)

All endpoints are foundation-level health endpoints only.

## Core API Contracts (Schemas Only)

Session contracts:
- `SessionCreate`: input payload for starting a voice shopping session; includes `merchant`, `locale`, `screen_reader`, `client_version`, and `user_agent`.
- `SessionSummary`: lightweight session metadata for listing/overview surfaces; includes `session_id`, `merchant`, `status`, and `created_at`.
- `SessionDetail`: extended session view based on `SessionSummary`, adding `locale`, `screen_reader`, and `client_version`.
- Session enums:
  - `Merchant`: `amazon.in`, `flipkart.com`, `meesho.com`
  - `SessionStatus`: `active`, `ended`, `cancelled`, `error`

Agent log contract:
- `AgentLogEntry`: per-step audit record with `session_id`, `step_type`, state transition fields, tool excerpts, confidence/checkpoint flags, user spoken summary, error fields, and `created_at`.
- `AgentStepType`: step taxonomy (`perception`, `intent_parse`, `navigation`, `verification`, `checkout`, `error`, `meta`) used for audit trail, user-facing explanation, and debugging.

### Persistence Core v1 (Sessions & Agent Logs)

- `SessionORM` and `AgentLogORM` provide SQLAlchemy-backed persistence models for the session and agent-log schema contracts.
- Repository boundary (`app/repositories/session_repo.py`) handles ORM-to-schema mapping through:
  - `create_session`, `get_session`, `list_sessions`
  - `append_agent_log`, `list_agent_logs_for_session`
- This layer is persistence-only. No HTTP routes, orchestration logic, or merchant-specific behavior is attached yet.
