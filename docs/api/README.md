# API Notes

The authoritative repo-level API summary is [API_OVERVIEW.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/API_OVERVIEW.md).

This folder note keeps the `docs/api` path available for more detailed endpoint notes without duplicating the top-level overview.

## Current API shape

BlindNav currently exposes route groups for:

- health and readiness
- lightweight auth and user identity
- Amazon.in connect status and redirect support
- session lifecycle, logs, context, and history
- agent-step execution
- live websocket sessions
- checkpoint and final-confirmation resolution
- runtime observation and screenshot inspection
- cart adjustment, latest-order loading, and order cancellation

## Live transport highlights

The live websocket is the main interactive surface for:

- wake-driven spoken input becoming `user_text`
- backend `spoken_output` events
- interruption and cancel
- clarification responses
- checkpoint and final-confirmation resolution

## Contract location

Implementation contracts live in:

- `apps/api/app/schemas`
- `apps/web/lib/types.ts`

## Scope rule

This folder should document only active endpoints and payloads that exist in the runnable codebase.
