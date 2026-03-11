from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from browser_runtime.driver import browser_session_manager
from browser_runtime.observation.models import (
    RuntimePageObservation,
    RuntimeScreenshotObservation,
)

router = APIRouter(prefix="/sessions", tags=["observation"])

_DEMO_STORE_HOME = "https://demo.nopcommerce.com"


@router.get("/{session_id}/observation/current_page", response_model=RuntimePageObservation)
def get_current_page_observation(session_id: UUID) -> RuntimePageObservation:
    try:
        if browser_session_manager.get_current_url(session_id) == "about:blank":
            browser_session_manager.navigate_to(session_id, _DEMO_STORE_HOME)
    except Exception:
        pass
    try:
        current_url = browser_session_manager.get_current_url(session_id)
        if current_url and (
            "captcha" in current_url.lower() or "validatecaptcha" in current_url.lower()
        ):
            browser_session_manager.navigate_to(session_id, _DEMO_STORE_HOME)
    except Exception:
        pass
    return browser_session_manager.get_current_page_observation(session_id)


@router.get(
    "/{session_id}/observation/screenshot",
    response_model=RuntimeScreenshotObservation,
)
def get_current_page_screenshot(session_id: UUID) -> RuntimeScreenshotObservation:
    return browser_session_manager.get_page_screenshot(session_id)
