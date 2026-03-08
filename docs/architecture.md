# BlindNav Architecture

BlindNav (`Luminar`) is a voice-first shopping copilot with a realtime loop between frontend voice capture, backend reasoning, and browser automation.

## End-to-end Flow

```mermaid
flowchart LR
    A[User Voice Input] --> B[Web Speech API in Next.js Frontend]
    B --> C[WebSocket Session ws://localhost:8100/session]
    C --> D[Backend Orchestrator]
    D --> E[Gemini Reasoning and Plan Generation]
    E --> F[Browser Automation Runtime]
    F --> G[Verification Layer]
    G --> H[Cart Update]
    H --> I[Checkout Checkpoint]
    I --> C
    C --> J[Frontend Voice and Timeline Updates]
```

## Core Components

- `apps/web` (Next.js + React + TypeScript + Tailwind)
- `apps/api` (FastAPI websocket and orchestration endpoints)
- `browser-runtime` (Playwright-based execution engine)
- `data` and `packages` (shared schemas/contracts and fixtures)

## Runtime Responsibilities

1. Voice Input
- Frontend captures speech with Web Speech API.
- Transcript is sent to backend over websocket session.

2. Gemini Reasoning
- Backend interprets intent and builds navigation/action steps.
- Reasoning output is emitted as typed realtime events.

3. Browser Automation
- Playwright runtime executes action plan against merchant pages.
- Intermediate navigation and extraction states are streamed back.

4. Verification
- Extracted product/cart data is validated against request intent.
- Verification failures emit audit events and recovery suggestions.

5. Cart and Checkout Checkpoint
- Backend confirms intended item(s) and cart totals.
- System stops at explicit checkout checkpoint for human approval.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant W as Web UI
    participant B as Backend
    participant G as Gemini
    participant R as Browser Runtime

    U->>W: Speak shopping intent
    W->>B: websocket user_transcript
    B->>G: intent + context
    G-->>B: action plan + reasoning
    B->>R: execute steps
    R-->>B: nav/product/cart states
    B-->>W: navigation_state/cart_update/product_summary
    W-->>U: visual + spoken guidance
    B-->>W: checkout checkpoint event
```

## Notes

- Websocket is the primary realtime channel.
- Frontend timeline acts as session audit trail.
- Checkout is intentionally a gated checkpoint, not silent auto-purchase.
