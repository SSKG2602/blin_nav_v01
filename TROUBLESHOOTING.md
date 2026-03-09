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
- `FRONTEND_ORIGIN` matches the deployed or local frontend host
- websocket traffic to the backend is not blocked by origin or proxy settings

## Gemini-backed features are failing

Check:

- `GEMINI_API_KEY` is set
- the configured Gemini model names point to your intended Gemini 2.5 Flash deployment target
- outbound network access is available from the backend environment

If Gemini is unavailable, interpretation or summary quality may degrade, but deterministic orchestration should still remain intact.

## Wake word is not triggering

Check:

- you are using Chrome or Edge
- microphone permission was granted when `Wake Luminar` was clicked
- the shell entered wake-listening state
- the websocket session is active after the wake button was pressed

If the fallback message says voice recognition requires Chrome or Edge, switch browsers or use typed input.

## Browser speech recognition is unavailable

Check:

- the browser supports `SpeechRecognition` or `webkitSpeechRecognition`
- microphone permission has not been blocked
- the shell is running in Chrome or Edge

Safari and other unsupported browsers should fall back to typed input rather than voice recognition.

## Browser-native TTS is not speaking

Check:

- the browser allows audio playback
- `window.speechSynthesis` is available
- the backend is emitting `spoken_output`
- the shell is not muted by autoplay or OS-level output settings

## Browser activity panel is blank or stale

Check:

- the browser-runtime is reachable through the backend
- `GET /api/sessions/{session_id}/runtime/screenshot` is returning data
- the session is active and the shell is polling runtime screenshots
- the current page is still available to the browser-runtime session

## Amazon connect status is not appearing

Check:

- a live session exists before clicking `Connect Amazon.in`
- the popup was not blocked by the browser
- the shell can reach `/api/auth/amazon/status/{session_id}`
- the runtime session still has the relevant merchant cookies

## Order cancellation is unavailable

Check:

- a latest-order snapshot exists for the session
- the merchant page still exposes the latest order card
- the order is still inside Amazon’s cancellable window

If the shell says the order has already shipped, the cancellation path is no longer available by design.

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
