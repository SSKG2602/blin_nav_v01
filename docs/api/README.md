# API Notes

The authoritative repo-level API summary is [API_OVERVIEW.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/API_OVERVIEW.md).

This note keeps the `docs/api` path available without duplicating the full overview.

## Current public demo API shape

BlindNav currently exposes route groups for:

- health and readiness
- lightweight auth and user identity
- bounded session initialization on `demo.nopcommerce.com`
- session lifecycle, logs, context, and history
- deterministic `agent/step` execution
- live websocket sessions
- checkpoint and final-confirmation resolution
- runtime observation and screenshot inspection
- cart adjustment helpers used by the operator shell

## Active demo boundary

The public demo flow stops at checkout-entry recognition. The current demo should not be described as using the API for guest checkout execution, payment, or order placement.

## Internal/non-demo surfaces

Some routes for latest-order loading or cancellation still exist in the runnable codebase, but they are not part of the active Phase 4 demo story and should not be used as judging claims.

## Contract location

Implementation contracts live in:

- `apps/api/app/schemas`
- `apps/web/lib/types.ts`
