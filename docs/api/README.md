# API Notes

The authoritative repo-level API summary is [API_OVERVIEW.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/API_OVERVIEW.md).

This folder-level note exists to keep the `docs/api` path available for more detailed route and payload notes if they need to be expanded later.

## Current API shape

BlindNav currently exposes route groups for:

- health
- lightweight auth
- session lifecycle and history
- agent-step execution
- live websocket sessions
- checkpoint and final-confirmation resolution
- runtime observation and screenshot inspection
- cart adjustment and latest-order support

## Contract location

Implementation contracts live in:

- `apps/api/app/schemas`
- `apps/web/lib/types.ts`

## Scope rule

This folder should document only active endpoints and payloads that exist in the runnable codebase.
