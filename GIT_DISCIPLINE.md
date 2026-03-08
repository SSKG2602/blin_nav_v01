# Git Discipline

## Scope Control

- This repository is the shippable codebase
- `../Gemini_Hack` is reference-only and must not be edited from this repo
- Changes must preserve deterministic BlindNav architecture and existing API/runtime contracts unless explicitly planned

## Branch Naming

- Use hyphenated names only
- Do not use `#` in branch names
- Prefer short, concrete names tied to the change set

Examples:
- `sskg-78-orchestrator-hardening`
- `msms-64-frontend-shell-panels`
- `docs-implementation-alignment`

## Ownership Boundaries

- `sskg-78` owns most backend, infra, browser runtime, AI integration, and architecture-critical paths
- `msms-64` owns bounded frontend, docs, fixtures, and smoke-oriented support paths
- Cross-cutting changes should remain narrow and low-risk so both owners can integrate safely

## Commit and PR Rules

- Keep commits focused
- Avoid unrelated refactors in controlled integration phases
- Prefer readable commit messages over clever ones
- Document assumptions when a reference detail is missing locally
- Do not mix architecture-sensitive behavior changes with unrelated cleanup

## Repository Rules

- No secrets in the repo
- No fake business logic
- No hardcoded merchant flows
- No port `3000`
- Keep Apple Silicon macOS, WSL2 Linux, and Cloud Run Linux compatibility in mind
