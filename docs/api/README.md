# API Docs

Current backend surface includes deterministic orchestration endpoints, live-session transport, and runtime observation bridges.

## Health Endpoints

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

`/health/ready` includes DB/Redis checks and aggregate status (`ok`, `degraded`, `down`).

## Session + Logs API

- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions`
- `POST /api/sessions/{session_id}/logs`
- `GET /api/sessions/{session_id}/logs`

## Deterministic Agent-Step API

- `POST /api/sessions/{session_id}/agent/step`

This executes one orchestrated state-machine step, emits agent commands for the tools layer, updates context evidence, and returns the new state + spoken summary.

## Context / Consent / Runtime APIs

- `GET /api/sessions/{session_id}/context`
- `GET /api/sessions/{session_id}/checkpoint`
- `POST /api/sessions/{session_id}/checkpoint/resolve`
- `GET /api/sessions/{session_id}/final-confirmation`
- `POST /api/sessions/{session_id}/final-confirmation/resolve`
- `GET /api/sessions/{session_id}/runtime/observation`
- `GET /api/sessions/{session_id}/runtime/screenshot`

## Live Session API

- `POST /api/live/sessions`
- `WS /api/live/sessions/{session_id}/stream`

Live websocket flow supports start/user_text/audio/interrupt/cancel and consent resolution events, and emits transcription/intent/agent-step/spoken-output/control-state events for the operator shell.

## Contract Notes

- Session, context, control-state, purchase-support, trust, review, and multimodal schemas are active and used by route handlers and orchestration layers.
- Locale is normalized (`en-IN`, `hi-IN`) at live ingress and propagated through spoken/transcription payloads.
- Claims here are implementation-grounded; this doc intentionally avoids speculative future endpoint claims.
