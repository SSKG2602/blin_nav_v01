# Testing

## Automated test surfaces

BlindNav currently validates three main surfaces:

- backend tests in `apps/api/app/tests`
- browser-runtime tests in `browser-runtime/tests`
- frontend static verification in `apps/web`

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

Frontend checks currently run:

- `npm run typecheck`
- `npm run build`

## CI coverage in repo

GitHub workflow files exist for:

- backend CI: `.github/workflows/backend-ci.yml`
- frontend CI: `.github/workflows/frontend-ci.yml`

They provide baseline verification, but local execution is still expected before merging behavior changes.

## What backend tests cover

The backend suite includes coverage for:

- health endpoints
- auth and session ownership
- live session API and websocket event flow
- agent-step execution and orchestration
- page understanding and product verification
- control-state, checkpoint, and final-confirmation behavior
- order and post-purchase control routes
- context, logs, and scenario paths

## What browser-runtime tests cover

The browser-runtime suite covers the runtime service and helper behavior, including:

- observation extraction
- screenshot capture surfaces
- merchant interaction helpers
- cart and order helper logic
- bounded cancellation helpers

## Manual smoke checks

After automated tests pass, run a manual local smoke pass through the operator shell:

1. log in or sign up
2. click `Wake Luminar`
3. confirm the browser microphone permission prompt appears
4. confirm the shell enters wake-listening state
5. say `Luminar`
6. confirm wake detection appears in the transcript
7. speak a shopping request and confirm it appears immediately in the transcript panel
8. confirm the backend responds and browser-native TTS plays the spoken reply
9. confirm the `Browser Activity` panel shows screenshot thumbnail, current URL, and status text
10. verify clarification, checkpoint, or final-confirmation surfaces if triggered
11. verify `Connect Amazon.in` is reachable and status feedback appears in the shell
12. verify cart controls, latest-order loading, and bounded order cancellation when the flow makes them relevant
13. verify session history, closure artifacts, and post-purchase summary visibility

## What must be preserved

When validating behavior changes, confirm that the repo still preserves:

- deterministic state-machine control
- browser-grounded execution and verification
- explicit consent checkpoints
- final verbal confirmation before purchase
- low-confidence halt and recovery behavior
- auditable session history and closure artifacts
- operator-shell visibility for runtime activity and spoken interaction

## Documentation alignment

If a change alters operator flow, API surface, deployment expectations, voice behavior, or testing procedures, update the relevant docs in the same change set.
