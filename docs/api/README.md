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

## Session API v1

- `POST /api/sessions`
  - Creates a new session from `SessionCreate`.
  - Returns `SessionDetail` with generated `session_id`, `status`, and timestamps.
- `GET /api/sessions/{session_id}`
  - Returns a single `SessionDetail`.
  - Returns `404` when the session does not exist.
- `GET /api/sessions`
  - Returns `list[SessionSummary]`.
  - Supports basic `limit`/`offset` and optional `merchant` filtering.
- `POST /api/sessions/{session_id}/logs`
  - Appends one agent log entry for the session.
  - Returns the stored `AgentLogEntry`.
  - Returns `404` when the session does not exist.
- `GET /api/sessions/{session_id}/logs`
  - Returns `list[AgentLogEntry]` for a session.
  - Returns `404` when the session does not exist.

This API layer is transport + persistence only. Agent state machine behavior, Gemini wiring, and browser-runtime execution are layered later.

## Agent Step API v1

- `POST /api/sessions/{session_id}/agent/step`
  - Drives one agent step for the given session.
  - Request body is a discriminated union `AgentEvent` with an `event_type` field, e.g.:
    - `user_intent_parsed`
    - `nav_result`
    - `verification_result`
    - `checkout_progress`
    - `human_checkpoint_resolved`
    - `low_confidence_triggered`
    - `tool_error`
    - `session_close_requested`
  - Response:
    - `new_state`: the updated `AgentState`.
    - `spoken_summary`: optional string the UI can read out to the user.
    - `commands`: list of `AgentCommand` objects (command type + payload) that a tools layer (LLM, browser runtime, etc.) can interpret.
    - `debug_notes`: optional debugging text for logs and development.
  - Returns `404` with `{"detail": "Session not found"}` when the session does not exist.

This API is backend-only orchestration. It does not directly call Gemini or the browser runtime; it just exposes state-machine decisions and audit trail.
