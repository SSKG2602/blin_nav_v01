# Agent Log Schema

BlindNav already writes structured agent logs and session closure artifacts through the backend.

Current canonical locations:

- `apps/api/app/schemas/agent_log.py`
- `apps/api/app/schemas/session_closure.py`
- `apps/api/app/models/session.py`
- `apps/api/app/repositories/session_repo.py`

This package directory remains a reserved extraction boundary if the log contract is later separated into a standalone shared package.
