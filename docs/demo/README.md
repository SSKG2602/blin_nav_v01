# Demo Notes

BlindNav is aligned to the UI Navigator track with a voice-first operator shell and browser-grounded execution path.

Current implementation status:
- live-session creation + websocket interaction are available
- deterministic agent-step progression is wired through backend orchestration
- checkpoint and final-confirmation controls are exposed in the web operator shell
- runtime observation/screenshot mirror is available in the shell
- safety-state surfaces (low confidence, recovery, pending consent) are visible in the shell

Intentional demo boundaries:
- primary flow is constrained and deterministic
- no claim of unconstrained autonomous shopping
- consent checkpoints remain explicit operator/user gates
