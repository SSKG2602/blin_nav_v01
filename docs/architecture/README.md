# Architecture Notes

The authoritative top-level architecture document is [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md).

Use this folder for narrower supplements only when they add implementation detail without duplicating or contradicting the top-level architecture story.

## Current implementation anchors

- deterministic backend orchestration lives under `apps/api/app/agent`
- API and live transport live under `apps/api/app/api/routes`
- browser-grounded execution lives under `browser-runtime` and `apps/api/app/tools`
- session, context, cart, order, and closure persistence live under `apps/api/app/models`, `apps/api/app/repositories`, and `apps/api/app/schemas`
- the operator shell lives under `apps/web`

## Scope rule

Architecture notes in this folder should stay implementation-grounded and should not reintroduce planning-era or branch-era language as the main explanation.
