# BlindNav (`Luminar`)

BlindNav is a voice-first accessibility shopping agent for blind users. This repo ships the bounded demo implementation used for the Gemini Live Agent Challenge: a deterministic, browser-grounded shopping flow on `demo.nopcommerce.com` that searches, verifies products, adds safe products to cart, reads the cart back, recognizes checkout entry, and then intentionally stops before guest checkout.

## What BlindNav does

- listens for wake-driven or typed shopping requests in the operator shell
- grounds actions in a live browser session instead of guessing
- verifies search results, product detail, and cart state before progressing
- halts or clarifies on configurable products, minimum-quantity blockers, or low-confidence evidence
- keeps checkpoints, final confirmation, audit logs, and spoken summaries intact

## Active bounded demo scope

The active Phase 4 demo path is:

1. land on the nopCommerce home page
2. submit a search
3. read back search results
4. open and verify a product
5. add to cart when safe
6. verify cart contents
7. recognize checkout entry
8. stop before guest checkout

Supported demo-visible paths:

- happy path: simple supported product such as `HTC One M8 Android L 5.0 Lollipop`
- blocker path: configurable product such as `Build your own computer`
- recovery path: modal interruption or selector/layout drift leading to deterministic recovery or safe halt

Hard boundaries:

- no full checkout
- no `Checkout as Guest` click
- no address, shipping, payment, or order placement flow
- no merchant expansion beyond `demo.nopcommerce.com`

## Why the merchant is bounded

The current repo is optimized for one rehearsed public merchant so the demo can show trust, verification, and accessibility-first control clearly. The goal is not broad merchant abstraction. The goal is a judgeable, repeatable, honest demo path.

## Service layout

- `apps/api` - FastAPI backend for deterministic orchestration, live transport, verification, clarification, checkpoints, final confirmation, recovery, session context, and audit logs
- `browser-runtime` - Playwright-based runtime for nopCommerce navigation, DOM-first observation, screenshots, search/product/cart actions, and checkout-entry recognition
- `apps/web` - Next.js operator shell for wake flow, transcript visibility, spoken replies, runtime activity, checkpoints, and session controls

## Run locally

Use [RUNNING_LOCALLY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/RUNNING_LOCALLY.md) for startup steps.

Common commands:

```bash
make install
make dev
./scripts/test/run-backend-tests.sh
./scripts/test/run-runtime-tests.sh
./scripts/test/run-frontend-checks.sh
```

## Demo and evidence docs

- [docs/demo/README.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/docs/demo/README.md)
- [docs/demo/OPERATOR_GUIDE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/docs/demo/OPERATOR_GUIDE.md)
- [docs/demo/EVIDENCE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/docs/demo/EVIDENCE.md)
- [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md)
- [TROUBLESHOOTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TROUBLESHOOTING.md)
- [DEPLOYMENT.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/DEPLOYMENT.md)

## Scope honesty

This repo preserves the full BlindNav safety model, but the active public demo is intentionally bounded. If a behavior is not covered by the nopCommerce happy path, blocker path, or recovery path documented here, it should not be presented as part of the live demo.
