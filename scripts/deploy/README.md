# Deploy Scripts

The active deployment assets in this repo currently live under `infra/cloudrun`.

Authoritative deployment guidance is in [DEPLOYMENT.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/DEPLOYMENT.md).

Current in-repo deployment files:

- `infra/cloudrun/service.yaml`
- `infra/cloudrun/deploy.sh`
- `infra/cloudrun/env.sample.yaml`

Use `scripts/deploy` only for additional wrapper scripts that reflect the real deployment flow and reduce operator overhead without duplicating or obscuring the existing Cloud Run path.
