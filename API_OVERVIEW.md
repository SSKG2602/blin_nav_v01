# API Overview

BlindNav exposes a compact backend API centered on auth, session lifecycle, deterministic orchestration, runtime inspection, live websocket transport, and user-controlled consent flows.

## Health

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Auth

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/auth/me`

These routes support lightweight demo auth and user-scoped session history.

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

This remains the deterministic state-machine step surface used by the backend orchestration flow.

## Runtime inspection and grounded support

- `GET /api/sessions/{session_id}/runtime/observation`
- `GET /api/sessions/{session_id}/runtime/screenshot`
- `POST /api/sessions/{session_id}/cart/remove`
- `POST /api/sessions/{session_id}/cart/quantity`
- `POST /api/sessions/{session_id}/orders/latest`
- `GET /api/sessions/{session_id}/orders/latest`
- `POST /api/sessions/{session_id}/orders/cancel`

These routes support the operator shell’s runtime mirror, browser activity panel, cart management, latest-order loading, and bounded cancellation flow.

The active public demo merchant is `demo.nopcommerce.com`. The public shell no longer depends on a merchant cookie-connect route.

## Live session API

- `POST /api/live/sessions`
- `WS /api/live/sessions/{session_id}/stream`

The live websocket supports:

- session creation and `start`
- wake-driven spoken input normalized into `user_text`
- optional `audio_chunk` transport
- backend-emitted `spoken_output`
- interruption and cancel events
- clarification responses
- checkpoint resolution
- final-confirmation resolution

## Contract ownership

Schema contracts live under `apps/api/app/schemas`. Frontend type mirrors live under `apps/web/lib/types.ts`.

For architecture context, see [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md).
