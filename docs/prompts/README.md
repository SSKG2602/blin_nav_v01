# Prompt Notes

BlindNav already uses Gemini-backed interpretation, summarization, and multimodal support in the backend. Prompt ownership is currently implementation-local rather than published as a standalone contract package.

Relevant implementation areas:

- `apps/api/app/llm/client.py`
- `apps/api/app/llm/gemini_service.py`
- `apps/api/app/api/routes/agent.py`
- `apps/api/app/api/routes/live.py`

Use this folder only for prompt-interface documentation that is stable enough to matter outside the current implementation.
