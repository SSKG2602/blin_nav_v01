# Shared Types

Cross-surface contracts already exist, but they currently live inside the backend schemas and frontend type mirrors rather than in a dedicated published package.

Current canonical locations:

- `apps/api/app/schemas`
- `apps/web/lib/types.ts`

This package directory remains a reserved extraction boundary if shared contracts need to be published or versioned separately later.
