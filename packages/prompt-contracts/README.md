# Prompt Contracts

Prompt logic and Gemini wiring are already active in the backend implementation. The docs target Gemini 2.5 Flash as the deployed model family for those prompt-driven flows.

Current canonical locations:

- `apps/api/app/llm/client.py`
- `apps/api/app/llm/gemini_service.py`
- `apps/api/app/api/routes/live.py`
- `apps/api/app/api/routes/agent.py`

This package directory is reserved for future extraction of stable prompt contracts if cross-surface reuse becomes necessary.
