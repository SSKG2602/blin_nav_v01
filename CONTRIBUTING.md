# Contributing to BlindNav

Thank you for contributing to BlindNav. This repository is a runnable engineering codebase, not a planning sandbox. Changes should improve the real implementation, keep the bounded demo path stable, and preserve the deterministic architecture.

## Contribution standards

- keep changes scoped and reviewable
- align every behavior change with the current implementation, not with speculative roadmap ideas
- preserve deterministic backend ownership of orchestration
- preserve browser-grounded execution and verification
- do not bypass consent checkpoints, final confirmation, or low-confidence safety behavior
- keep docs aligned with code whenever implementation behavior changes

## What kinds of changes are welcome

- backend improvements that preserve deterministic control and verification
- browser-runtime hardening for grounded merchant interaction
- frontend operator shell improvements that do not move orchestration into the UI
- test coverage that proves real behavior instead of seeded or cosmetic completion
- documentation updates that reflect actual repo behavior
- operational fixes for local run, deployment, observability, and debugging

## Branch and pull request hygiene

- branch from current `main`
- keep one bounded purpose per branch
- avoid mixing architecture-sensitive behavior changes with unrelated cleanup
- summarize user-visible behavior changes and risk in the PR description
- list commands run for local verification
- call out any environment-variable additions or contract changes clearly

## Testing expectations

Before opening a PR for behavior changes, run the relevant checks:

- backend: `./scripts/test/run-backend-tests.sh`
- browser runtime: `./scripts/test/run-runtime-tests.sh`
- frontend: `./scripts/test/run-frontend-checks.sh`

If a change affects the live path, also perform a manual smoke run through the operator shell and note what was exercised.

## Documentation expectations

- keep top-level docs authoritative and implementation-grounded
- update `docs/` notes when supporting explanations need to change
- do not reintroduce planning-era, milestone-era, or placeholder wording once the code has moved beyond it
- do not claim future-scope behavior as implemented

## Architecture preservation

BlindNav relies on a few non-negotiable rules:

- the backend state machine owns orchestration
- the browser runtime owns action execution and observation
- the frontend shell is an operator surface, not the source of truth
- Gemini assists with interpretation, summarization, and multimodal reasoning support; it does not replace runtime evidence or consent gates

Read [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md) before changing behavior.

## Contributor history

For repo history and attribution context:

- **Shreyas Gowda S** contributed architecture-critical backend, browser-runtime, infra, and integration work from the `sskg-78` line
- **Mimansha Mishra** contributed bounded frontend, documentation, and support integration work from the `msms-64` line

That history is useful for context, but future contributions should use normal engineering ownership and review rather than branch-era politics.

## Security and secrets

- never commit credentials, tokens, merchant accounts, or personal data
- keep `.env` files local
- treat auth, checkout, OTP, CAPTCHA, and payment-related behavior as sensitive surfaces

See [SECURITY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/SECURITY.md) for repo-specific guidance.

## New contributors

Start with:

1. [README.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/README.md)
2. [ARCHITECTURE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/ARCHITECTURE.md)
3. [RUNNING_LOCALLY.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/RUNNING_LOCALLY.md)
4. [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md)

If you keep the code deterministic, grounded, and honest about scope, you are contributing in the right direction.
