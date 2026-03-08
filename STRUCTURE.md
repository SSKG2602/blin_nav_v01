# Repository Structure

This repository is an active BlindNav implementation monorepo with deterministic backend orchestration, browser-runtime integration, and an operator-oriented frontend shell.

## Top Level

- `apps/web` - Next.js operator shell on `3100`, including live control panels, transcript/exchange UI, checkpoint/final-confirmation surfaces, runtime mirror, and session history
- `apps/api` - FastAPI service on `8100` with session APIs, deterministic agent-step orchestration, live websocket gateway, and context/checkpoint/final-confirmation/runtime endpoints
- `browser-runtime` - Playwright-backed runtime service for action execution + page observation/screenshot capture
- `infra/docker` - container build definitions for local/dev execution
- `infra/cloudrun` - deployment assets for Cloud Run
- `packages` - shared contract/package stubs and schema notes used across surfaces
- `scripts` - local dev/test/deploy helpers
- `docs` - implementation-aligned architecture/API/demo/prompt/merchant notes
- `data` - fixtures/transcripts placeholders and runtime support folders
- `tests` - test harness roots; most active test coverage currently sits under `apps/api/app/tests` and `browser-runtime/tests`
- `.github/workflows` - CI workflow skeletons

## Principles

- Deterministic orchestration is intentional and remains backend-owned.
- Frontend is an operator shell: it visualizes and controls existing backend behavior; it does not own business orchestration.
- Browser runtime is consumed via explicit backend tool boundaries.
- Consent checkpoints, final confirmation, and safety-state visibility are first-class demo behaviors.
- Documentation should describe only implemented behavior; speculative future scope belongs in reference planning material, not implementation docs.
