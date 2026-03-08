# API Overview

BlindNav exposes a compact backend API centered on session lifecycle, live orchestration, runtime inspection, and user-controlled consent flows.

## Health

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Auth

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`

These endpoints support lightweight demo auth and user-scoped session history.

## Sessions

- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/logs`
- `GET /api/sessions/{session_id}/logs`
- `GET /api/sessions/{session_id}/context`

## Control-state and consent

- `GET /api/sessions/{session_id}/checkpoint`
- `POST /api/sessions/{session_id}/checkpoint/resolve`
- `GET /api/sessions/{session_id}/final-confirmation`
- `POST /api/sessions/{session_id}/final-confirmation/resolve`

## Agent step execution

- `POST /api/sessions/{session_id}/agent/step`

This is the deterministic state-machine step surface used by the backend orchestration flow.

## Runtime inspection and grounded support

- `GET /api/sessions/{session_id}/runtime/observation`
- `GET /api/sessions/{session_id}/runtime/screenshot`
- `POST /api/sessions/{session_id}/cart/remove`
- `POST /api/sessions/{session_id}/cart/quantity`
- `POST /api/sessions/{session_id}/orders/latest`
- `GET /api/sessions/{session_id}/orders/latest`

## Live session API

- `POST /api/live/sessions`
- `WS /api/live/sessions/{session_id}/stream`

The websocket supports live session events including session start, user text, audio, interruption, cancel, checkpoint resolution, and final-confirmation resolution.

## Contract ownership

Schema contracts live under `apps/api/app/schemas`. Frontend type mirrors live under `apps/web/lib/types.ts`.

For architecture context, see [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md).
