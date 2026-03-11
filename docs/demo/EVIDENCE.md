# Phase 4 Evidence Pack

This document summarizes the bounded nopCommerce scenarios that are green in the repo and the evidence judges or operators can rely on today.

## Green bounded scenarios

- golden happy path: search, results, product verification, add-to-cart, cart verification, checkout-entry recognition, intentional stop
- blocker path: configurable product requires options and is blocked before add-to-cart
- recovery path: modal interruption or selector/layout drift triggers deterministic recovery or safe halt
- audit/log completeness: page type, verification outcome, blocker or recovery reason, cart count, and checkout stop reason are surfaced
- spoken micro-summary stability: results loaded, product verified, add-to-cart success, cart verified, checkout-entry stop

## Latest bounded suite run

Repo-local run on March 11, 2026:

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

Result:

- `131 passed`
- `10 skipped`
- `2 warnings`

## Why the skips are correct

The skipped tests are deferred surfaces outside the bounded demo:

- full checkout continuation
- guest checkout execution
- post-purchase and order-history flows that are not part of the current judging path

Those skips are intentional because BlindNav must stop at checkout entry recognition in the active demo.

## Known warning/noise interpretation

- FastAPI emits `on_event` deprecation warnings from the runtime app startup path
- some tests log backend database metadata initialization retries before dependency overrides take over

Neither warning changes the bounded demo result, but both should be understood as environment noise rather than demo evidence.

## Remaining honest risks

- the suite is still fixture-backed rather than a full live-site end-to-end browser replay
- the current nopCommerce demo theme could change over time and shift selectors or visible text
- Next.js production build can fail if the workspace path contains `#`; use a clean path for frontend build verification if needed
