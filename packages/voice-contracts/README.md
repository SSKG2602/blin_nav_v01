# Voice Contracts

BlindNav already includes a live voice/session transport path and voice-related payloads.

Current voice behavior includes:

- wake phrase detection in the frontend shell
- wake-driven spoken input normalized into websocket `user_text`
- backend `spoken_output` events for assistant replies
- browser-native TTS playback in the operator shell

Current canonical locations:

- `apps/api/app/schemas/live_session.py`
- `apps/api/app/live`
- `apps/api/app/api/routes/live.py`
- `apps/web/lib/types.ts`
- `apps/web/lib/browser-speech.ts`

This package directory is reserved if voice contracts later need to be extracted into a standalone shared package.
