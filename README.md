# BlindNav (`Luminar`)

BlindNav is a voice-first accessibility shopping agent for blind users. It captures spoken shopping intent, grounds actions in a live merchant browser session, verifies what it sees before progressing, pauses for explicit consent on sensitive steps, requires final confirmation before purchase, and produces a user-verifiable session record at the end of the flow.

This repository is the runnable implementation. The sibling `../Gemini_Hack` folder remains the intended-scope and workflow reference, but the code in this repo is the implementation truth.

## Why BlindNav exists

Blind shopping workflows should not depend on opaque automation or blind trust. BlindNav is built around a stricter model:

- voice-first interaction is the primary user surface
- the backend state machine owns orchestration
- browser-grounded evidence is required before important progression
- vision and Gemini 2.5 Flash support interpretation and summarization, not blind clicking
- sensitive actions pause at explicit checkpoints
- final order placement requires explicit confirmation
- low-confidence situations halt or route through recovery instead of guessing

## The runnable stack

BlindNav runs as three cooperating services:

- `apps/api` - FastAPI backend for deterministic orchestration, auth, persistence, session control, live websocket transport, verification, checkpoints, final confirmation, session closure, and post-purchase support
- `browser-runtime` - Playwright-based runtime for merchant navigation, page interaction, observation capture, screenshots, cart/order operations, and grounded execution
- `apps/web` - Next.js operator shell for voice interaction, live session control, transcript visibility, browser activity monitoring, checkpoint/final-confirmation handling, cart/order controls, and audit visibility

## Implemented features

The current branch implements the bounded non-future BlindNav scope, including:

- wake-word voice flow through the operator shell
- live websocket voice command capture using `user_text`
- browser-native spoken replies from backend `spoken_output` events
- multilingual interaction support
- spoken shopping intent capture, clarification, and safe ambiguity handling
- merchant trust verification and visual page understanding
- grounded search navigation, candidate ranking, product verification, and variant precision checks
- review risk analysis with spoken takeaways
- interruption handling, low-confidence halt, and desynchronization recovery
- cart and checkout verification with explicit checkpoint and final-confirmation gating
- Amazon.in connect flow surfaced from the shell
- browser activity monitor with screenshot thumbnail, URL, and status text
- latest-order support, bounded order cancellation, and post-purchase summary visibility
- session history, lightweight auth, structured logs, closure artifacts, and self-diagnosis

## Bounded demo scope

BlindNav is intentionally scoped for a bounded hackathon demo:

- primary merchant target: `amazon.in`
- bounded backup contingencies: `flipkart.com`, `meesho.com`
- operator shell: live demo and debugging surface, not a consumer storefront
- no claim of unconstrained multi-merchant autonomy
- no claim that future-scope features are implemented unless the runnable repo supports them

## Deployment shape

The production deployment story for this repo is a three-service Google Cloud Run stack:

- `blindnav-api`
- `blindnav-browser-runtime`
- `blindnav-web`

The repo already includes production Dockerfiles for all three services and existing Cloud Run assets for the backend under `infra/cloudrun`. See [DEPLOYMENT.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/DEPLOYMENT.md) for the service topology, environment wiring, and rollout notes.

## Repository layout

- `apps/api` - backend orchestration, API routes, live transport, auth, persistence, cart/order/session logic, and Gemini integration
- `apps/web` - operator shell, browser-native voice capture/TTS, session UI, browser activity panel, and live controls
- `browser-runtime` - Playwright runtime, action helpers, observation extraction, screenshots, and merchant interaction logic
- `docs` - supporting implementation notes aligned to the current repo behavior
- `infra` - Dockerfiles and Cloud Run deployment assets
- `packages` - documented extraction boundaries for contracts that still live in the main implementation
- `scripts` - local dev, test, and deploy helpers

## Running locally

Use [RUNNING_LOCALLY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/RUNNING_LOCALLY.md) for the full startup guide.

Common commands:

```bash
make install
make dev
make test-backend
make test-runtime
./scripts/test/run-frontend-checks.sh
```

Local ports:

- frontend shell: `3100`
- backend API: `8100`
- browser runtime: `8200`
- docs/devtools reserve: `4100`

## Testing

Testing guidance lives in [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md).

The current verification surface includes:

- backend pytest suite in `apps/api/app/tests`
- browser-runtime pytest suite in `browser-runtime/tests`
- frontend typecheck and production build checks in `apps/web`
- manual live smoke checks for voice wake, spoken replies, browser activity, Amazon connect, checkpoints, and post-purchase controls

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

These docs describe the bounded implementation that exists in this branch. Future-scope material in `Gemini_Hack` is useful for intent grounding, but it is not claimed as implemented unless the runnable code in this repo supports it.
