# BlindNav Architecture

BlindNav is a deterministic, browser-grounded shopping agent for blind users. The architecture is intentionally opinionated: language models assist bounded interpretation and summarization, but the backend state machine, browser evidence, and persisted session context remain the source of truth.

## Source of truth

- backend orchestration in `apps/api/app/agent`
- API and live transport in `apps/api/app/api/routes`
- browser-grounded action and observation in `browser-runtime` and `apps/api/app/tools`
- persisted session, context, logs, cart, and closure artifacts in `apps/api/app/models`, `apps/api/app/repositories`, and `apps/api/app/schemas`

The frontend shell in `apps/web` is an operator surface over those systems. It does not own business logic.

## Deterministic state machine

BlindNav is not an unconstrained chat agent. The backend advances through explicit states and events:

- intent capture and clarification
- merchant trust verification
- page understanding and grounded navigation
- product and variant verification
- review assessment and micro-summaries
- cart and checkout progression
- sensitive checkpoints
- final purchase confirmation
- checkout-entry stop handling and session closure

Transitions are evaluated in the backend, not improvised in the frontend.

## Backend orchestration ownership

The backend owns:

- state transitions and guardrails
- control-state derivation
- clarification and ambiguity loops
- runtime outcome normalization
- recovery and low-confidence halt behavior
- session closure and self-diagnosis artifacts

Key implementation areas:

- `apps/api/app/agent/engine.py`
- `apps/api/app/agent/state.py`
- `apps/api/app/agent/runtime_bridge.py`
- `apps/api/app/agent/control_state.py`
- `apps/api/app/agent/session_closure.py`

## Browser-runtime role

The browser runtime is the execution and observation boundary. It is responsible for:

- navigating merchant pages
- interacting with search, product, cart, and checkout-entry surfaces
- capturing page observations and screenshots
- reading grounded evidence used for verification, recovery, cart confirmation, and checkout-entry recognition

It is not allowed to invent product state, trust state, cart state, or checkout state. Those must be derived from observed page evidence and persisted through the backend.

## Frontend operator shell role

The Next.js shell in `apps/web` exists for live operation and demo visibility:

- start sessions and connect to the live websocket
- request microphone permission, capture wake phrase and spoken commands, and play browser-native spoken replies
- display transcript, agent speech, browser activity screenshot, URL, runtime mirror, and event stream
- surface auth, session history, checkpoints, final confirmation, cart context, and runtime visibility
- let the operator review or resolve state that is already owned by the backend

The shell can request actions. It does not decide what state the agent is in. Screenshot polling and activity text are visibility layers over backend and runtime truth, not new sources of truth.

## Gemini role

Gemini 2.5 Flash is the deployment-target model family for bounded reasoning and summarization tasks:

- intent understanding
- clarification answer interpretation
- page and verification summarization
- multimodal assessment support
- visual fallback analysis when DOM or OCR evidence is weak

Gemini does not replace:

- the deterministic state machine
- browser-grounded action execution
- consent checkpoints
- final confirmation
- cart or checkout state truth
- trust verification ownership

## Checkpoints, confirmation, and recovery

Safety behavior is first-class:

- OTP, CAPTCHA, and payment-auth flows surface as explicit checkpoints
- final order placement requires a dedicated final verbal confirmation state
- low-confidence conditions halt or reroute through recovery
- interruption is a backend control primitive, not only a frontend playback control
- recovery stores reason and outcome instead of silently masking desync

## Persistence, logging, and closure

The repo persists enough session state to make the agent inspectable:

- session records and lightweight history
- auth-linked ownership for user-scoped history
- structured agent logs
- session context snapshots
- cart context snapshots
- final session closure artifact
- deterministic self-diagnosis before close

This allows BlindNav to provide a user-verifiable summary instead of a black-box result.

## What is not a source of truth

The following are informative but not authoritative on their own:

- frontend panels and badges
- docs claims
- unused enums or schemas
- isolated tests that seed state without a real runtime path

Implementation truth comes from the live backend-runtime loop and persisted artifacts.

## Scope boundary

This repo documents and implements the bounded non-future BlindNav scope grounded by the sibling `Gemini_Hack` reference material. It does not claim completion for unconstrained internet shopping, multi-merchant orchestration at scale, advanced delivery intelligence, or production-grade autonomous checkout beyond the current bounded demo architecture.

## Demo Merchant Boundary

Phase 1 centers a single rehearsed public merchant at `demo.nopcommerce.com`.
The repo currently treats search, product detail, cart, browser activity visibility,
verification, checkpoints, and voice-first control as the active demo path.
Checkout entry recognition remains bounded and should not be presented as
full nopCommerce checkout automation without later validation.
