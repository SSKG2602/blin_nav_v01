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

They provide baseline repo verification, but local execution is still expected before merging behavior changes.

## What backend tests cover

The backend suite includes coverage for:

- health endpoints
- auth
- session APIs and repositories
- live session API
- agent-step execution
- orchestration and engine behavior
- page understanding
- product verification
- control-state and checkpoint flows
- demo scenario paths
- efficiency and context handling

## What browser-runtime tests cover

The browser-runtime suite covers the runtime service and helper behavior, including observation and automation helpers used by the backend execution path.

## Manual smoke checks

After automated tests pass, run a manual local smoke pass through the operator shell:

1. log in or sign up
2. create a live session
3. submit a shopping request
4. verify transcript and spoken-response updates
5. verify runtime observation is visible
6. verify clarification, checkpoint, or final-confirmation surfaces if triggered
7. verify session history, cart controls, and latest-order loading

## What must be preserved

When validating behavior changes, confirm that the repo still preserves:

- deterministic state-machine control
- browser-grounded execution and verification
- explicit consent checkpoints
- final verbal confirmation before purchase
- low-confidence halt and recovery behavior
- auditable session history and closure artifacts

## Documentation alignment

If a change alters operator flow, API surface, deployment expectations, or testing procedures, update the relevant docs in the same change set.
