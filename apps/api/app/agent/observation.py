from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agent.ocr import build_ocr_observation_patch, extract_text_from_screenshot
from app.agent.perception import classify_page_understanding
from app.llm.client import BlindNavLLMClient
from app.schemas.page_understanding import PageType, PageUnderstanding
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


def capture_page_understanding_hybrid(
    browser_client: BrowserRuntimeClient,
    llm_client: BlindNavLLMClient,
    session_id: UUID,
) -> tuple[PageUnderstanding, dict[str, Any], dict[str, Any] | None]:
    raw_observation = browser_client.get_current_page_observation(session_id=session_id)
    if not isinstance(raw_observation, dict):
        raw_observation = {}

    understanding = build_page_understanding_from_browser_observation(raw_observation)
    needs_visual_fallback = (
        understanding.page_type == PageType.UNKNOWN
        or understanding.confidence < 0.45
        or (understanding.primary_product is None and not understanding.product_candidates)
    )

    screenshot_payload: dict[str, Any] | None = None
    if not needs_visual_fallback:
        return understanding, raw_observation, screenshot_payload

    screenshot_raw = browser_client.get_current_page_screenshot(session_id=session_id)
    if isinstance(screenshot_raw, dict):
        screenshot_payload = screenshot_raw
    else:
        screenshot_payload = {}

    ocr_text = extract_text_from_screenshot(screenshot_payload)
    ocr_patch = build_ocr_observation_patch(ocr_text)
    if ocr_patch:
        merged = dict(raw_observation)
        for key in (
            "page_type",
            "notes",
            "checkout_ready",
            "cart_item_count",
            "primary_product",
            "product_candidates",
        ):
            if key in ocr_patch:
                if key == "primary_product":
                    existing_primary = merged.get("primary_product")
                    if isinstance(existing_primary, dict) and isinstance(ocr_patch[key], dict):
                        merged[key] = {**existing_primary, **ocr_patch[key]}
                    else:
                        merged[key] = ocr_patch[key]
                else:
                    merged[key] = ocr_patch[key]
        understanding = build_page_understanding_from_browser_observation(merged)
        raw_observation = merged
        if understanding.page_type != PageType.UNKNOWN and understanding.confidence >= 0.45:
            return understanding, raw_observation, screenshot_payload

    try:
        visual_patch = llm_client.analyze_visual_page(
            raw_observation=raw_observation,
            screenshot=screenshot_payload,
        )
    except Exception:
        visual_patch = {}

    if isinstance(visual_patch, dict) and visual_patch:
        merged = dict(raw_observation)
        for key in (
            "page_type",
            "notes",
            "checkout_ready",
            "cart_item_count",
            "primary_product",
            "product_candidates",
        ):
            if key in visual_patch:
                merged[key] = visual_patch[key]
        understanding = build_page_understanding_from_browser_observation(merged)
        raw_observation = merged

    return understanding, raw_observation, screenshot_payload
