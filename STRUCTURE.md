# Repository Structure

This repository is a minimal monorepo foundation for BlindNav. It mirrors the documented split between frontend shell, backend API, browser runtime, infrastructure, and shared contracts without implementing product logic yet.

## Top Level

- `apps/web` - Next.js 15 placeholder frontend on port `3100`
- `apps/api` - FastAPI placeholder backend on port `8100`
- `browser-runtime` - Playwright runtime placeholder only
- `infra/docker` - local container images
- `infra/cloudrun` - Cloud Run deployment skeleton
- `packages` - shared cross-surface contract placeholders
- `scripts` - local dev, test, and deployment helpers
- `docs` - architecture, API, prompt, merchant, and demo notes
- `data` - fixtures, merchant metadata, transcripts, and seed placeholders
- `tests` - repo-level e2e, integration, contract, and smoke placeholders
- `.github/workflows` - CI skeleton

## Principles

- Foundation only: no feature modules yet
- Keep the backend as the future deployment center for Cloud Run
- Keep the browser runtime isolated until real Playwright services exist
- Keep shared packages intentionally empty until contracts are defined
- Keep reference planning material outside this repository
