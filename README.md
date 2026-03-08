# BlindNav (`Luminar`)

BlindNav is a voice-first accessibility shopping agent for blind users. It listens to a shopping request, interprets intent, grounds itself on the live merchant page, navigates through a deterministic backend state machine, verifies what it is doing, pauses at sensitive checkpoints, requires final verbal confirmation before purchase, and produces a user-verifiable session record.

This repository is the runnable implementation. The sibling `../Gemini_Hack` folder is reference material for intended scope, workflow, and architecture; it is not the executable codebase.

## Why BlindNav exists

Blind users should not have to trust opaque automation when shopping online. BlindNav is built to keep the agent explainable and constrained:

- voice-first interaction is the primary surface
- browser-grounded evidence is required before important actions
- vision supports page understanding and verification, not blind clicking
- sensitive actions are gated by explicit consent checkpoints
- final order placement requires explicit verbal confirmation
- low-confidence situations halt or route through recovery instead of guessing

## What is implemented here

The current branch is implementation-complete for the bounded non-future hackathon scope:

- deterministic backend orchestration and state-machine control
- browser-runtime execution and page observation via Playwright
- live session flow with websocket events, speech integration, interruption handling, and locale-aware interaction
- intent parsing, clarification, trust checks, grounded navigation, candidate selection, product verification, variant precision checks, review risk analysis, and spoken micro-summaries
- consent checkpoints for sensitive actions, explicit final purchase confirmation, low-confidence halt, desynchronization recovery, and session self-diagnosis
- persistent session history, lightweight auth, agent logs, session closure artifacts, cart context, latest-order support, and post-purchase summary data
- Next.js operator shell for live operation, runtime inspection, checkpoints, final confirmation, cart review, session history, and audit visibility

## Bounded demo scope

BlindNav is intentionally scoped for a bounded hackathon demo:

- primary merchant target: `amazon.in`
- backup contingencies: `flipkart.com`, `meesho.com`
- operator shell: demo and debugging surface, not a consumer-polished storefront
- no claim of unconstrained multi-merchant autonomy
- no claim that future-scope items are implemented beyond what the codebase actually contains

## Architecture principles

- Backend orchestration is the behavioral source of truth.
- The browser runtime is the execution and observation boundary.
- Frontend surfaces state and user actions; it does not own business logic.
- Gemini supports bounded interpretation, summarization, and multimodal assistance.
- Page evidence, runtime observation, and persisted session context remain the source of truth for execution, consent, and verification.

See [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md) for the full breakdown.

## Repository layout

- `apps/api` - FastAPI backend, deterministic orchestration, persistence, live transport, auth, session control, and verification layers
- `apps/web` - Next.js operator shell for live demo operation and audit visibility
- `browser-runtime` - Playwright-based runtime for navigation, action execution, and observation capture
- `docs` - supporting repo-local notes aligned to the current implementation
- `infra` - Dockerfiles and Cloud Run deployment assets
- `packages` - reserved contract/package boundaries documented for future extraction, not active publishable packages today
- `scripts` - local dev, test, and deploy helpers

## Running locally

Use the practical run guide in [RUNNING_LOCALLY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/RUNNING_LOCALLY.md).

Common local commands:

```bash
make install
make dev
make test-backend
make test-runtime
./scripts/test/run-frontend-checks.sh
```

Pinned local ports:

- frontend: `3100`
- backend API: `8100`
- browser runtime: `8200`
- docs/devtools reserve: `4100`

## Testing

Testing guidance lives in [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md).

Current repo test surfaces include:

- backend pytest suite under `apps/api/app/tests`
- browser-runtime pytest suite under `browser-runtime/tests`
- frontend typecheck and production build checks under `apps/web`

## Deployment

Deployment notes live in [DEPLOYMENT.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/DEPLOYMENT.md).

The repo includes:

- Docker Compose for local multi-service execution
- Dockerfiles for backend, frontend, and browser runtime
- Cloud Run deployment assets for the backend under `infra/cloudrun`

## Documentation map

- [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md)
- [API_OVERVIEW.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/API_OVERVIEW.md)
- [RUNNING_LOCALLY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/RUNNING_LOCALLY.md)
- [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md)
- [DEPLOYMENT.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/DEPLOYMENT.md)
- [SECURITY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/SECURITY.md)
- [TROUBLESHOOTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TROUBLESHOOTING.md)
- [HACKATHON_SCOPE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/HACKATHON_SCOPE.md)
- [CONTRIBUTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/CONTRIBUTING.md)

## Contributor acknowledgment

BlindNav in this repo reflects architecture-critical backend, runtime, and integration work led by **Shreyas Gowda S**, with bounded frontend, documentation, and support integration contributions from **Mimansha Mishra**.

## Scope honesty

This repository documents only what is implemented in the current branch. Future scope described in the Gemini_Hack grounding material is not claimed as complete unless the runnable code in this repo supports it.
