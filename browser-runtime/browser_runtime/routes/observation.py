from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from browser_runtime.driver import browser_session_manager
from browser_runtime.observation.extractor import extract_current_page_observation
from browser_runtime.observation.models import RuntimePageObservation

router = APIRouter(prefix="/sessions", tags=["observation"])


@router.get("/{session_id}/observation/current_page", response_model=RuntimePageObservation)
def get_current_page_observation(session_id: UUID) -> RuntimePageObservation:
    page = browser_session_manager.get_page(session_id)
    return extract_current_page_observation(page)

