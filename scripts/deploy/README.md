# Deploy Scripts

The active deployment assets in this repo currently live under `infra/cloudrun` and `infra/docker`.

Authoritative deployment guidance is in [DEPLOYMENT.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/DEPLOYMENT.md).

Current in-repo deployment files:

- backend Cloud Run template: `infra/cloudrun/service.yaml`
- backend deploy helper: `infra/cloudrun/deploy.sh`
- backend env sample: `infra/cloudrun/env.sample.yaml`
- backend image: `infra/docker/backend.Dockerfile`
- browser-runtime image: `infra/docker/playwright.Dockerfile`
- frontend image: `infra/docker/frontend.Dockerfile`

Use `scripts/deploy` only for additional wrapper scripts that reflect the real three-service Cloud Run deployment flow and reduce operator overhead without obscuring the existing backend manifests or the separate frontend/browser-runtime container wiring.
