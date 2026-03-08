# Playwright Service Notes

The active browser runtime implementation for BlindNav lives in the `browser_runtime` package at the root of `browser-runtime/`.

This `playwright_service` folder is not the main runtime entrypoint today. It remains a useful boundary for sidecar-specific notes or requirements if the runtime surface is split further later.

Current implementation truth:

- Playwright is the browser automation foundation for the repo
- the runnable service is started from `browser_runtime.main`
- merchant interaction, observation, and action helpers live under `browser_runtime/automation`, `browser_runtime/observation`, and `browser_runtime/routes`
