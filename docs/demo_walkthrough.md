# Hackathon Demo Walkthrough

This script is for a live BlindNav (`Luminar`) demonstration.

## Demo Goal

Show a complete voice-driven shopping loop:

voice input -> agent reasoning -> browser navigation state -> product/cart verification -> checkout checkpoint.

## Pre-demo Checklist

1. Start stack:
```bash
docker compose up --build
```
2. Open frontend on `http://localhost:3100`.
3. Confirm backend websocket endpoint is reachable at `ws://localhost:8100/session`.
4. Keep microphone permission enabled in browser.

## Live Demo Steps

1. Introduce UI layout
- Left panel: voice interaction, transcript, agent response, navigation/cart status.
- Right panel: session history timeline with typed events.

2. Start voice intent
- Click microphone button.
- Speak: "Find running shoes under 3000 rupees."
- Highlight transcript capture and `voice_intent` event in timeline.

3. Explain reasoning and navigation
- Narrate that backend sends request to Gemini for plan generation.
- Show incoming `navigation_state` events updating in realtime.

4. Show product summary
- Point to agent response and timeline `product_summary` event.
- Expand event metadata to show details.

5. Show cart update
- Trigger "Add the second option to cart."
- Highlight `cart_update` event and cart indicator panel.

6. Show auditability
- Expand one or two timeline entries.
- Show timestamp, event type, description, metadata.
- Open audit summary card (warnings/errors counters).

7. Export log
- Click `Export Session Log`.
- Mention JSON can be shared for judging and debugging.

8. Checkout checkpoint
- Explain system pauses at checkout checkpoint for explicit user confirmation.
- Reinforce safety: no silent final purchase step.

## Suggested Narration

- "Luminar listens to voice, converts it to structured intent, and streams every state transition."
- "Judges can inspect the exact action trail in session history, including metadata."
- "BlindNav keeps a human approval checkpoint before checkout completion."

## Failure Recovery Talking Points

- If speech fails: use keyboard shortcut (`Space`) to retry listening.
- If websocket drops: show connection state and relaunch backend container.
- If merchant state changes: rely on verification and audit events before cart/checkout.
