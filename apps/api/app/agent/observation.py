from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agent.perception import classify_page_understanding
from app.schemas.page_understanding import PageUnderstanding
from app.tools.browser_runtime import BrowserRuntimeClient


def build_page_understanding_from_browser_observation(
    raw_observation: dict[str, Any],
) -> PageUnderstanding:
    normalized: dict[str, Any] = dict(raw_observation)
    observed_url = normalized.pop("observed_url", None)
    if "url" not in normalized and observed_url is not None:
        normalized["url"] = observed_url

    hints = normalized.get("detected_page_hints")
    if "page_type" not in normalized and isinstance(hints, list):
        for hint in hints:
            if isinstance(hint, str) and hint.strip():
                normalized["page_type"] = hint
                break

    return classify_page_understanding(normalized)


def capture_page_understanding(
    browser_client: BrowserRuntimeClient,
    session_id: UUID,
) -> PageUnderstanding:
    raw_observation = browser_client.get_current_page_observation(session_id=session_id)
    if not isinstance(raw_observation, dict):
        raw_observation = {}
    return build_page_understanding_from_browser_observation(raw_observation)

