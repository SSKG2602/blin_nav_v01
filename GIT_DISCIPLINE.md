# Git Discipline

## Scope Control

- This repository is the shippable codebase
- `../Gemini_Hack` is reference-only and must not be edited from this repo
- Bootstrap work should stay limited to shared foundation and repo hygiene

## Branch Naming

- Use hyphenated names only
- Do not use `#` in branch names
- Prefer short, concrete names tied to the change set

Examples:
- `foundation-repo-bootstrap`
- `sskg-78-infra-base`
- `msms-64-docs-bootstrap`

## Ownership Boundaries

- `sskg-78` owns most backend, infra, browser runtime, AI integration, and architecture-critical paths
- `msms-64` owns bounded frontend, docs, fixtures, and smoke-oriented support paths
- Shared base changes should remain narrow and low-risk so both owners can branch safely afterward

## Commit and PR Rules

- Keep commits focused
- Avoid unrelated refactors during scaffold setup
- Prefer readable commit messages over clever ones
- Document assumptions when a reference detail is missing locally
- Do not merge feature logic into foundation branches

## Early Repository Rules

- No secrets in the repo
- No fake business logic
- No hardcoded merchant flows
- No port `3000`
- Keep Apple Silicon macOS, WSL2 Linux, and Cloud Run Linux compatibility in mind
