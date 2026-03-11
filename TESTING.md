# Testing

## Active test surfaces

BlindNav currently validates three main surfaces:

- backend tests in `apps/api/app/tests`
- browser-runtime tests in `browser-runtime/tests`
- frontend static checks in `apps/web`

## Standard commands

From the repo root:

```bash
./scripts/test/run-backend-tests.sh
./scripts/test/run-runtime-tests.sh
./scripts/test/run-frontend-checks.sh
```

Or use Make targets:

```bash
make test-backend
make test-runtime
```

## Bounded demo suite

Use this command when you want the current demo-ready nopCommerce verification surface:

```bash
PYTHONPATH=apps/api:browser-runtime apps/api/.venv/bin/python -m pytest \
  browser-runtime/tests/test_automation_helpers.py \
  browser-runtime/tests/test_observation.py \
  browser-runtime/tests/test_dummy_mode.py \
  browser-runtime/tests/test_service_api.py \
  apps/api/app/tests/test_browser_observation_integration.py \
  apps/api/app/tests/test_agent_api.py \
  apps/api/app/tests/test_agent_context_api.py \
  apps/api/app/tests/test_demo_scenarios.py \
  apps/api/app/tests/test_live_session_api.py \
  apps/api/app/tests/test_control_state.py \
  apps/api/app/tests/test_decision_support.py \
  apps/api/app/tests/test_agent_engine.py \
  apps/api/app/tests/test_agent_command_executor.py \
  apps/api/app/tests/test_checkpoint_api.py \
  apps/api/app/tests/test_session_control_routes.py \
  -q
```

Interpretation:

- passing means the bounded happy path, blocker path, recovery path, audit-log coverage, and spoken-summary coverage are green
- skipped tests are deferred full-checkout or post-purchase surfaces outside the current demo scope
- warnings currently reflect known startup/deprecation noise, not a bounded-demo failure

## Frontend checks

Frontend checks currently run:

- `npm run typecheck`
- `npm run build`

Known caveat:

- `npm run build` or `next build` can fail if the workspace path contains `#`; move the repo to a clean path before treating that as an app-level frontend regression

## What backend tests cover

The backend suite includes coverage for:

- auth and session ownership
- live session API and websocket event flow
- agent-step execution and deterministic orchestration
- page understanding and product verification
- control-state, checkpoint, and final-confirmation behavior
- bounded happy-path, blocker-path, and recovery-path demo scenarios
- session context, audit logs, and spoken micro-summary stability

## What browser-runtime tests cover

The browser-runtime suite covers:

- nopCommerce page classification for home, listing/search, product, cart, and checkout-entry recognition
- search submission and candidate extraction
- product detail extraction and blocker detection
- bounded add-to-cart verification
- cart extraction and checkout-entry stop notes
- observation payload consistency for replayable fixtures

## Manual local smoke path

After automated tests pass, run a manual local smoke pass through the operator shell:

1. sign in
2. click `Wake Luminar`
3. confirm microphone permission in Chrome or Edge
4. say `Luminar`
5. speak `find one m8`
6. confirm the transcript updates immediately
7. confirm spoken replies are read back through browser-native TTS
8. confirm the `Browser Activity` panel shows screenshot thumbnail, URL, and status
9. confirm the runtime lands on `demo.nopcommerce.com`
10. confirm search results are summarized coherently
11. confirm the simple product is verified and added to cart
12. confirm cart verification is spoken coherently
13. confirm checkout entry is recognized
14. confirm BlindNav stops before guest checkout
15. confirm audit/log output reflects the page type, verification, cart evidence, and checkout stop reason

Optional blocker smoke:

1. search for `build your own computer`
2. confirm BlindNav blocks before add-to-cart
3. confirm the blocker reason is spoken and logged

## What must remain true

When validating changes, confirm that BlindNav still preserves:

- deterministic state-machine control
- browser-grounded execution and verification
- clarification instead of blind continuation
- explicit consent checkpoints
- low-confidence halt and recovery behavior
- user-verifiable logs and bounded spoken summaries
- the checkout-entry stop boundary
