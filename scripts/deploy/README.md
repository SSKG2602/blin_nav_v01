# Deploy Scripts

Deployment scaffolding currently lives under `infra/cloudrun`.

Use this folder for future repo-level deployment helpers only after the application runtime is real enough to justify them. For now:

- `infra/cloudrun/service.yaml` is the Cloud Run service template
- `infra/cloudrun/deploy.sh` is the deployment command wrapper
- `infra/cloudrun/env.sample.yaml` is the env var placeholder file

Do not add feature-specific deployment logic here during foundation setup.
