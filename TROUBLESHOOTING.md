# Troubleshooting

## Backend will not start

Check:

- `.env` exists at the repo root
- PostgreSQL is reachable at `DATABASE_URL`
- Redis is reachable at `REDIS_URL`
- Python dependencies are installed under the expected virtual environment

Useful commands:

```bash
docker compose ps postgres redis
curl http://localhost:8100/health
curl http://localhost:8100/health/ready
```

## Browser runtime is unavailable

Check:

- the runtime process is running on port `8200`
- Playwright dependencies are installed
- the backend `BROWSER_RUNTIME_BASE_URL` matches the runtime host

Useful command:

```bash
curl http://localhost:8200/health/live
```

## Frontend cannot reach the backend

Check:

- `NEXT_PUBLIC_API_BASE_URL` is set correctly
- the backend is listening on `8100`
- CORS origin matches the frontend host

## Gemini-backed features are failing

Check:

- `GEMINI_API_KEY` is set
- the configured Gemini model names exist for your environment
- outbound network access is available from the backend environment

If Gemini is unavailable, some interpretation or summary paths may degrade, but deterministic orchestration should still remain intact.

## Voice input is not working

Check:

- browser microphone permissions
- websocket connection from the shell
- browser-native speech mode configuration

Remember that the default live speech provider is `browser-native`, so browser capabilities matter in local testing.

## OCR-dependent page understanding is weak

Check:

- Tesseract is installed locally when running the backend outside Docker
- `OCR_ENABLED` is not disabled
- the browser runtime can capture the current page successfully

## Health checks look inconsistent

Interpret them correctly:

- `/health` checks basic process availability
- `/health/live` checks liveness
- `/health/ready` checks readiness, including infrastructure dependencies

## Auth or session history looks empty

Check:

- you are signed in with the expected user
- the backend database is persistent and reachable
- you are not switching between guest mode and signed-in mode unexpectedly
