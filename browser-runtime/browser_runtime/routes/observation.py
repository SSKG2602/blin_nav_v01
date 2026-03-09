from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException

from browser_runtime.driver import browser_session_manager
from browser_runtime.observation.extractor import (
    extract_current_page_observation,
    extract_current_page_screenshot,
)
from browser_runtime.observation.models import (
    RuntimeAmazonAuthStatus,
    RuntimePageObservation,
    RuntimeScreenshotObservation,
)

router = APIRouter(prefix="/sessions", tags=["observation"])


@router.get("/{session_id}/observation/current_page", response_model=RuntimePageObservation)
def get_current_page_observation(session_id: UUID) -> RuntimePageObservation:
    page = browser_session_manager.get_page(session_id)
    return extract_current_page_observation(page)


@router.get(
    "/{session_id}/observation/screenshot",
    response_model=RuntimeScreenshotObservation,
)
def get_current_page_screenshot(session_id: UUID) -> RuntimeScreenshotObservation:
    page = browser_session_manager.get_page(session_id)
    return extract_current_page_screenshot(page)


@router.get(
    "/{session_id}/observation/amazon_auth_status",
    response_model=RuntimeAmazonAuthStatus,
)
def get_amazon_auth_status(session_id: UUID) -> RuntimeAmazonAuthStatus:
    return RuntimeAmazonAuthStatus.model_validate(
        browser_session_manager.get_amazon_auth_status(session_id)
    )


@router.post("/{session_id}/cookies")
def set_session_cookies(
    session_id: UUID,
    payload: dict[str, Any] = Body(...),
) -> dict[str, bool]:
    raw_cookies = payload.get("cookies")
    if not isinstance(raw_cookies, str) or not raw_cookies.strip():
        raise HTTPException(status_code=400, detail="cookies is required")

    try:
        cookies_list = json.loads(raw_cookies)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="cookies must be valid JSON") from exc

    if not isinstance(cookies_list, list):
        raise HTTPException(status_code=400, detail="cookies JSON must decode to a list")

    try:
        browser_session_manager.set_session_cookies(session_id, cookies_list)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load cookies: {exc}") from exc

    return {"ok": True}
